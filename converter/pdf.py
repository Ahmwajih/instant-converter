import csv
import re
import sys
from pathlib import Path
from typing import Sequence
import openpyxl
from openpyxl.styles import Font
import pymupdf

sys.modules.setdefault("fitz", pymupdf)
from pdf2docx import Converter
from pypdf import PdfWriter
from docx import Document
from converter.ocr import ocr_pdf_to_text


def extract_text_from_pdf(source_path: Path) -> str:
    pages_text = []
    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            extracted = page.get_text("text", sort=True) or ""
            if extracted.strip():
                pages_text.append(extracted.strip())

    combined = "\n\n".join(pages_text)
    if not combined.strip():
        # Scanned PDF detected -> Run automatic offline OCR
        combined = ocr_pdf_to_text(source_path)
    return combined


def _extract_tables_from_pdf(source_path: Path) -> list[list[list[str]]]:
    """Extracts structured tables from PDF pages using PyMuPDF's table finder with line fallback."""
    extracted_tables: list[list[list[str]]] = []
    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            try:
                finder = page.find_tables()
                for table in finder.tables:
                    rows = [
                        ["" if cell is None else str(cell).strip() for cell in row]
                        for row in table.extract()
                    ]
                    if rows:
                        extracted_tables.append(rows)
            except Exception:
                pass

        # Fallback if PDF tables have no borders/gridlines
        if not extracted_tables:
            fallback_rows: list[list[str]] = []
            for page in doc:
                text = page.get_text("text", sort=True) or ""
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped:
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
    """Converts PDF to DOCX preserving layout, with automatic OCR fallback for scanned PDFs."""
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
            return output_path

    # Scanned PDF or fallback route -> OCR + python-docx
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
