from pathlib import Path
from PIL import Image
import pytest
from converter.engine import convert_file


def test_png_rgba_to_jpg_and_webp(tmp_path: Path) -> None:
    src = tmp_path / "sample.png"
    img = Image.new("RGBA", (120, 80), color=(255, 0, 0, 128))
    img.save(src, format="PNG")

    jpg_out = convert_file(src, "JPG")
    assert jpg_out.exists()
    assert jpg_out.suffix == ".jpg"
    with Image.open(jpg_out) as converted:
        assert converted.mode == "RGB"
        assert converted.size == (120, 80)

    webp_out = convert_file(src, "WEBP")
    assert webp_out.exists()
    assert webp_out.suffix == ".webp"


def test_image_to_pdf(tmp_path: Path) -> None:
    src = tmp_path / "photo.bmp"
    img = Image.new("RGB", (200, 200), color=(0, 128, 255))
    img.save(src, format="BMP")

    pdf_out = convert_file(src, "PDF")
    assert pdf_out.exists()
    assert pdf_out.suffix == ".pdf"
    assert pdf_out.stat().st_size > 100


def test_unsupported_target_raises(tmp_path: Path) -> None:
    src = tmp_path / "test.png"
    Image.new("RGB", (32, 32)).save(src)
    with pytest.raises(ValueError):
        convert_file(src, "DOCX")
