# ABIS one-shot dev setup (Windows 11). Idempotent -- safe to re-run.
#   powershell -File scripts\setup.ps1
. "$PSScriptRoot\common.ps1"

Write-Host 'ABIS dev setup' -ForegroundColor White

# -- prerequisites -----------------------------------------------------------
Write-Step 'Checking prerequisites (python, node, docker)'
foreach ($tool in @('node', 'npm', 'docker')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool is not on PATH -- install it first (Node 20+, Docker Desktop)."
    }
}
Write-Ok "node $(node --version), npm $(npm --version)"

# -- python venv -------------------------------------------------------------
if (-not (Test-Path $VenvPython)) {
    Write-Step 'Creating Python 3.12 venv at .\venv'
    $py = Resolve-Python312
    & $py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
}
Write-Ok "venv python: $(& $VenvPython --version)"

Write-Step 'Installing backend dependencies (pip)'
& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install -q `
    -r (Join-Path $BackendDir 'requirements.txt') `
    -r (Join-Path $BackendDir 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
Write-Ok 'backend deps installed'

# -- frontend deps -----------------------------------------------------------
Write-Step 'Installing frontend dependencies (npm)'
Push-Location $FrontendDir
try {
    npm install --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
} finally { Pop-Location }
Write-Ok 'frontend deps installed'

# -- env file ----------------------------------------------------------------
$envFile = Join-Path $BackendDir '.env'
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $BackendDir '.env.example') $envFile
    Write-Ok 'created backend\.env from .env.example'
} else {
    Write-Ok 'backend\.env already exists (left untouched)'
}

# -- services + database -----------------------------------------------------
Start-DevServices

Write-Step 'Applying database migrations'
Push-Location $BackendDir
try {
    & $VenvPython manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw 'migrate failed' }
} finally { Pop-Location }
Write-Ok 'migrations applied'

# -- demo data (available from T-019) ----------------------------------------
Push-Location $BackendDir
try {
    $commands = & $VenvPython manage.py help --commands
    if ($commands -contains 'seed_demo') {
        Write-Step 'Seeding demo data'
        & $VenvPython manage.py seed_demo
        Write-Ok 'demo data seeded'
    } else {
        Write-Warning2 'seed_demo command not available yet (lands with T-019) -- skipped.'
    }
} finally { Pop-Location }

Write-Host "`nSetup complete. Start everything with: powershell -File scripts\dev.ps1" -ForegroundColor White
