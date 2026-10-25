import html
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
import pymupdf
from docx import Document


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
        f"<title>{html.escape(title)}</title>\n"
        "<style>body{font-family:sans-serif;line-height:1.5;margin:40px;color:#18181b;}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def extract_plain_text(source_path: Path) -> str:
    ext = source_path.suffix.lower().lstrip(".")
    if ext == "docx":
        doc = Document(str(source_path))
        parts = [p.text for p in doc.paragraphs if p.text]
        for table in doc.tables:
            for row in table.rows:
                parts.append("\t".join(cell.text.strip() for cell in row.cells))
        return "\n".join(parts)
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    if ext == "html":
        return _strip_html(raw)
    return raw


def _render_vector_pdf(text: str, output_path: Path) -> Path:
    """Generates a true vector, searchable PDF with selectable text via PyMuPDF."""
    doc = pymupdf.open()
    page_width, page_height = 595.0, 842.0  # A4 in points
    margin = 50.0
    fontsize = 11.0
    line_height = 16.0
    max_lines_per_page = int((page_height - 2 * margin) // line_height)

    wrapped_lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(textwrap.wrap(raw_line, width=82))

    if not wrapped_lines:
        wrapped_lines = [""]

    for i in range(0, len(wrapped_lines), max_lines_per_page):
        chunk = wrapped_lines[i : i + max_lines_per_page]
        page = doc.new_page(width=page_width, height=page_height)
        y = margin + fontsize
        for line in chunk:
            page.insert_text(
                (margin, y),
                line,
                fontsize=fontsize,
                fontname="helv",
                color=(0.08, 0.08, 0.09),
            )
            y += line_height

    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()
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
            stripped = line.strip()
            if stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("### "):
                doc.add_heading(stripped[4:], level=3)
            else:
                doc.add_paragraph(line)
        doc.save(str(output_path))
        return output_path

    if tgt_ext == "pdf":
        soffice = _find_libreoffice()
        if soffice and src_ext in {"docx", "html"}:
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
        return _render_vector_pdf(text, output_path)

    raise ValueError(f"Unsupported document target format: {target_format}")
