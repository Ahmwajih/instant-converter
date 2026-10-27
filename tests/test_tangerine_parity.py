from pathlib import Path
from PIL import Image
import pymupdf
from converter.engine import convert_file


def test_image_compression_and_metadata_strip(tmp_path: Path) -> None:
    src = tmp_path / "photo.jpg"
    img = Image.new("RGB", (600, 400), color=(40, 120, 220))
    img.save(src, format="JPEG", quality=98)

    compressed = convert_file(src, "COMPRESS", settings={"quality": 50, "scale": 0.5})
    assert compressed.exists()
    assert compressed.stat().st_size < src.stat().st_size

    clean_meta = convert_file(src, "NO-META")
    assert clean_meta.exists()


def test_pdf_redaction_and_pptx_export(tmp_path: Path) -> None:
    pdf_path = tmp_path / "confidential.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Contact: secret@example.com or SecretWord", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    redacted = convert_file(
        pdf_path,
        "REDACT",
        settings={"redact_pii": True, "redact_terms": "SecretWord"},
    )
    assert redacted.exists()
    with pymupdf.open(str(redacted)) as rdoc:
        extracted = rdoc[0].get_text("text")
        assert "secret@example.com" not in extracted
        assert "SecretWord" not in extracted

    pptx_out = convert_file(pdf_path, "PPTX")
    assert pptx_out.exists() and pptx_out.suffix == ".pptx"


def test_subtitles_srt_vtt_txt(tmp_path: Path) -> None:
    srt = tmp_path / "movie.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:04,000\nHello World!\n\n2\n00:00:05,000 --> 00:00:08,000\nSecond line.\n",
        encoding="utf-8",
    )
    vtt = convert_file(srt, "VTT")
    assert vtt.exists() and "WEBVTT" in vtt.read_text(encoding="utf-8")

    txt = convert_file(srt, "TXT")
    txt_content = txt.read_text(encoding="utf-8")
    assert "Hello World!" in txt_content
    assert "-->" not in txt_content


def test_tsv_spreadsheet_conversion(tmp_path: Path) -> None:
    tsv = tmp_path / "metrics.tsv"
    tsv.write_text("service\tstatus\nauth\tok\n", encoding="utf-8")

    xlsx = convert_file(tsv, "XLSX")
    assert xlsx.exists() and xlsx.suffix == ".xlsx"


def test_png_and_pdf_to_svg_export(tmp_path: Path) -> None:
    src_png = tmp_path / "badge.png"
    img = Image.new("RGBA", (100, 100), color=(37, 99, 235, 255))
    img.save(src_png, format="PNG")

    svg_from_img = convert_file(src_png, "SVG")
    assert svg_from_img.exists() and svg_from_img.suffix == ".svg"
    assert "<svg" in svg_from_img.read_text(encoding="utf-8")

    pdf_file = convert_file(src_png, "PDF")
    svg_from_pdf = convert_file(pdf_file, "SVG")
    assert svg_from_pdf.exists() and svg_from_pdf.suffix == ".svg"
    assert "<svg" in svg_from_pdf.read_text(encoding="utf-8")


