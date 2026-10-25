import shutil
import tempfile
from pathlib import Path
import pymupdf
from PIL import Image
from docx import Document

_RAPID_OCR_INSTANCE = None


def _get_rapid_ocr():
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        from rapidocr_onnxruntime import RapidOCR
        _RAPID_OCR_INSTANCE = RapidOCR()
    return _RAPID_OCR_INSTANCE


def ocr_image_to_text(image_path: Path) -> str:
    """Extracts text from an image offline using RapidOCR (ONNX) or Tesseract fallback."""
    # 1. Primary: Self-contained ONNX RapidOCR
    try:
        engine = _get_rapid_ocr()
        result, _ = engine(str(image_path))
        if result:
            lines = [item[1] for item in result if len(item) > 1 and str(item[1]).strip()]
            if lines:
                return "\n".join(lines)
    except Exception:
        pass

    # 2. Fallback: System Tesseract if installed
    if shutil.which("tesseract"):
        try:
            import pytesseract
            with Image.open(image_path) as img:
                text = pytesseract.image_to_string(img)
                if text and text.strip():
                    return text.strip()
        except Exception:
            pass

    return ""


def ocr_pdf_to_text(pdf_path: Path) -> str:
    """Renders scanned PDF pages at 200 DPI and performs offline OCR on each page."""
    pages_text: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        with pymupdf.open(str(pdf_path)) as doc:
            for idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200, alpha=False)
                img_path = Path(tmpdir) / f"page_{idx}.png"
                pix.save(str(img_path))
                page_txt = ocr_image_to_text(img_path)
                if page_txt.strip():
                    pages_text.append(page_txt.strip())
    return "\n\n".join(pages_text)


def image_to_txt(source_path: Path, output_path: Path) -> Path:
    text = ocr_image_to_text(source_path)
    output_path.write_text(text or "[No text detected by OCR]", encoding="utf-8")
    return output_path


def image_to_docx(source_path: Path, output_path: Path) -> Path:
    text = ocr_image_to_text(source_path) or "[No text detected by OCR]"
    doc = Document()
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    doc.save(str(output_path))
    return output_path
