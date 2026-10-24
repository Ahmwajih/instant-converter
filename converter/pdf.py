import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence
from pypdf import PdfReader, PdfWriter
from docx import Document
from PIL import Image, ImageDraw, ImageFont
from converter.documents import _text_to_html


def extract_text_from_pdf(source_path: Path) -> str:
    reader = PdfReader(str(source_path))
    pages_text = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        pages_text.append(extracted.strip())
    return "\n\n".join(filter(None, pages_text))


def pdf_to_txt(source_path: Path, output_path: Path) -> Path:
    text = extract_text_from_pdf(source_path)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def pdf_to_html(source_path: Path, output_path: Path) -> Path:
    text = extract_text_from_pdf(source_path)
    output_path.write_text(_text_to_html(text, source_path.stem), encoding="utf-8")
    return output_path


def pdf_to_docx(source_path: Path, output_path: Path) -> Path:
    reader = PdfReader(str(source_path))
    doc = Document()
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            for paragraph in text.splitlines():
                if paragraph.strip():
                    doc.add_paragraph(paragraph)
        if idx < len(reader.pages) - 1:
            doc.add_page_break()
    doc.save(str(output_path))
    return output_path


def pdf_to_png(source_path: Path, output_path: Path) -> Path:
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = str(Path(tmpdir) / "page")
            cmd = [pdftoppm, "-png", "-singlefile", str(source_path), prefix]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            rendered = Path(f"{prefix}.png")
            if res.returncode == 0 and rendered.exists():
                shutil.move(str(rendered), str(output_path))
                return output_path

    # Pure-Python fallback if poppler-utils is not installed
    text = extract_text_from_pdf(source_path) or "PDF Preview"
    img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    y = 80
    for line in text.splitlines()[:48]:
        draw.text((80, y), line[:90], fill=(20, 20, 20), font=font)
        y += 32
    img.save(output_path, format="PNG")
    return output_path


def merge_pdfs(source_paths: Sequence[Path], output_path: Path) -> Path:
    writer = PdfWriter()
    for path in source_paths:
        writer.append(str(path))
    with output_path.open("wb") as f_out:
        writer.write(f_out)
    return output_path
