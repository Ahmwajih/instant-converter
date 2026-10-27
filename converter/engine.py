import shutil
import subprocess
import tempfile
from pathlib import Path
from converter.detection import (
    DATA_FORMATS,
    DOCUMENT_FORMATS,
    EBOOK_FORMATS,
    IMAGE_FORMATS,
    MEDIA_FORMATS,
    SLIDE_FORMATS,
    SUBTITLE_FORMATS,
    get_available_targets,
    get_extension,
    resolve_output_path,
)
from converter.data_formats import convert_data
from converter.documents import convert_document
from converter.ebooks import convert_ebook
from converter.images import convert_image
from converter.media import convert_media
from converter.pdf import (
    pdf_to_csv,
    pdf_to_docx,
    pdf_to_html,
    pdf_to_svg,
    pdf_to_txt,
    pdf_to_xlsx,
)
from converter.tools import (
    compress_file,
    convert_subtitles,
    create_zip_archive,
    lock_pdf,
    pdf_all_pages_to_images,
    pdf_to_pptx,
    redact_pdf,
    remove_background,
    strip_metadata,
)


def convert_file(
    source_path: Path,
    target_format: str,
    output_path: Path | None = None,
    settings: dict | None = None,
) -> Path:
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    settings = settings or {}
    src_ext = get_extension(source_path)
    action = target_format.upper().strip()
    tgt_ext = target_format.lower().lstrip(".")

    # --- A. PRO TOOLS ACTIONS ---
    if action == "EDIT-PDF":
        out = output_path or resolve_output_path(source_path, "pdf", suffix_tag="_edited")
        shutil.copy2(source_path, out)
        return out

    if action == "NO-BG":
        out = output_path or resolve_output_path(source_path, "png", suffix_tag="_nobg")
        return remove_background(source_path, out)

    if action == "LOCK-PDF":
        out = output_path or resolve_output_path(source_path, "pdf", suffix_tag="_locked")
        return lock_pdf(source_path, out, password=settings.get("pdf_password", "instant2026"))

    if action == "COMPRESS":
        out = output_path or resolve_output_path(source_path, src_ext, suffix_tag="_compressed")
        return compress_file(source_path, out, settings)

    if action == "NO-META":
        out = output_path or resolve_output_path(source_path, src_ext, suffix_tag="_clean")
        return strip_metadata(source_path, out)

    if action == "REDACT" and src_ext == "pdf":
        out = output_path or resolve_output_path(source_path, "pdf", suffix_tag="_redacted")
        return redact_pdf(
            source_path,
            out,
            custom_terms=settings.get("redact_terms", ""),
            redact_pii=settings.get("redact_pii", True),
        )

    if action == "ALL-PNG" and src_ext == "pdf":
        out = output_path or resolve_output_path(source_path, "png")
        return pdf_all_pages_to_images(source_path, out, img_ext="png", dpi=int(settings.get("dpi", 300)))

    if action == "OCR-TXT" and src_ext in IMAGE_FORMATS:
        out = output_path or resolve_output_path(source_path, "txt", suffix_tag="_ocr")
        return convert_image(source_path, out, "txt")

    if action == "ZIP":
        out = output_path or resolve_output_path(source_path, "zip")
        return create_zip_archive([source_path], out, password=settings.get("zip_password"))

    # --- B. STANDARD FORMAT CONVERSIONS ---
    available = [t.lower() for t in get_available_targets(source_path, mode="convert")]
    if tgt_ext not in available:
        raise ValueError(f"Conversion from .{src_ext} to .{tgt_ext} is not supported.")

    final_output = output_path or resolve_output_path(source_path, tgt_ext)

    if src_ext in SUBTITLE_FORMATS:
        return convert_subtitles(source_path, final_output, tgt_ext)

    if src_ext in SLIDE_FORMATS:
        soffice = shutil.which("libreoffice") or shutil.which("soffice")
        if not soffice:
            raise RuntimeError("LibreOffice is required to convert presentation slides.")
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_uri = Path(tmpdir).as_uri() + "/lo_profile"
            conv_target = "pdf" if tgt_ext in {"pdf", "png", "jpg"} else tgt_ext
            cmd = [
                soffice, f"-env:UserInstallation={profile_uri}",
                "--headless", "--convert-to", conv_target, "--outdir", tmpdir, str(source_path)
            ]
            subprocess.run(cmd, capture_output=True, timeout=90)
            gen_pdf = Path(tmpdir) / f"{source_path.stem}.{conv_target}"
            if not gen_pdf.exists():
                raise RuntimeError("Slide conversion failed via LibreOffice.")
            if tgt_ext in {"pdf", "pptx"}:
                shutil.move(str(gen_pdf), str(final_output))
                return final_output
            return pdf_all_pages_to_images(gen_pdf, final_output, img_ext=tgt_ext, dpi=int(settings.get("dpi", 300)))

    if src_ext == "gif" and tgt_ext == "mp4":
        return convert_media(source_path, final_output, tgt_ext, settings=settings)

    if src_ext in IMAGE_FORMATS:
        if settings.get("custom_live") and tgt_ext in {"jpg", "jpeg", "png", "webp", "avif"}:
            return compress_file(source_path, final_output, settings)
        return convert_image(source_path, final_output, tgt_ext)

    if src_ext == "pdf":
        if tgt_ext in {"txt", "md"}:
            return pdf_to_txt(source_path, final_output)
        if tgt_ext == "docx":
            return pdf_to_docx(source_path, final_output)
        if tgt_ext == "pptx":
            return pdf_to_pptx(source_path, final_output)
        if tgt_ext == "xlsx":
            return pdf_to_xlsx(source_path, final_output)
        if tgt_ext == "csv":
            return pdf_to_csv(source_path, final_output)
        if tgt_ext == "html":
            return pdf_to_html(source_path, final_output)
        if tgt_ext == "svg":
            return pdf_to_svg(source_path, final_output)
        if tgt_ext in {"png", "jpg", "jpeg"}:
            return pdf_all_pages_to_images(
                source_path, final_output, img_ext=tgt_ext, dpi=int(settings.get("dpi", 300))
            )

    if src_ext in EBOOK_FORMATS:
        return convert_ebook(source_path, final_output, tgt_ext)

    if src_ext in DATA_FORMATS:
        return convert_data(source_path, final_output, tgt_ext)

    if src_ext in DOCUMENT_FORMATS:
        return convert_document(source_path, final_output, tgt_ext)

    if src_ext in MEDIA_FORMATS:
        return convert_media(source_path, final_output, tgt_ext, settings=settings)

    raise ValueError(f"Unhandled conversion route: {src_ext} -> {tgt_ext}")
