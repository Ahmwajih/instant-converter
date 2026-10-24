$ErrorActionPreference = "Stop"

Write-Host "==> Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "==> Generating application icons..."
python scripts/generate_icons.py

Write-Host "==> Running automated test suite..."
pytest

Write-Host "==> Building standalone Windows executable with PyInstaller..."
pyinstaller --noconfirm --clean `
    --name "InstantConverter" `
    --windowed `
    --onedir `
    --icon "assets\icon.ico" `
    --add-data "assets;assets" `
    app.py

Write-Host "==> Checking for Inno Setup Compiler (ISCC)..."
$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($iscc) {
    Write-Host "==> Compiling InstantConverter-Setup.exe..."
    & $iscc.Source "scripts\installer_windows.iss"
} else {
    Write-Host "Inno Setup (ISCC.exe) not found in PATH. Standalone build is ready in dist\InstantConverter\"
}
