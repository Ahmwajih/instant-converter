# Instant Converter

[![Release: v1.0.2](https://img.shields.io/badge/Release-v1.0.2-2563eb.svg)](https://github.com/Ahmwajih/instant-converter/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Ubuntu%20Linux-success.svg)](#prerequisites)

**Instant Converter** is an open-source, 100% offline desktop conversion & document modification suite built with **Python** and **PySide6**. Designed to surpass macOS-only utilities across **Windows 10/11** and **Ubuntu Linux**, it combines an adaptive radial wheel with a **Live Modification Studio**, **Interactive PDF Page & Line Editor**, **Offline AI OCR**, **Background Removal**, and **Multi-File Batch Combine/Separate Workflows**.

---

## Flagship Features in v1.0.2

- **Interactive PDF Page & Line Studio (`EDIT-PDF`)**: Click any line directly on the live visual page preview to edit or delete text in place, add new lines, reorder/add/delete pages, stamp a **Signature (`✒️ Sign`)**, or apply a **Watermark (`💧 Watermark`)** with full **`↶ Undo`** history before finalizing.
- **Multi-File Separate vs. Combine Mode**: Drop or select multiple files and choose whether to convert them **separately** or **combine** them into one unified `.pdf`, `.docx`, `.xlsx`, `.txt`, `.png`, or `.zip`.
- **Clipboard-to-File Conversion (`Ctrl+V` / `📋 Paste`)**: Copy any screenshot, image, JSON payload, or Markdown snippet and press `Ctrl+V` on the orb to convert immediately.
- **OS Right-Click Integration**: Right-click any file(s) in **Ubuntu Files (Nautilus)** (`Scripts → Send to Instant Converter` or `Open With`) or **Windows Explorer** (`Convert with Instant Converter`) to summon the radial wheel directly under your cursor.
- **Pro Privacy & Compression Tools (`🛠️ TOOLS` Mode)**:
  - **`NO-BG`**: 1-click offline background removal to transparent `.png`.
  - **`COMPRESS`**: Live quality %, resolution scaling, and video CRF bitrate presets.
  - **`REDACT`**: Automatically blacks out Emails, Phone Numbers, IBANs, and custom keywords in PDFs.
  - **`LOCK-PDF`**: Encrypts PDFs with **AES-256** password protection.
  - **`NO-META`**: Strips EXIF, GPS location, and author metadata from images, PDFs, DOCX, and media.

---

## Supported Conversions & Tools

| Category | Input Formats | Available Output Formats & Actions |
| :--- | :--- | :--- |
| **Images & Vector** | `PNG`, `JPG`, `WEBP`, `AVIF`, `HEIC`, `SVG`, `BMP`, `TIFF`, `GIF`, `ICO` | `PNG`, `JPG`, `WEBP`, `SVG`, `AVIF`, `PDF`, `ICO`, `TXT` *(OCR)*, `DOCX` *(OCR)*, `NO-BG`, `COMPRESS`, `NO-META` |
| **PDF Studio & Office** | `PDF`, `DOCX`, `DOC`, `RTF`, `ODT`, `TXT`, `MD`, `HTML` | `DOCX`, `PPTX`, `XLSX`, `CSV`, `SVG`, `PNG` *(300 DPI)*, `JPG`, `TXT`, `MD`, `HTML`, `EDIT-PDF`, `REDACT`, `LOCK-PDF`, `COMPRESS` |
| **Slides & E-Books** | `PPT`, `PPTX`, `ODP`, `EPUB`, `FB2`, `XPS`, `CBZ` | `PDF`, `PPTX`, `DOCX`, `PNG`, `JPG`, `TXT`, `MD`, `HTML` |
| **Spreadsheets & Data** | `XLSX`, `XLS`, `ODS`, `CSV`, `TSV`, `JSON`, `YAML`, `TOML`, `XML` | `XLSX`, `CSV`, `TSV`, `ODS`, `PDF`, `JSON`, `YAML`, `TOML`, `XML` |
| **Video, Audio & Subs** | `MP4`, `MOV`, `MKV`, `WEBM`, `AVI`, `WMV`, `MP3`, `M4A`, `WAV`, `FLAC`, `OGG`, `OPUS`, `AIFF`, `WMA`, `SRT`, `VTT` | `MP4`, `MOV`, `MKV`, `WEBM`, `GIF`, `MP3`, `M4A`, `WAV`, `FLAC`, `OGG`, `OPUS`, `AIFF`, `TXT`, `SRT`, `VTT`, `COMPRESS` |

---

## Quick Start (From Source)

    git clone https://github.com/Ahmwajih/instant-converter.git
    cd instant-converter
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    python app.py

---

## Building Native Installers

### Ubuntu Linux (`instant-converter_1.0.2_amd64.deb`)

    ./scripts/build_linux.sh
    sudo apt install -y ./dist/instant-converter_1.0.2_amd64.deb

### Windows 10 / 11 (`InstantConverter-Setup.exe`)

    .\scripts\build_windows.ps1

---

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
