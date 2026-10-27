#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.2"
APP_NAME="instant-converter"
ARCH="amd64"

echo "==> Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Generating application icons..."
python3 scripts/generate_icons.py

echo "==> Running pytest..."
pytest

echo "==> Packaging slimmed Linux binary with PyInstaller..."
pyinstaller --noconfirm --clean \
    --name "${APP_NAME}" \
    --windowed \
    --onedir \
    --icon "assets/icon.png" \
    --add-data "assets:assets" \
    --collect-all pymupdf \
    --collect-all pdf2docx \
    --collect-all docx \
    --collect-all pptx \
    --collect-all openpyxl \
    --collect-all pillow_heif \
    --collect-all rapidocr_onnxruntime \
    --collect-all pyzipper \
    --exclude-module PySide6.QtWebEngineCore \
    --exclude-module PySide6.QtWebEngineWidgets \
    --exclude-module PySide6.QtWebEngineQuick \
    --exclude-module PySide6.QtQuick \
    --exclude-module PySide6.QtQml \
    --exclude-module PySide6.Qt3DCore \
    --exclude-module PySide6.Qt3DRender \
    --exclude-module PySide6.QtPdf \
    --exclude-module PySide6.QtPdfWidgets \
    --exclude-module PySide6.QtBluetooth \
    --exclude-module PySide6.QtSensors \
    --exclude-module PySide6.QtPositioning \
    --exclude-module tkinter \
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
mkdir -p "${DEB_ROOT}/usr/share/nautilus-python/extensions"

cp -r "dist/${APP_NAME}/"* "${DEB_ROOT}/opt/${APP_NAME}/"
ln -sf "/opt/${APP_NAME}/${APP_NAME}" "${DEB_ROOT}/usr/bin/${APP_NAME}"

cp "assets/icon.png" "${DEB_ROOT}/usr/share/pixmaps/${APP_NAME}.png"
cp "assets/icon.png" "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

# Top-level Nautilus right-click context menu extension ("Instant Converter" directly in right-click menu)
cat << 'NAUT_EXT' > "${DEB_ROOT}/usr/share/nautilus-python/extensions/instant_converter_menu.py"
import subprocess
from urllib.parse import unquote, urlparse
from gi.repository import GObject, Nautilus


class InstantConverterMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def _launch_converter(self, menu, files):
        paths = []
        for f in files:
            uri = f.get_uri()
            if uri.startswith("file://"):
                paths.append(unquote(urlparse(uri).path))
        if paths:
            subprocess.Popen(["/usr/bin/instant-converter"] + paths, start_new_session=True)

    def get_file_items(self, *args):
        files = args[-1] if args else []
        if not files:
            return []
        item = Nautilus.MenuItem(
            name="InstantConverter::ConvertFiles",
            label="Instant Converter",
            tip="Convert, compress, or edit with Instant Converter",
            icon="instant-converter",
        )
        item.connect("activate", self._launch_converter, files)
        return [item]
NAUT_EXT

cat <<CONTROL > "${DEB_ROOT}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Instant Converter Contributors <opensource@example.com>
Depends: libegl1, libgl1, libxkbcommon-x11-0, libxcb-cursor0
Recommends: libreoffice-writer, ffmpeg, tesseract-ocr, python3-nautilus
Description: 100% Offline Radial File Converter, PDF Studio, OCR & Background Remover
 Cross-platform local file converter with live PDF Page/Line Studio, AI OCR,
 background removal, AES-256 PDF/ZIP encryption, and multi-file batching.
CONTROL

cat << 'POSTINST' > "${DEB_ROOT}/DEBIAN/postinst"
#!/usr/bin/env bash
set -e
for home_dir in /home/*; do
    if [ -d "${home_dir}" ]; then
        rm -f "${home_dir}/.local/share/nautilus/scripts/Send to Instant Converter" 2>/dev/null || true
    fi
done
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
POSTINST

cat <<DESKTOP > "${DEB_ROOT}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Version=1.0
Name=Instant Converter
Comment=Offline radial file converter, PDF Studio, and OCR
Exec=/usr/bin/${APP_NAME} %F
Icon=/usr/share/pixmaps/${APP_NAME}.png
Terminal=false
Type=Application
Categories=Utility;Office;Graphics;AudioVideo;
MimeType=application/pdf;image/png;image/jpeg;image/webp;image/svg+xml;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;text/plain;text/csv;application/json;video/mp4;audio/mpeg;
StartupNotify=true
StartupWMClass=instant-converter
DESKTOP

chmod 755 "${DEB_ROOT}/DEBIAN/control"
chmod 755 "${DEB_ROOT}/DEBIAN/postinst"
chmod 644 "${DEB_ROOT}/usr/share/applications/${APP_NAME}.desktop"
chmod 644 "${DEB_ROOT}/usr/share/nautilus-python/extensions/instant_converter_menu.py"
dpkg-deb --root-owner-group --build "${DEB_ROOT}" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "==> Debian package created at dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
