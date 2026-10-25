import io
from pathlib import Path
import pymupdf
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

from converter.ocr import image_to_docx, image_to_txt

PILLOW_FORMAT_MAP = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "ico": "ICO",
    "tiff": "TIFF",
    "gif": "GIF",
    "pdf": "PDF",
}


def _open_image_or_svg(source_path: Path) -> Image.Image:
    if source_path.suffix.lower() == ".svg":
        with pymupdf.open(str(source_path)) as doc:
            pix = doc[0].get_pixmap(dpi=300, alpha=True)
            return Image.open(io.BytesIO(pix.tobytes("png")))
    return Image.open(source_path)


def convert_image(source_path: Path, output_path: Path, target_format: str) -> Path:
    fmt_key = target_format.lower().lstrip(".")

    # Offline OCR routes from any image to TXT or DOCX
    if fmt_key == "txt":
        return image_to_txt(source_path, output_path)
    if fmt_key == "docx":
        return image_to_docx(source_path, output_path)

    # Direct vector SVG -> PDF route
    if source_path.suffix.lower() == ".svg" and fmt_key == "pdf":
        with pymupdf.open(str(source_path)) as svg_doc:
            output_path.write_bytes(svg_doc.convert_to_pdf())
        return output_path

    if fmt_key not in PILLOW_FORMAT_MAP:
        raise ValueError(f"Unsupported image target format: {target_format}")

    pillow_format = PILLOW_FORMAT_MAP[fmt_key]

    with _open_image_or_svg(source_path) as img:
        img = ImageOps.exif_transpose(img)

        if fmt_key in {"jpg", "jpeg", "bmp", "pdf"} and img.mode in ("RGBA", "LA", "P"):
            rgba_img = img.convert("RGBA")
            background = Image.new("RGB", rgba_img.size, (255, 255, 255))
            background.paste(rgba_img, mask=rgba_img.split()[3])
            img = background
        elif fmt_key in {"jpg", "jpeg", "bmp", "pdf"} and img.mode != "RGB":
            img = img.convert("RGB")

        save_kwargs = {}
        if pillow_format == "JPEG":
            save_kwargs["quality"] = 92
            save_kwargs["optimize"] = True
        elif pillow_format == "WEBP":
            save_kwargs["quality"] = 90
        elif pillow_format == "PDF":
            save_kwargs["resolution"] = 150.0
        elif pillow_format == "ICO":
            img = img.resize((256, 256), Image.Resampling.LANCZOS)

        img.save(output_path, format=pillow_format, **save_kwargs)

    return output_path
