# Instant Converter

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Platform: Windows & Ubuntu](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Ubuntu%2024.04%2F26.04-success.svg)](#installation)

**Instant Converter** is a lightweight, 100% offline desktop file converter built with **Python** and **PySide6**. It features a floating radial menu that wraps dynamically around your cursor or desktop orb to convert **Images**, **Documents**, **Markdown/HTML**, **Audio**, and **Video** locally in seconds.

---

## Key Features

- **Integrated Radial Wheel**: Slices automatically expand around the desktop orb showing only valid target formats for the loaded file.
- **Single-Click or Drag & Drop**: Click the center orb to open your native file dialog, or drag and drop any supported file directly onto it.
- **Interactive Status Pill**: Visual status bar indicates progress (`Converting...`), errors, and provides a direct click-to-open shortcut (`✓ Saved (Click to open)`) to reveal the file in your system file manager.
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

## Prerequisites (System Libraries)

### Ubuntu / Debian

```bash
# Core Qt / XCB libraries
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0 libegl1 libgl1

# Optional but recommended for full document and media conversion:
sudo apt install -y ffmpeg poppler-utils libreoffice-writer
