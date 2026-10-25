#!/usr/bin/env bash
set -euo pipefail

VERSION="1.1.0"
APP_NAME="instant-converter"
ARCH="amd64"

echo "==> Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Generating application icons..."
python3 scripts/generate_icons.py

echo "==> Running pytest..."
pytest

echo "==> Packaging Linux binary with PyInstaller..."
pyinstaller --noconfirm --clean \
    --name "${APP_NAME}" \
    --windowed \
    --onedir \
    --icon "assets/icon.png" \
    --add-data "assets:assets" \
    --collect-all pymupdf \
    --collect-all pdf2docx \
    --collect-all docx \
    --collect-all openpyxl \
    --collect-all pillow_heif \
    --collect-all rapidocr_onnxruntime \
    app.py

echo "==> Building Debian package (${APP_NAME}_${VERSION}_${ARCH}.deb)..."
DEB_ROOT="build/deb/${APP_NAME}_${VERSION}_${ARCH}"
rm -rf "${DEB_ROOT}"
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/opt/${APP_NAME}"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/share/applications"
mkdir -p "${DEB_ROOT}/usr/share/pixmaps"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps"

cp -r "dist/${APP_NAME}/"* "${DEB_ROOT}/opt/${APP_NAME}/"
ln -sf "/opt/${APP_NAME}/${APP_NAME}" "${DEB_ROOT}/usr/bin/${APP_NAME}"

cp "assets/icon.png" "${DEB_ROOT}/usr/share/pixmaps/${APP_NAME}.png"
cp "assets/icon.png" "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

cat <<CONTROL > "${DEB_ROOT}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Instant Converter Contributors <opensource@example.com>
Depends: libegl1, libgl1, libxkbcommon-x11-0, libxcb-cursor0
Recommends: libreoffice-writer, ffmpeg, tesseract-ocr
Description: Floating radial menu offline file converter with OCR and Table Extraction
 Cross-platform local file converter for images, HEIC/SVG, PDFs, Excel tables,
 E-Books, JSON/YAML/TOML, DOCX, and media with offline OCR.
CONTROL

cat <<DESKTOP > "${DEB_ROOT}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Version=1.0
Name=Instant Converter
Comment=Offline radial menu file converter
Exec=/usr/bin/${APP_NAME} %f
Icon=/usr/share/pixmaps/${APP_NAME}.png
Terminal=false
Type=Application
Categories=Utility;Office;Graphics;AudioVideo;
StartupNotify=true
StartupWMClass=instant-converter
DESKTOP

chmod 755 "${DEB_ROOT}/DEBIAN/control"
chmod 644 "${DEB_ROOT}/usr/share/applications/${APP_NAME}.desktop"
dpkg-deb --build "${DEB_ROOT}" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "==> Debian package created at dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
