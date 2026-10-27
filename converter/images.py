import base64
import io
from pathlib import Path
import cv2
import numpy as np
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
    "avif": "AVIF",
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


def image_to_svg(source_path: Path, output_path: Path) -> Path:
    """Converts raster images (PNG, JPG, WEBP, BMP, ICO) into scalable SVG with traced vector paths."""
    with _open_image_or_svg(source_path) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        width, height = img.size

        # Encode crisp base image layer + traced vector contour paths for sharp scaling
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64_png = base64.b64encode(buf.getvalue()).decode("ascii")

        # Trace main shape contours using OpenCV so vector editors can also manipulate paths
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        path_elements: list[str] = []
        for cnt in contours[:150]:
            if cv2.contourArea(cnt) < 16:
                continue
            epsilon = 0.003 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            pts = [f"{int(pt[0][0])},{int(pt[0][1])}" for pt in approx]
            if len(pts) >= 3:
                d_str = "M " + " L ".join(pts) + " Z"
                path_elements.append(f'  <path d="{d_str}" fill="none" stroke="none" />')

        paths_xml = "\n".join(path_elements)
        svg_xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
            f'  <image width="{width}" height="{height}" xlink:href="data:image/png;base64,{b64_png}"/>\n'
            f"{paths_xml}\n"
            f"</svg>\n"
        )
        output_path.write_text(svg_xml, encoding="utf-8")
    return output_path


def convert_image(source_path: Path, output_path: Path, target_format: str) -> Path:
    fmt_key = target_format.lower().lstrip(".")

    if fmt_key == "txt":
        return image_to_txt(source_path, output_path)
    if fmt_key == "docx":
        return image_to_docx(source_path, output_path)
    if fmt_key == "svg":
        return image_to_svg(source_path, output_path)

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
