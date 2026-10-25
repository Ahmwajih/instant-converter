import tempfile
from pathlib import Path
import pymupdf
from converter.pdf import pdf_to_docx, pdf_to_html, pdf_to_png, pdf_to_txt


def convert_ebook(source_path: Path, output_path: Path, target_format: str) -> Path:
    """Converts EPUB, FB2, XPS, and CBZ files using PyMuPDF's native layout engine."""
    tgt = target_format.lower().lstrip(".")

    with pymupdf.open(str(source_path)) as ebook_doc:
        pdf_bytes = ebook_doc.convert_to_pdf()

    if tgt == "pdf":
        output_path.write_bytes(pdf_bytes)
        return output_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / f"{source_path.stem}.pdf"
        tmp_pdf.write_bytes(pdf_bytes)

        if tgt == "docx":
            return pdf_to_docx(tmp_pdf, output_path)
        if tgt in {"txt", "md"}:
            return pdf_to_txt(tmp_pdf, output_path)
        if tgt == "html":
            return pdf_to_html(tmp_pdf, output_path)
        if tgt == "png":
            return pdf_to_png(tmp_pdf, output_path)

    raise ValueError(f"Unsupported e-book target format: {target_format}")
