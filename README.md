# Instant Converter

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Ubuntu%20Linux-success.svg)](#prerequisites)

**Instant Converter** is an open-source, 100% offline desktop file converter built with **Python** and **PySide6**. It features an adaptive floating radial wheel that wraps dynamically around your desktop orb to convert **Images**, **Documents**, **Markdown/HTML**, **Audio**, and **Video** completely locally in seconds.

---

## Key Features

- **Integrated Radial Wheel**: Slices automatically expand around the desktop orb showing only valid target formats for the loaded file.
- **Single-Click or Drag & Drop**: Click the center orb to open your native file dialog, or drag and drop any supported file directly onto it.
- **Interactive Status Pill**: Visual status bar indicates progress (`Converting...`), errors, and provides a direct shortcut (`✓ Saved (Click to open)`) to reveal the file in your system file manager.
- **100% Offline & Private**: Zero cloud processing. No file size limits or privacy leaks.
- **Cross-Platform & Wayland-Ready**: Built for Windows 10/11 and Ubuntu (X11 & Wayland compatible via automatic XCB fallbacks).
- **Graceful Engine Fallbacks**: Seamlessly uses LibreOffice Headless and FFmpeg when installed, while providing pure-Python fallback renderers for documents.

---

## Supported Conversions

| Category | Input Formats | Available Output Formats | Processing Engine |
| :--- | :--- | :--- | :--- |
| **Images** | `PNG`, `JPG`, `JPEG`, `WEBP`, `BMP`, `GIF`, `TIFF`, `ICO` | `PNG`, `JPG`, `WEBP`, `BMP`, `ICO`, `PDF`, `MP4` *(GIF)* | Pillow |
| **Documents** | `DOCX`, `TXT`, `MD`, `HTML` | `PDF`, `DOCX`, `TXT`, `MD`, `HTML` | python-docx, Pillow, LibreOffice *(optional)* |
| **PDF Operations** | `PDF` | `DOCX`, `TXT`, `MD`, `HTML`, `PNG` | pypdf, poppler-utils / Pillow |
| **Video** | `MP4`, `MKV`, `WEBM`, `AVI`, `MOV` | `MP4`, `WEBM`, `MKV`, `GIF`, `MP3`, `WAV` | FFmpeg |
| **Audio** | `MP3`, `WAV`, `FLAC`, `OGG`, `M4A` | `MP3`, `WAV`, `FLAC`, `OGG` | FFmpeg |

---

## Prerequisites

### Ubuntu / Debian Linux

Install core Qt/XCB runtime packages and optional media/document tools:

    sudo apt update
    sudo apt install -y python3-venv python3-pip libxcb-cursor0 libegl1 libgl1
    sudo apt install -y ffmpeg poppler-utils libreoffice-writer

### Windows 10 / 11

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) (check **"Add Python to PATH"** during setup).
2. Install **FFmpeg** and **LibreOffice** *(optional, for media and high-fidelity DOCX-to-PDF conversion)* via PowerShell:

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
    python app.py ~/Documents/sample.docx

    # Windows
    python app.py "C:\path\to\sample.docx"

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

### Ubuntu Linux (`instant-converter_1.0.0_amd64.deb`)

Build and install the Debian package:

    sudo apt install -y dpkg-dev
    chmod +x scripts/build_linux.sh
    ./scripts/build_linux.sh
    sudo apt install ./dist/instant-converter_1.0.0_amd64.deb

---

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
