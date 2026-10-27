import shutil
import tempfile
from pathlib import Path
from typing import Sequence
import openpyxl
import pymupdf
from docx import Document
from PIL import Image, ImageOps
from converter.detection import resolve_output_path
from converter.engine import convert_file
from converter.tools import create_zip_archive


def combine_files_to_single_output(
    source_paths: Sequence[Path],
    target_format: str,
    settings: dict | None = None,
) -> Path:
    """Combines multiple input files into a single output file of target_format."""
    if not source_paths:
        raise ValueError("No files provided to combine.")

    settings = settings or {}
    first = Path(source_paths[0]).resolve()
    tgt_ext = target_format.lower().lstrip(".")
    action = target_format.upper().strip()

    if action in {"ZIP", "COMPRESS"} and tgt_ext == "zip":
        out_zip = resolve_output_path(first, "zip", suffix_tag="_combined")
        return create_zip_archive(source_paths, out_zip, password=settings.get("zip_password"))

    # 1. Combine into a single unified PDF (from PDFs, Images, DOCX, TXT, Slides, etc.)
    if tgt_ext == "pdf" or action in {"MERGE-PDF", "EDIT-PDF", "REDACT"}:
        out_pdf = resolve_output_path(first, "pdf", suffix_tag="_combined")
        merged_doc = pymupdf.open()
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(source_paths):
                src = Path(src).resolve()
                ext = src.suffix.lower().lstrip(".")
                if ext == "pdf":
                    with pymupdf.open(str(src)) as pdoc:
                        merged_doc.insert_pdf(pdoc)
                else:
                    tmp_pdf = Path(tmpdir) / f"part_{idx}.pdf"
                    convert_file(src, "PDF", output_path=tmp_pdf, settings=settings)
                    with pymupdf.open(str(tmp_pdf)) as pdoc:
                        merged_doc.insert_pdf(pdoc)

            if settings.get("strip_meta", True):
                merged_doc.set_metadata({})
            merged_doc.save(str(out_pdf), garbage=4, deflate=True)
            merged_doc.close()

        if action == "REDACT":
            from converter.tools import redact_pdf
            redacted_out = resolve_output_path(first, "pdf", suffix_tag="_combined_redacted")
            redact_pdf(
                out_pdf,
                redacted_out,
                custom_terms=settings.get("redact_terms", ""),
                redact_pii=settings.get("redact_pii", True),
            )
            out_pdf.unlink(missing_ok=True)
            return redacted_out

        return out_pdf

    # 2. Combine into a single DOCX document
    if tgt_ext == "docx":
        out_docx = resolve_output_path(first, "docx", suffix_tag="_combined")
        master_doc = Document()
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(source_paths):
                src = Path(src).resolve()
                ext = src.suffix.lower().lstrip(".")
                if ext == "docx":
                    sub_doc = Document(str(src))
                else:
                    tmp_docx = Path(tmpdir) / f"part_{idx}.docx"
                    convert_file(src, "DOCX", output_path=tmp_docx, settings=settings)
                    sub_doc = Document(str(tmp_docx))

                for para in sub_doc.paragraphs:
                    if para.text.strip():
                        master_doc.add_paragraph(para.text)
                for table in sub_doc.tables:
                    new_tbl = master_doc.add_table(rows=len(table.rows), cols=len(table.columns))
                    for r_idx, row in enumerate(table.rows):
                        for c_idx, cell in enumerate(row.cells):
                            new_tbl.cell(r_idx, c_idx).text = cell.text

                if idx < len(source_paths) - 1:
                    master_doc.add_page_break()

        master_doc.save(str(out_docx))
        return out_docx

    # 3. Combine into a single TXT, MD, or HTML file
    if tgt_ext in {"txt", "md", "html"}:
        out_text_file = resolve_output_path(first, tgt_ext, suffix_tag="_combined")
        chunks: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(source_paths):
                src = Path(src).resolve()
                tmp_part = Path(tmpdir) / f"part_{idx}.{tgt_ext}"
                convert_file(src, tgt_ext.upper(), output_path=tmp_part, settings=settings)
                chunks.append(tmp_part.read_text(encoding="utf-8", errors="replace").strip())

        separator = "\n\n<hr>\n\n" if tgt_ext == "html" else "\n\n" + ("=" * 40) + "\n\n"
        out_text_file.write_text(separator.join(chunks), encoding="utf-8")
        return out_text_file

    # 4. Combine into a single XLSX workbook (each file as a sheet) or merged CSV/JSON
    if tgt_ext == "xlsx":
        out_xlsx = resolve_output_path(first, "xlsx", suffix_tag="_combined")
        master_wb = openpyxl.Workbook()
        default_ws = master_wb.active
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(source_paths):
                src = Path(src).resolve()
                tmp_xlsx = Path(tmpdir) / f"part_{idx}.xlsx"
                if src.suffix.lower() == ".xlsx":
                    shutil.copy2(src, tmp_xlsx)
                else:
                    convert_file(src, "XLSX", output_path=tmp_xlsx, settings=settings)

                sub_wb = openpyxl.load_workbook(tmp_xlsx, data_only=True)
                sub_ws = sub_wb.active
                ws = default_ws if idx == 0 else master_wb.create_sheet()
                ws.title = f"{idx + 1}_{src.stem[:20]}"
                for row in sub_ws.iter_rows(values_only=True):
                    ws.append(list(row))

        master_wb.save(out_xlsx)
        return out_xlsx

    # 5. Combine multiple images vertically into a single long image (PNG, JPG, WEBP)
    if tgt_ext in {"png", "jpg", "jpeg", "webp"}:
        out_img = resolve_output_path(first, tgt_ext, suffix_tag="_combined")
        loaded_imgs: list[Image.Image] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(source_paths):
                src = Path(src).resolve()
                if src.suffix.lower().lstrip(".") in {"png", "jpg", "jpeg", "webp", "bmp"}:
                    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
                else:
                    tmp_png = Path(tmpdir) / f"part_{idx}.png"
                    convert_file(src, "PNG", output_path=tmp_png, settings=settings)
                    im = Image.open(tmp_png).convert("RGB")
                loaded_imgs.append(im)

        max_w = max(im.width for im in loaded_imgs)
        resized: list[Image.Image] = []
        for im in loaded_imgs:
            if im.width != max_w:
                new_h = max(1, int(im.height * (max_w / im.width)))
                im = im.resize((max_w, new_h), Image.Resampling.LANCZOS)
            resized.append(im)

        total_h = sum(im.height for im in resized)
        canvas = Image.new("RGB", (max_w, total_h), (255, 255, 255))
        y_offset = 0
        for im in resized:
            canvas.paste(im, (0, y_offset))
            y_offset += im.height

        fmt = "JPEG" if tgt_ext in {"jpg", "jpeg"} else tgt_ext.upper()
        canvas.save(out_img, format=fmt, quality=int(settings.get("quality", 88)))
        return out_img

    # Fallback: Convert each file to target_format and bundle into a single ZIP
    out_zip = resolve_output_path(first, "zip", suffix_tag=f"_combined_{tgt_ext}")
    converted_parts: list[Path] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for src in source_paths:
            src = Path(src).resolve()
            dest = Path(tmpdir) / f"{src.stem}.{tgt_ext}"
            converted_parts.append(convert_file(src, target_format, output_path=dest, settings=settings))
        return create_zip_archive(converted_parts, out_zip, password=settings.get("zip_password"))