def test_pdf_editor_session_pages_and_lines(tmp_path: Path) -> None:
    from converter.pdf_editor import PDFDocumentSession

    pdf_path = tmp_path / "draft.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((50, 80), "Header Line To Keep", fontsize=12)
    p1.insert_text((50, 110), "29/04/2026, 08:19", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()

    session = PDFDocumentSession(pdf_path)
    assert session.page_count() == 1
    lines = session.get_page_lines(0)
    assert len(lines) == 2

    # Remove the timestamp line and add a custom line
    session.delete_line(0, lines[1]["bbox"])
    session.add_line(0, "Added Custom Line")
    session.add_blank_page()
    assert session.page_count() == 2

    edited_out = tmp_path / "final.pdf"
    session.save_to(edited_out)
    session.close()

    with pymupdf.open(str(edited_out)) as check:
        assert len(check) == 2
        page0_txt = check[0].get_text("text")
        assert "Header Line To Keep" in page0_txt
        assert "29/04/2026, 08:19" not in page0_txt
        assert "Added Custom Line" in page0_txt


def test_multi_file_combine_into_single_pdf_and_docx(tmp_path: Path) -> None:
    from converter.batch import combine_files_to_single_output

    f1 = tmp_path / "part1.txt"
    f2 = tmp_path / "part2.txt"
    f1.write_text("First document content", encoding="utf-8")
    f2.write_text("Second document content", encoding="utf-8")

    combined_pdf = combine_files_to_single_output([f1, f2], "PDF")
    assert combined_pdf.exists() and combined_pdf.suffix == ".pdf"
    with pymupdf.open(str(combined_pdf)) as doc:
        assert len(doc) == 2

    combined_docx = combine_files_to_single_output([f1, f2], "DOCX")
    assert combined_docx.exists() and combined_docx.suffix == ".docx"


def test_pdf_editor_undo_and_safe_overwrite(tmp_path: Path) -> None:
    from converter.pdf_editor import PDFDocumentSession

    pdf_path = tmp_path / "input.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 80), "Original Line", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    session = PDFDocumentSession(pdf_path)
    lines = session.get_page_lines(0)
    session.delete_line(0, lines[0]["bbox"])
    assert len(session.get_page_lines(0)) == 0

    assert session.can_undo()
    session.undo()
    assert len(session.get_page_lines(0)) == 1

    # Saving back to the same path must succeed without file-lock errors
    session.save_to(pdf_path)
    session.close()


def test_offline_background_removal_no_bg(tmp_path: Path) -> None:
    src = tmp_path / "portrait.jpg"
    img = Image.new("RGB", (120, 120), color=(255, 255, 255))
    for x in range(40, 80):
        for y in range(40, 80):
            img.putpixel((x, y), (20, 90, 220))
    img.save(src, format="JPEG")

    nobg_out = convert_file(src, "NO-BG")
    assert nobg_out.exists() and nobg_out.suffix == ".png"
    with Image.open(nobg_out) as out_img:
        assert out_img.mode == "RGBA"


def test_pdf_aes256_password_lock(tmp_path: Path) -> None:
    pdf_path = tmp_path / "unlocked.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 80), "Top Secret Financial Data", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    locked = convert_file(pdf_path, "LOCK-PDF", settings={"pdf_password": "StrongPassword2026"})
    assert locked.exists()
    with pymupdf.open(str(locked)) as check_doc:
        assert check_doc.needs_pass
        assert check_doc.authenticate("StrongPassword2026") > 0


def test_pdf_studio_canvas_hit_test_watermark_and_signature(tmp_path: Path) -> None:
    from converter.pdf_editor import PDFDocumentSession

    pdf_path = tmp_path / "contract.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((60, 100), "Click this line on canvas", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    sig_path = tmp_path / "sig.png"
    Image.new("RGBA", (80, 30), color=(0, 0, 0, 255)).save(sig_path)

    session = PDFDocumentSession(pdf_path)
    lines = session.get_page_lines(0)
    bbox = lines[0]["bbox"]
    mid_x = (bbox[0] + bbox[2]) / 2.0
    mid_y = (bbox[1] + bbox[3]) / 2.0

    assert session.find_line_at_point(0, mid_x, mid_y) == 0
    session.add_watermark("CONFIDENTIAL", all_pages=True)
    session.add_signature_image(0, sig_path, center_x=300, center_y=500)

    highlighted_png = session.render_page_png_bytes(0, dpi=100, highlight_bbox=bbox)
    assert len(highlighted_png) > 500

    out_pdf = tmp_path / "signed_contract.pdf"
    session.save_to(out_pdf)
    session.close()
    assert out_pdf.exists()


def test_password_protected_aes_zip_and_line_drag(tmp_path: Path) -> None:
    import pyzipper
    from converter.pdf_editor import PDFDocumentSession

    secret_file = tmp_path / "notes.txt"
    secret_file.write_text("Top secret payload", encoding="utf-8")

    zip_out = convert_file(secret_file, "ZIP", settings={"zip_password": "MyZipPassword2026"})
    assert zip_out.exists() and zip_out.suffix == ".zip"

    with pyzipper.AESZipFile(zip_out, "r") as zf:
        zf.setpassword(b"MyZipPassword2026")
        extracted = zf.read("notes.txt").decode("utf-8")
        assert extracted == "Top secret payload"

    pdf_path = tmp_path / "move.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 80), "Draggable Line", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    session = PDFDocumentSession(pdf_path)
    line0 = session.get_page_lines(0)[0]
    session.move_line(0, line0["bbox"], line0["text"], 14.0, 120.0, 200.0)
    moved_line = session.get_page_lines(0)[0]
    assert moved_line["bbox"][0] > 100.0
    session.close()
