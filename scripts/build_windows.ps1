# Execute on a trusted Windows 11 build machine after installing Python 3.12.
# A built installer is NOT included in the ZIP; Windows-only validation is required.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
& .\.venv\Scripts\python.exe -m pip install 'pyinstaller>=6,<7'
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --name CybersecurityOperationsStudio --windowed --onedir --paths src scripts\launcher.py
Write-Host 'Build is in dist\CybersecurityOperationsStudio\ — test on clean Windows 11 and sign before release.'
