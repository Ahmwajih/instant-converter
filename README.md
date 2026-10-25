# Instant Converter

[![Release: v1.1.0](https://img.shields.io/badge/Release-v1.1.0-2563eb.svg)](https://github.com/Ahmwajih/instant-converter/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Ubuntu%20Linux-success.svg)](#prerequisites)

**Instant Converter** is an open-source, 100% offline desktop file converter built with **Python** and **PySide6**. It features an adaptive floating radial wheel that expands around your desktop orb to convert **Images (including HEIC/AVIF/SVG)**, **PDFs (to Editable DOCX & Excel/CSV Tables)**, **Scanned Documents (Offline OCR)**, **E-Books (EPUB/XPS/CBZ)**, **Developer Data (JSON/YAML/TOML/XML/XLSX)**, **Audio**, and **Video** locally in seconds.

---

## What Makes Instant Converter Different?

- **Offline PDF Table Extraction (`PDF` → `XLSX` / `CSV`)**: Extracts structured financial and report tables directly into multi-sheet Excel workbooks or CSV files without uploading sensitive documents to the cloud.
- **Built-In Offline OCR (`IMG` / Scanned `PDF` → `DOCX` / `TXT`)**: Powered by local ONNX Runtime (`RapidOCR`) + Tesseract fallback—turn screenshots, receipt photos, and scanned PDFs into editable Word or text files offline.
- **High-Fidelity Layout Reconstruction (`PDF` → `DOCX`)**: Preserves tables, embedded images, multi-column layouts, and typography via `pdf2docx` and `PyMuPDF`.
- **Apple & Vector Formats (`HEIC`, `AVIF`, `SVG`)**: Native conversion for iPhone `.heic` photos, `.avif` images, and 300 DPI / vector `.svg` graphics.
- **Zero-Calibre E-Book Engine (`EPUB`, `FB2`, `XPS`, `CBZ`)**: Convert e-books and comic archives directly to PDF, DOCX, TXT, or HTML.
- **Developer & Admin Data Pipeline (`JSON` ↔ `YAML` ↔ `TOML` ↔ `XML` ↔ `CSV` ↔ `XLSX`)**: Transform configuration files and API payloads into formatted Excel sheets or vice versa in one click.

---

## Supported Conversions

| Category | Input Formats | Available Output Formats | Processing Engine |
| :--- | :--- | :--- | :--- |
| **Images & Next-Gen** | `PNG`, `JPG`, `WEBP`, `BMP`, `GIF`, `TIFF`, `ICO`, `HEIC`, `HEIF`, `AVIF`, `SVG` | `PNG`, `JPG`, `WEBP`, `PDF`, `ICO`, `TXT` *(OCR)*, `DOCX` *(OCR)*, `MP4` *(GIF)* | Pillow, pillow-heif, PyMuPDF, RapidOCR |
| **PDF Operations** | `PDF` *(Digital & Scanned)* | `DOCX`, `XLSX`, `CSV`, `TXT`, `HTML`, `PNG` *(300 DPI)* | pdf2docx, PyMuPDF, openpyxl, RapidOCR |
| **Documents** | `DOCX`, `TXT`, `MD`, `HTML` | `PDF`, `DOCX`, `TXT`, `MD`, `HTML` | PyMuPDF Vector Engine, python-docx, LibreOffice |
| **E-Books & Archives** | `EPUB`, `FB2`, `XPS`, `CBZ` | `PDF`, `DOCX`, `TXT`, `HTML`, `PNG` | PyMuPDF Native Layout Engine |
| **Data & Spreadsheets** | `JSON`, `YAML`, `YML`, `TOML`, `XML`, `CSV`, `XLSX` | `XLSX`, `CSV`, `JSON`, `YAML`, `TOML`, `XML` | openpyxl, PyYAML, tomllib/tomli-w, xml |
| **Video** | `MP4`, `MKV`, `WEBM`, `AVI`, `MOV` | `MP4`, `WEBM`, `MKV`, `GIF`, `MP3`, `WAV` | FFmpeg |
| **Audio** | `MP3`, `WAV`, `FLAC`, `OGG`, `M4A` | `MP3`, `WAV`, `FLAC`, `OGG` | FFmpeg |

---

## Prerequisites

### Ubuntu / Debian Linux

Install core Qt/XCB runtime packages and optional media/document tools:

    sudo apt update
    sudo apt install -y python3-venv python3-pip libxcb-cursor0 libegl1 libgl1
    sudo apt install -y ffmpeg libreoffice-writer tesseract-ocr

### Windows 10 / 11

1. Install **Python 3.11+** from [python.org](https://www.python.org/downloads/) (check **"Add Python to PATH"** during setup).
2. Install **FFmpeg** and **LibreOffice** *(optional, for media and DOCX-to-PDF conversion)* via PowerShell:

    winget install Gyan.FFmpeg
    winget install TheDocumentFoundation.LibreOffice

---

## Quick Start (From Source)

### 1. Clone the Repository

    git clone https://github.com/Ahmwajih/instant-converter.git
    cd instant-converter

### 2. Create and Activate Virtual Environment

**On Ubuntu / Linux (Bash):**

    python3 -m venv .venv
    source .venv/bin/activate

**On Windows (PowerShell):**

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

*(If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first).*

### 3. Install Python Dependencies

    pip install --upgrade pip
    pip install -r requirements.txt

### 4. Run the Application

    python app.py

Pass a file path directly to open the radial selector immediately:

    # Ubuntu / Linux
    python app.py ~/Documents/invoice.pdf

    # Windows
    python app.py "C:\path\to\invoice.pdf"

---

## How to Use

1. **Load a file:** Click the center **`CONVERT`** orb to open the file picker, or drag and drop any supported file directly onto it.
2. **Select format:** Slices showing available target formats will expand around the orb. Click any slice.
3. **Open converted file:** When conversion completes, the status pill turns green (`✓ filename (Click to open)`). Click it to jump straight to the saved file in **Ubuntu Files (Nautilus)** or **Windows File Explorer**.
4. **Move or Exit:** Click and drag the orb to move it anywhere on your screen. Click the red **`✕`** icon or right-click the orb/tray icon to select **Quit**.

---

## Running Automated Tests

    pytest -v

---

## Building Native Installers

### Windows (`InstantConverter-Setup.exe`)

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) with `ISCC.exe` in your system `PATH`:

    .\scripts\build_windows.ps1

The compiled installer will be created at `dist\InstantConverter-Setup.exe`.

### Ubuntu Linux (`instant-converter_1.1.0_amd64.deb`)

Build and install the Debian package:

    sudo apt install -y dpkg-dev
    chmod +x scripts/build_linux.sh
    ./scripts/build_linux.sh
    sudo apt install ./dist/instant-converter_1.1.0_amd64.deb

---

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
