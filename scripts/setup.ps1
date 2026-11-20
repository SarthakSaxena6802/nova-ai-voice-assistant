# One-time setup for Nova on Windows (PowerShell).
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Backend: virtual environment + dependencies ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "== Training the intent classifier ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe ml\train_model.py

Write-Host "== Frontend: npm install ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install

if (-not (Test-Path "$root\.env")) { Copy-Item "$root\.env.example" "$root\.env" }
Set-Location $root
Write-Host "Setup complete. Start Nova with: powershell -ExecutionPolicy Bypass -File scripts\start.ps1" -ForegroundColor Green
