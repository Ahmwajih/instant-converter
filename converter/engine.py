from pathlib import Path
from converter.detection import (
    DOCUMENT_FORMATS,
    IMAGE_FORMATS,
    MEDIA_FORMATS,
    get_available_targets,
    get_extension,
    resolve_output_path,
)
from converter.images import convert_image
from converter.pdf import pdf_to_docx, pdf_to_html, pdf_to_png, pdf_to_txt
from converter.documents import convert_document
from converter.media import convert_media


def convert_file(
    source_path: Path, target_format: str, output_path: Path | None = None
) -> Path:
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    src_ext = get_extension(source_path)
    tgt_ext = target_format.lower().lstrip(".")

    available = [t.lower() for t in get_available_targets(source_path)]
    if tgt_ext not in available:
        raise ValueError(f"Conversion from .{src_ext} to .{tgt_ext} is not supported.")

    final_output = output_path or resolve_output_path(source_path, tgt_ext)

    # 1. GIF to MP4 uses FFmpeg
    if src_ext == "gif" and tgt_ext == "mp4":
        return convert_media(source_path, final_output, tgt_ext)

    # 2. Images
    if src_ext in IMAGE_FORMATS:
        return convert_image(source_path, final_output, tgt_ext)

    # 3. PDF
    if src_ext == "pdf":
        if tgt_ext in {"txt", "md"}:
            return pdf_to_txt(source_path, final_output)
        if tgt_ext == "docx":
            return pdf_to_docx(source_path, final_output)
        if tgt_ext == "html":
            return pdf_to_html(source_path, final_output)
        if tgt_ext == "png":
            return pdf_to_png(source_path, final_output)

    # 4. Documents (DOCX, TXT, MD, HTML)
    if src_ext in DOCUMENT_FORMATS:
        return convert_document(source_path, final_output, tgt_ext)

    # 5. Audio & Video (FFmpeg)
    if src_ext in MEDIA_FORMATS:
        return convert_media(source_path, final_output, tgt_ext)

    raise ValueError(f"Unhandled conversion route: {src_ext} -> {tgt_ext}")
