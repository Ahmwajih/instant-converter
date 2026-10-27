import csv
import re
import sys
import tempfile
from pathlib import Path
from typing import Sequence
import openpyxl
from openpyxl.styles import Font
import pymupdf

sys.modules.setdefault("fitz", pymupdf)
from pdf2docx import Converter
from pypdf import PdfWriter
from docx import Document
from docx.oxml.ns import qn
from converter.ocr import ocr_pdf_to_text

_BROWSER_HEADER_FOOTER_RE = re.compile(
    r"^(\d+\s*(von|of|/)\s*\d+|\d{1,2}[./]\d{1,2}[./]\d{2,4},?\s*\d{1,2}:\d{2})$",
    re.IGNORECASE,
)


def _collapse_doubled_string(text: str) -> str:
    """Détecte et corrige une chaîne doublée exactement (ex: 'ABCABC' ou 'Phrase.Phrase.')."""
    s = text.strip()
    n = len(s)
    if n >= 6 and n % 2 == 0:
        half = n // 2
        if s[:half] == s[half:]:
            return s[:half]
    # Cas où un espace sépare le doublon
    if n >= 7 and n % 2 == 1 and s[n // 2] == " ":
        half = n // 2
        if s[:half] == s[half + 1 :]:
            return s[:half]
    return text


def _postprocess_docx(docx_path: Path) -> None:
    """Nettoie les doublons de calques PDF et les boîtes noires dans le fichier Word généré."""
    doc = Document(str(docx_path))

    def clean_paragraph(p) -> None:
        # 1. Supprimer les runs consécutifs strictement identiques (ex: badges doublés)
        prev_text = None
        for run in p.runs:
            t = run.text.strip()
            if not t:
                continue
            cleaned_t = _collapse_doubled_string(run.text)
            if cleaned_t != run.text:
                run.text = cleaned_t
                t = cleaned_t.strip()
            if prev_text is not None and t == prev_text:
                run.text = ""
            else:
                # Ajouter un espace si deux badges consécutifs sont collés
                if prev_text is not None and not run.text.startswith((" ", ".", ",", ";", ":", "-", "/")):
                    run.text = "  " + run.text
                prev_text = t

        # 2. Si le paragraphe complet est doublé (ex: Tools & Technologien...Tools & Technologien...)
        full = p.text.strip()
        collapsed = _collapse_doubled_string(full)
        if collapsed != full and p.runs:
            p.runs[0].text = collapsed
            for r in p.runs[1:]:
                r.text = ""

        # 3. Supprimer les en-têtes/pieds de page d'impression navigateur (ex: "1 von 6", "29/04/2026, 08:19")
        if _BROWSER_HEADER_FOOTER_RE.match(p.text.strip()):
            for r in p.runs:
                r.text = ""

    for para in doc.paragraphs:
        clean_paragraph(para)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    clean_paragraph(para)

    # 4. Supprimer les petites images/boîtes noires générées à partir des cadres de badges
    for shape in list(doc.inline_shapes):
        try:
            # Si l'image est un petit badge (< 45mm de large et < 18mm de haut)
            if shape.width < 1600000 and shape.height < 650000:
                inline = shape._inline
                inline.getparent().remove(inline)
        except Exception:
            pass

    doc.save(str(docx_path))


def extract_text_from_pdf(source_path: Path) -> str:
    pages_text = []
    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            lines = []
            for raw_line in (page.get_text("text", sort=True) or "").splitlines():
                stripped = raw_line.strip()
                if stripped and not _BROWSER_HEADER_FOOTER_RE.match(stripped):
                    lines.append(_collapse_doubled_string(stripped))
            if lines:
                pages_text.append("\n".join(lines))

    combined = "\n\n".join(pages_text)
    if not combined.strip():
        combined = ocr_pdf_to_text(source_path)
    return combined


def _extract_tables_from_pdf(source_path: Path) -> list[list[list[str]]]:
    extracted_tables: list[list[list[str]]] = []
    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            try:
                finder = page.find_tables()
                for table in finder.tables:
                    rows = [
                        ["" if cell is None else _collapse_doubled_string(str(cell).strip()) for cell in row]
                        for row in table.extract()
                    ]
                    if rows:
                        extracted_tables.append(rows)
            except Exception:
                pass

        if not extracted_tables:
            fallback_rows: list[list[str]] = []
            for page in doc:
                text = page.get_text("text", sort=True) or ""
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and not _BROWSER_HEADER_FOOTER_RE.match(stripped):
                        cols = [c.strip() for c in re.split(r"\s{2,}|\t", stripped) if c.strip()]
                        fallback_rows.append(cols if cols else [stripped])
            if fallback_rows:
                extracted_tables.append(fallback_rows)

    return extracted_tables


def pdf_to_xlsx(source_path: Path, output_path: Path) -> Path:
    tables = _extract_tables_from_pdf(source_path)
    wb = openpyxl.Workbook()
    default_sheet = wb.active

    if not tables:
        default_sheet.title = "Extracted"
        text = extract_text_from_pdf(source_path)
        for line in text.splitlines():
            default_sheet.append([line])
    else:
        for idx, table in enumerate(tables):
            ws = default_sheet if idx == 0 else wb.create_sheet(title=f"Table_{idx + 1}")
            if idx == 0:
                ws.title = "Table_1"
            for r_idx, row in enumerate(table):
                ws.append(row)
                if r_idx == 0:
                    for cell in ws[1]:
                        cell.font = Font(bold=True)

    wb.save(output_path)
    return output_path


def pdf_to_csv(source_path: Path, output_path: Path) -> Path:
    tables = _extract_tables_from_pdf(source_path)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for idx, table in enumerate(tables):
            for row in table:
                writer.writerow(row)
            if idx < len(tables) - 1:
                writer.writerow([])
    return output_path


def pdf_to_txt(source_path: Path, output_path: Path) -> Path:
    text = extract_text_from_pdf(source_path)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def pdf_to_html(source_path: Path, output_path: Path) -> Path:
    html_pages = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{source_path.stem}</title>"
        "<style>body{background:#f4f4f5;margin:20px;font-family:sans-serif;}"
        ".page{background:#fff;margin:16px auto;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.1);}</style>"
        "</head><body>"
    ]
    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            html_pages.append(f"<div class='page'>{page.get_text('html')}</div>")
    html_pages.append("</body></html>")
    output_path.write_text("\n".join(html_pages), encoding="utf-8")
    return output_path


