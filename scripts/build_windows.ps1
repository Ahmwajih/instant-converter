$ErrorActionPreference = "Stop"

Write-Host "==> Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "==> Generating application icons..."
python scripts/generate_icons.py

Write-Host "==> Running automated test suite..."
pytest

Write-Host "==> Building slimmed standalone Windows executable with PyInstaller..."
pyinstaller --noconfirm --clean `
    --name "InstantConverter" `
    --windowed `
    --onedir `
    --icon "assets\icon.ico" `
    --add-data "assets;assets" `
    --collect-all pymupdf `
    --collect-all pdf2docx `
    --collect-all docx `
    --collect-all pptx `
    --collect-all openpyxl `
    --collect-all pillow_heif `
    --collect-all rapidocr_onnxruntime `
    --exclude-module PySide6.QtWebEngineCore `
    --exclude-module PySide6.QtWebEngineWidgets `
    --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.QtQml `
    --exclude-module PySide6.Qt3DCore `
    --exclude-module PySide6.QtPdf `
    --exclude-module tkinter `
    app.py

Write-Host "==> Checking for Inno Setup Compiler (ISCC)..."
$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($iscc) {
    Write-Host "==> Compiling InstantConverter-Setup.exe..."
    & $iscc.Source "scripts\installer_windows.iss"
} else {
    Write-Host "Inno Setup (ISCC.exe) not found in PATH. Standalone build is ready in dist\InstantConverter\"
}
