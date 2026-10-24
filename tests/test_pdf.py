from pathlib import Path
from converter.engine import convert_file
from converter.pdf import merge_pdfs


def test_txt_to_pdf_and_docx_roundtrip(tmp_path: Path) -> None:
    src_txt = tmp_path / "notes.txt"
    src_txt.write_text("Instant Converter Test\nLine Two", encoding="utf-8")

    docx_out = convert_file(src_txt, "DOCX")
    assert docx_out.exists()
    assert docx_out.suffix == ".docx"

    txt_back = convert_file(docx_out, "TXT")
    assert txt_back.exists()
    assert "Instant Converter Test" in txt_back.read_text(encoding="utf-8")

    pdf_out = convert_file(src_txt, "PDF")
    assert pdf_out.exists()
    assert pdf_out.suffix == ".pdf"
    assert pdf_out.stat().st_size > 100


def test_merge_pdfs(tmp_path: Path) -> None:
    txt1 = tmp_path / "p1.txt"
    txt2 = tmp_path / "p2.txt"
    txt1.write_text("Page 1", encoding="utf-8")
    txt2.write_text("Page 2", encoding="utf-8")

    pdf1 = convert_file(txt1, "PDF")
    pdf2 = convert_file(txt2, "PDF")

    merged = tmp_path / "merged.pdf"
    merge_pdfs([pdf1, pdf2], merged)
    assert merged.exists()
    assert merged.stat().st_size > pdf1.stat().st_size
