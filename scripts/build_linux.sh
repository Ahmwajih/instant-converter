#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
APP_NAME="instant-converter"
ARCH="amd64"

echo "==> Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Running pytest..."
pytest

echo "==> Packaging Linux binary with PyInstaller..."
pyinstaller --noconfirm --clean \
    --name "${APP_NAME}" \
    --windowed \
    --onedir \
    app.py

echo "==> Building Debian package (${APP_NAME}_${VERSION}_${ARCH}.deb)..."
DEB_ROOT="build/deb/${APP_NAME}_${VERSION}_${ARCH}"
rm -rf "${DEB_ROOT}"
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/opt/${APP_NAME}"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/share/applications"

cp -r "dist/${APP_NAME}/"* "${DEB_ROOT}/opt/${APP_NAME}/"
ln -sf "/opt/${APP_NAME}/${APP_NAME}" "${DEB_ROOT}/usr/bin/${APP_NAME}"

cat <<EOF > "${DEB_ROOT}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Instant Converter Contributors <opensource@example.com>
Depends: libegl1, libgl1, libxkbcommon-x11-0, libxcb-cursor0
Recommends: libreoffice-writer
Description: Floating radial menu offline file converter
 Cross-platform local file converter for images, PDFs, DOCX, and TXT files
 featuring a fast floating radial menu.
EOF

cat <<EOF > "${DEB_ROOT}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Name=Instant Converter
Comment=Offline radial menu file converter
Exec=/usr/bin/${APP_NAME} %f
Terminal=false
Type=Application
Categories=Utility;Office;Graphics;
StartupNotify=false
EOF

chmod 755 "${DEB_ROOT}/DEBIAN/control"
dpkg-deb --build "${DEB_ROOT}" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "==> Debian package created at dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
