# Starts the analysis API and the web app in two windows (defaults: API 8000, app 3000).
#   .\run.ps1                                   first run creates the venv and installs everything
#   .\run.ps1 -ApiPort 8001 -AppPort 3100       when 3000/8000 are taken (e.g. by the MM-RETINA website
#                                               and the older demo backend running side by side)
param([switch]$SkipInstall, [int]$ApiPort = 8000, [int]$AppPort = 3000)
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
# The API only accepts browser calls from the app's origin, and the app must know where the API is.
$cors = "http://localhost:$AppPort,http://127.0.0.1:$AppPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; `$env:KERAS_BACKEND='torch'; `$env:HF_HUB_OFFLINE='1'; `$env:CORS_ORIGINS='$cors'; & '$py' -m uvicorn app:app --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; `$env:NEXT_PUBLIC_API_URL='http://localhost:$ApiPort'; npm run dev -- -p $AppPort"
Write-Host "API  -> http://localhost:$ApiPort/docs" -ForegroundColor Green
Write-Host "App  -> http://localhost:$AppPort/workspace" -ForegroundColor Green
