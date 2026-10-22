# Starts the analysis API (port 8000) and the web app (port 3000) in two windows.
#   .\run.ps1            first run creates the venv and installs everything
param([switch]$SkipInstall)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Creating Python environment..." -ForegroundColor Cyan
    python -m venv (Join-Path $root ".venv") --system-site-packages
}
if (-not $SkipInstall) {
    & $py -m pip install -q -r (Join-Path $root "backend\requirements.txt")
    if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
        Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
    }
}

$env:KERAS_BACKEND = "torch"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; `$env:KERAS_BACKEND='torch'; `$env:HF_HUB_OFFLINE='1'; & '$py' -m uvicorn app:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Write-Host "API  -> http://localhost:8000/docs" -ForegroundColor Green
Write-Host "App  -> http://localhost:3000/workspace" -ForegroundColor Green
