# Shared helpers for ABIS dev scripts. Dot-source this file:
#   . "$PSScriptRoot\common.ps1"

$ErrorActionPreference = 'Stop'

$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:BackendDir = Join-Path $RepoRoot 'backend'
$script:FrontendDir = Join-Path $RepoRoot 'frontend'
$script:VenvDir = Join-Path $RepoRoot 'venv'
$script:VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$script:VenvCelery = Join-Path $VenvDir 'Scripts\celery.exe'
$script:VenvPipAudit = Join-Path $VenvDir 'Scripts\pip-audit.exe'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  OK $Message" -ForegroundColor Green
}

function Write-Warning2([string]$Message) {
    Write-Host "  !! $Message" -ForegroundColor Yellow
}

# Find a Python 3.12 interpreter (project standard). Falls back with a warning.
function Resolve-Python312 {
    $candidates = @(
        @{ Cmd = 'py'; Args = @('-3.12', '-c', 'import sys;print(sys.executable)') },
        @{ Cmd = 'py'; Args = @('-V:Astral/CPython3.12.12', '-c', 'import sys;print(sys.executable)') }
    )
    foreach ($c in $candidates) {
        try {
            $exe = & $c.Cmd @($c.Args) 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
        } catch { }
    }
    Write-Warning2 'Python 3.12 not found via py launcher; falling back to "python" on PATH.'
    return 'python'
}

# Start db + redis and block until their healthchecks pass.
function Start-DevServices {
    Write-Step 'Starting Postgres (:5433) and Redis (:6379) via docker compose'
    docker compose -f (Join-Path $RepoRoot 'docker-compose.yml') up -d db redis | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed -- is Docker Desktop running?' }

    foreach ($svc in @('abis-db', 'abis-redis')) {
        $deadline = (Get-Date).AddSeconds(90)
        do {
            $status = docker inspect --format '{{.State.Health.Status}}' $svc 2>$null
            if ($status -eq 'healthy') { break }
            Start-Sleep -Seconds 2
        } while ((Get-Date) -lt $deadline)
        if ($status -ne 'healthy') { throw "$svc did not become healthy within 90s (status: $status)" }
        Write-Ok "$svc healthy"
    }
}

# Pick pwsh (PowerShell 7) when present, else Windows PowerShell.
function Resolve-Shell {
    if (Get-Command pwsh -ErrorAction SilentlyContinue) { return 'pwsh' }
    return 'powershell'
}
