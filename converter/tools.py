import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence
import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageOps


# ---------------------------------------------------------------------------
# 1. OFFLINE BACKGROUND REMOVAL (NO-BG)
# ---------------------------------------------------------------------------
def remove_background(source_path: Path, output_path: Path) -> Path:
    """Removes image background offline using corner flood-fill + GrabCut alpha matting."""
    with Image.open(source_path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img).convert("RGBA")
        rgba = np.array(pil_img)

    bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    h, w = bgr.shape[:2]

    # Sample border pixels to estimate background color distribution
    border_pixels = np.concatenate(
        [bgr[0, :], bgr[h - 1, :], bgr[:, 0], bgr[:, w - 1]], axis=0
    )
    bg_median = np.median(border_pixels, axis=0)
    diff = np.linalg.norm(bgr.astype(np.float32) - bg_median.astype(np.float32), axis=2)

    # Initial foreground mask from color distance
    alpha_mask = np.where(diff > 28.0, 255, 0).astype(np.uint8)

    # Refine with GrabCut when image has sufficient dimensions and foreground area
    if h >= 32 and w >= 32:
        try:
            gc_mask = np.where(alpha_mask > 0, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
            gc_mask[0:2, :] = cv2.GC_BGD
            gc_mask[h - 2 : h, :] = cv2.GC_BGD
            gc_mask[:, 0:2] = cv2.GC_BGD
            gc_mask[:, w - 2 : w] = cv2.GC_BGD
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            rect = (2, 2, max(1, w - 4), max(1, h - 4))
            cv2.grabCut(bgr, gc_mask, rect, bgd_model, fgd_model, 2, cv2.GC_INIT_WITH_MASK)
            refined = np.where(
                (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0
            ).astype(np.uint8)
            if np.count_nonzero(refined) > (h * w * 0.01):
                alpha_mask = refined
        except Exception:
            pass

    # Smooth edges for clean anti-aliased transparency
    alpha_mask = cv2.GaussianBlur(alpha_mask, (3, 3), 0)
    rgba[:, :, 3] = np.minimum(rgba[:, :, 3], alpha_mask)

    out_png = output_path.with_suffix(".png")
    Image.fromarray(rgba, mode="RGBA").save(out_png, format="PNG", optimize=True)
    return out_png


# ---------------------------------------------------------------------------
# 2. AES-256 PDF PASSWORD PROTECTION (LOCK-PDF)
# ---------------------------------------------------------------------------
def lock_pdf(source_path: Path, output_path: Path, password: str) -> Path:
    """Encrypts a PDF with 256-bit AES encryption."""
    pw = (password or "").strip() or "instant2026"
    doc = pymupdf.open(str(source_path))
    doc.save(
        str(output_path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw=pw,
        user_pw=pw,
        garbage=3,
        deflate=True,
    )
    doc.close()
    return output_path


# ---------------------------------------------------------------------------
# 3. DEDICATED COMPRESSION ENGINE (#tool-compress)
# ---------------------------------------------------------------------------
def compress_file(source_path: Path, output_path: Path, settings: dict) -> Path:
    ext = source_path.suffix.lower().lstrip(".")
    quality = int(settings.get("quality", 72))
    scale = float(settings.get("scale", 1.0))
    crf = int(settings.get("crf", 28))
    strip_meta = bool(settings.get("strip_meta", True))

    if ext in {"png", "jpg", "jpeg", "webp", "avif", "heic", "heif", "bmp", "tiff"}:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            if scale < 1.0:
                new_w = max(1, int(img.width * scale))
                new_h = max(1, int(img.height * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            if ext == "png":
                if quality < 90:
                    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                img.save(output_path, format="PNG", optimize=True)
            elif ext in {"webp", "avif"}:
                img.save(output_path, format=ext.upper(), quality=quality, method=6)
            else:
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    rgba = img.convert("RGBA")
                    bg.paste(rgba, mask=rgba.split()[3])
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                save_kwargs = {"quality": quality, "optimize": True, "progressive": True}
                if not strip_meta and "exif" in img.info:
                    save_kwargs["exif"] = img.info["exif"]
                img.save(output_path, format="JPEG", **save_kwargs)
        return output_path

    if ext == "pdf":
        doc = pymupdf.open(str(source_path))
        if strip_meta:
            doc.set_metadata({})
            try:
                doc.del_xml_metadata()
            except Exception:
                pass
        if hasattr(doc, "rewrite_images"):
            dpi_target = 110 if quality < 60 else 150
            try:
                doc.rewrite_images(dpi_threshold=dpi_target + 30, dpi_target=dpi_target, quality=quality)
            except Exception:
                pass
        doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        doc.close()
        return output_path

    if ext in {"mp4", "mov", "mkv", "webm", "avi", "wmv"}:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required for video compression.")
        cmd = [ffmpeg, "-y", "-i", str(source_path)]
        if scale < 1.0:
            cmd.extend(["-vf", f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"])
        if strip_meta:
            cmd.extend(["-map_metadata", "-1"])
        cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-c:a", "aac", "-b:a", "128k", str(output_path)])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode != 0 or not output_path.exists():
            raise RuntimeError(f"Video compression failed: {res.stderr[-200:]}")
        return output_path

    if ext in {"mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "wma"}:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required for audio compression.")
        bitrate = "96k" if quality < 60 else ("128k" if quality < 85 else "192k")
        out_mp3 = output_path.with_suffix(".mp3") if ext in {"wav", "aiff", "flac"} else output_path
        cmd = [ffmpeg, "-y", "-i", str(source_path), "-map_metadata", "-1", "-b:a", bitrate, str(out_mp3)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode != 0 or not out_mp3.exists():
            raise RuntimeError(f"Audio compression failed: {res.stderr[-200:]}")
        return out_mp3

    zip_out = output_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(source_path, arcname=source_path.name)
    return zip_out


# ---------------------------------------------------------------------------
# 4. METADATA SCRUBBER / PRIVACY CLEANER (NO-META)
# ---------------------------------------------------------------------------
def strip_metadata(source_path: Path, output_path: Path) -> Path:
    ext = source_path.suffix.lower().lstrip(".")

    if ext in {"png", "jpg", "jpeg", "webp", "bmp", "tiff"}:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            clean_img = img.copy()
            clean_img.info.clear()
            fmt = "JPEG" if ext in {"jpg", "jpeg"} else ext.upper()
            clean_img.save(output_path, format=fmt, quality=95)
        return output_path

    if ext == "pdf":
        doc = pymupdf.open(str(source_path))
        doc.set_metadata({})
        try:
            doc.del_xml_metadata()
        except Exception:
            pass
        doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        doc.close()
        return output_path

    if ext == "docx":
        from docx import Document
        doc = Document(str(source_path))
        props = doc.core_properties
        props.author = ""
        props.comments = ""
        props.last_modified_by = ""
        props.title = ""
        props.subject = ""
        doc.save(str(output_path))
        return output_path

    if shutil.which("ffmpeg") and ext in {"mp4", "mov", "mkv", "webm", "mp3", "m4a", "flac", "ogg", "wav"}:
        cmd = [shutil.which("ffmpeg"), "-y", "-i", str(source_path), "-map_metadata", "-1", "-c", "copy", str(output_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode == 0 and output_path.exists():
            return output_path

    shutil.copy2(source_path, output_path)
    return output_path


# ---------------------------------------------------------------------------
# 5. SMART PDF REDACTION (REDACT)
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{3,5}[\s-]?\d{4,8}")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")


def redact_pdf(source_path: Path, output_path: Path, custom_terms: str = "", redact_pii: bool = True) -> Path:
    doc = pymupdf.open(str(source_path))
    extra_words = [w.strip() for w in custom_terms.split(",") if w.strip()]

    for page in doc:
        text = page.get_text("text") or ""
        targets: set[str] = set(extra_words)
        if redact_pii:
            targets.update(_EMAIL_RE.findall(text))
            targets.update(_PHONE_RE.findall(text))
            targets.update(_IBAN_RE.findall(text))

        for target in targets:
            if len(target) < 3:
                continue
            for rect in page.search_for(target):
                page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.set_metadata({})
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()
    return output_path


# ---------------------------------------------------------------------------
# 6. PDF ALL PAGES AT 300 DPI & PDF -> PPTX SLIDES
# ---------------------------------------------------------------------------
def pdf_all_pages_to_images(source_path: Path, output_path: Path, img_ext: str = "png", dpi: int = 300) -> Path:
    with pymupdf.open(str(source_path)) as doc:
        if len(doc) == 0:
            raise ValueError("Cannot render an empty PDF.")
        if len(doc) == 1:
            pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
            pix.save(str(output_path))
            return output_path

        out_dir = source_path.parent / f"{source_path.stem}_{img_ext.upper()}_{dpi}DPI"
        out_dir.mkdir(parents=True, exist_ok=True)
        first_saved = None
        for idx, page in enumerate(doc, start=1):
            page_file = out_dir / f"{source_path.stem}_page_{idx:03d}.{img_ext}"
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            pix.save(str(page_file))
            if first_saved is None:
                first_saved = page_file
        return first_saved or output_path


def pdf_to_pptx(source_path: Path, output_path: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    with pymupdf.open(str(source_path)) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200, alpha=False)
            img_bytes = io.BytesIO(pix.tobytes("png"))
            slide = prs.slides.add_slide(blank_layout)
            slide.shapes.add_picture(img_bytes, 0, 0, width=prs.slide_width, height=prs.slide_height)
    prs.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# 7. SUBTITLES ENGINE & ZIP HELPER
# ---------------------------------------------------------------------------
_TIMESTAMP_LINE_RE = re.compile(r"^\d{2}:\d{2}[:.]\d{2}.*-->.*$")
_INDEX_LINE_RE = re.compile(r"^\d+$")


def convert_subtitles(source_path: Path, output_path: Path, target_format: str) -> Path:
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    src_ext = source_path.suffix.lower().lstrip(".")
    tgt_ext = target_format.lower().lstrip(".")

    if tgt_ext == "txt":
        clean_lines: list[str] = []
        for line in raw.splitlines():
            s = line.strip()
            if not s or s.upper().startswith("WEBVTT") or _INDEX_LINE_RE.match(s) or _TIMESTAMP_LINE_RE.match(s):
                continue
            s = re.sub(r"<[^>]+>", "", s)
            clean_lines.append(s)
        output_path.write_text("\n".join(clean_lines), encoding="utf-8")
        return output_path

    if src_ext == "srt" and tgt_ext == "vtt":
        vtt_body = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", raw)
        output_path.write_text("WEBVTT\n\n" + vtt_body.lstrip(), encoding="utf-8")
        return output_path

    if src_ext == "vtt" and tgt_ext == "srt":
        lines = [ln for ln in raw.splitlines() if not ln.strip().upper().startswith("WEBVTT")]
        srt_body = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{3})", r"\1,\2", "\n".join(lines).lstrip())
        output_path.write_text(srt_body, encoding="utf-8")
        return output_path

    output_path.write_text(raw, encoding="utf-8")
    return output_path


def create_zip_archive(
    source_paths: Sequence[Path],
    output_path: Path,
    password: str | None = None,
) -> Path:
    clean_pw = (password or "").strip()
    if clean_pw:
        import pyzipper
        with pyzipper.AESZipFile(
            output_path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(clean_pw.encode("utf-8"))
            for p in source_paths:
                if p.is_file():
                    zf.write(p, arcname=p.name)
        return output_path

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in source_paths:
            if p.is_file():
                zf.write(p, arcname=p.name)
    return output_path