def pdf_to_docx(source_path: Path, output_path: Path) -> Path:
    """Convertit un PDF en DOCX avec nettoyage des calques doublés et des formes parasites."""
    has_text_layer = False
    with pymupdf.open(str(source_path)) as check_doc:
        for page in check_doc:
            if (page.get_text("text") or "").strip():
                has_text_layer = True
                break

    if has_text_layer:
        cv = Converter(str(source_path))
        try:
            cv.convert(str(output_path), multi_processing=False)
        finally:
            cv.close()

        if output_path.exists() and output_path.stat().st_size > 0:
            _postprocess_docx(output_path)
            return output_path

    text = extract_text_from_pdf(source_path)
    doc = Document()
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    doc.save(str(output_path))
    return output_path


def pdf_to_png(source_path: Path, output_path: Path) -> Path:
    with pymupdf.open(str(source_path)) as doc:
        if len(doc) == 0:
            raise ValueError("Cannot render an empty PDF.")
        pix = doc[0].get_pixmap(dpi=300, alpha=False)
        pix.save(str(output_path))
    return output_path


def merge_pdfs(source_paths: Sequence[Path], output_path: Path) -> Path:
    writer = PdfWriter()
    for path in source_paths:
        writer.append(str(path))
    with output_path.open("wb") as f_out:
        writer.write(f_out)
    return output_path


def pdf_to_svg(source_path: Path, output_path: Path) -> Path:
    """Exports PDF page(s) to scalable vector SVG using PyMuPDF."""
    with pymupdf.open(str(source_path)) as doc:
        if len(doc) == 0:
            raise ValueError("Cannot export an empty PDF to SVG.")
        if len(doc) == 1:
            output_path.write_text(doc[0].get_svg_image(), encoding="utf-8")
            return output_path
        out_dir = source_path.parent / f"{source_path.stem}_SVG_Pages"
        out_dir.mkdir(parents=True, exist_ok=True)
        first_svg = None
        for idx, page in enumerate(doc, start=1):
            svg_file = out_dir / f"{source_path.stem}_page_{idx:03d}.svg"
            svg_file.write_text(page.get_svg_image(), encoding="utf-8")
            if first_svg is None:
                first_svg = svg_file
        return first_svg or output_path
