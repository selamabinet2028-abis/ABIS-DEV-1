# ABIS dev stack: docker services + API + Celery + Vite, each in its own window.
#   powershell -File scripts\dev.ps1
. "$PSScriptRoot\common.ps1"

if (-not (Test-Path $VenvPython)) {
    throw 'venv missing -- run scripts\setup.ps1 first.'
}

Start-DevServices

$shell = Resolve-Shell

Write-Step 'Starting Django API (http://localhost:8000)'
Start-Process $shell -ArgumentList @(
    '-NoExit', '-Command',
    "`$Host.UI.RawUI.WindowTitle = 'ABIS API :8000'; Set-Location '$BackendDir'; & '$VenvPython' manage.py runserver"
)

Write-Step 'Starting Celery worker (--pool=solo, Windows)'
Start-Process $shell -ArgumentList @(
    '-NoExit', '-Command',
    "`$Host.UI.RawUI.WindowTitle = 'ABIS Celery'; Set-Location '$BackendDir'; & '$VenvCelery' -A config worker -l info --pool=solo"
)

Write-Step 'Starting Vite dev server (http://localhost:5173)'
Start-Process $shell -ArgumentList @(
    '-NoExit', '-Command',
    "`$Host.UI.RawUI.WindowTitle = 'ABIS Frontend :5173'; Set-Location '$FrontendDir'; npm run dev"
)

Write-Host @'

ABIS dev stack launched:
  API      http://localhost:8000   (Swagger: /api/docs/)
  Frontend http://localhost:5173
  Postgres localhost:5433 (abis/abis)  |  Redis localhost:6379

Each service runs in its own window -- close a window to stop that service.
Stop docker services with: docker compose down
'@ -ForegroundColor White
