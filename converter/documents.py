import html
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from docx import Document
from PIL import Image, ImageDraw, ImageFont


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _text_to_html(text: str, title: str = "Document") -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            lines.append(f"<h3>{html.escape(stripped[4:])}</h3>")
        elif stripped:
            lines.append(f"<p>{html.escape(stripped)}</p>")
    body = "\n".join(lines)
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n"
        f"<title>{html.escape(title)}</title>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def extract_plain_text(source_path: Path) -> str:
    ext = source_path.suffix.lower().lstrip(".")
    if ext == "docx":
        doc = Document(str(source_path))
        return "\n".join(p.text for p in doc.paragraphs)
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    if ext == "html":
        return _strip_html(raw)
    return raw


def _render_text_to_pdf_fallback(text: str, output_path: Path) -> Path:
    page_width, page_height = 1240, 1754
    margin = 100
    line_height = 32
    max_lines_per_page = (page_height - 2 * margin) // line_height

    wrapped_lines = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(textwrap.wrap(raw_line, width=85))

    if not wrapped_lines:
        wrapped_lines = [""]

    font = ImageFont.load_default()
    pages = []

    for i in range(0, len(wrapped_lines), max_lines_per_page):
        chunk = wrapped_lines[i : i + max_lines_per_page]
        page_img = Image.new("RGB", (page_width, page_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(page_img)
        y = margin
        for line in chunk:
            draw.text((margin, y), line, fill=(20, 20, 20), font=font)
            y += line_height
        pages.append(page_img)

    first_page, *rest_pages = pages
    first_page.save(
        output_path,
        format="PDF",
        resolution=150.0,
        save_all=True,
        append_images=rest_pages,
    )
    return output_path


def _find_libreoffice() -> str | None:
    for binary in ("soffice", "libreoffice"):
        found = shutil.which(binary)
        if found:
            return found
    return None


def convert_document(source_path: Path, output_path: Path, target_format: str) -> Path:
    src_ext = source_path.suffix.lower().lstrip(".")
    tgt_ext = target_format.lower().lstrip(".")
    text = extract_plain_text(source_path)

    if tgt_ext in {"txt", "md"}:
        output_path.write_text(text, encoding="utf-8")
        return output_path

    if tgt_ext == "html":
        html_content = _text_to_html(text, title=source_path.stem)
        output_path.write_text(html_content, encoding="utf-8")
        return output_path

    if tgt_ext == "docx":
        doc = Document()
        for line in text.splitlines():
            doc.add_paragraph(line)
        doc.save(str(output_path))
        return output_path

    if tgt_ext == "pdf":
        if src_ext == "docx":
            soffice = _find_libreoffice()
            if soffice:
                with tempfile.TemporaryDirectory() as tmpdir:
                    cmd = [
                        soffice,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        tmpdir,
                        str(source_path),
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    generated = Path(tmpdir) / f"{source_path.stem}.pdf"
                    if res.returncode == 0 and generated.exists():
                        shutil.move(str(generated), str(output_path))
                        return output_path
        return _render_text_to_pdf_fallback(text, output_path)

    raise ValueError(f"Unsupported document target format: {target_format}")
