import json
from pathlib import Path
import pymupdf
from converter.engine import convert_file


def test_data_formats_json_yaml_xlsx_csv_toml_xml(tmp_path: Path) -> None:
    src_json = tmp_path / "servers.json"
    payload = [
        {"host": "web-01", "ip": "10.0.0.1", "active": True},
        {"host": "db-01", "ip": "10.0.0.2", "active": False},
    ]
    src_json.write_text(json.dumps(payload), encoding="utf-8")

    xlsx_out = convert_file(src_json, "XLSX")
    assert xlsx_out.exists() and xlsx_out.suffix == ".xlsx"

    csv_out = convert_file(xlsx_out, "CSV")
    assert csv_out.exists() and "web-01" in csv_out.read_text(encoding="utf-8")

    yaml_out = convert_file(src_json, "YAML")
    assert yaml_out.exists() and "web-01" in yaml_out.read_text(encoding="utf-8")

    toml_out = convert_file(yaml_out, "TOML")
    assert toml_out.exists() and "web-01" in toml_out.read_text(encoding="utf-8")

    xml_out = convert_file(src_json, "XML")
    assert xml_out.exists() and "<host>web-01</host>" in xml_out.read_text(encoding="utf-8")


def test_svg_to_png_and_vector_pdf(tmp_path: Path) -> None:
    svg_file = tmp_path / "logo.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        '<circle cx="100" cy="100" r="80" fill="#3b82f6"/></svg>',
        encoding="utf-8",
    )

    png_out = convert_file(svg_file, "PNG")
    assert png_out.exists() and png_out.stat().st_size > 100

    pdf_out = convert_file(svg_file, "PDF")
    assert pdf_out.exists() and pdf_out.stat().st_size > 100


def test_pdf_table_to_xlsx_and_csv(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Item    Quantity    Price", fontsize=12)
    page.insert_text((72, 92), "WidgetA    10    25.00", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    xlsx_out = convert_file(pdf_path, "XLSX")
    assert xlsx_out.exists() and xlsx_out.stat().st_size > 100

    csv_out = convert_file(pdf_path, "CSV")
    assert csv_out.exists() and "WidgetA" in csv_out.read_text(encoding="utf-8")
