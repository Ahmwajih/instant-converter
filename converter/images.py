from pathlib import Path
from PIL import Image, ImageOps

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


def convert_image(source_path: Path, output_path: Path, target_format: str) -> Path:
    fmt_key = target_format.lower().lstrip(".")
    if fmt_key not in PILLOW_FORMAT_MAP:
        raise ValueError(f"Unsupported image target format: {target_format}")

    pillow_format = PILLOW_FORMAT_MAP[fmt_key]

    with Image.open(source_path) as img:
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
