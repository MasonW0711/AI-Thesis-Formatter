param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[build] Installing build dependencies..."
& $Python -m pip install --upgrade pip pyinstaller

Write-Host "[build] Building executable..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --name "ThesisFormatter" `
    --add-data "app/ui/templates;app/ui/templates" `
    --add-data "app/ui/static;app/ui/static" `
    --add-data "defaults;defaults" `
    launcher.py

Write-Host "[build] Done. Output folder: dist/ThesisFormatter"
