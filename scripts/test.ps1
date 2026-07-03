# ABIS full test gate: pytest + vitest + typecheck + lint + security audits.
#   powershell -File scripts\test.ps1
# Exits non-zero if any gate fails. (CLAUDE.md "full gate")
. "$PSScriptRoot\common.ps1"

if (-not (Test-Path $VenvPython)) {
    throw 'venv missing -- run scripts\setup.ps1 first.'
}

# Backend tests need Postgres from T-004 onward; make sure services are up.
try { Start-DevServices } catch { Write-Warning2 "docker services unavailable: $_" }

$results = [ordered]@{}

function Invoke-Gate([string]$Name, [scriptblock]$Body) {
    Write-Step $Name
    & $Body
    $results[$Name] = ($LASTEXITCODE -eq 0)
    if ($results[$Name]) { Write-Ok $Name } else { Write-Warning2 "$Name FAILED" }
}

Invoke-Gate 'backend: pytest' {
    Push-Location $BackendDir
    try { & $VenvPython -m pytest } finally { Pop-Location }
}

Invoke-Gate 'frontend: vitest' {
    Push-Location $FrontendDir
    try { npm test } finally { Pop-Location }
}

Invoke-Gate 'frontend: typecheck' {
    Push-Location $FrontendDir
    try { npm run typecheck } finally { Pop-Location }
}

Invoke-Gate 'frontend: lint' {
    Push-Location $FrontendDir
    try { npm run lint } finally { Pop-Location }
}

Invoke-Gate 'security: pip-audit' {
    & $VenvPipAudit --progress-spinner off
}

Invoke-Gate 'security: npm audit (critical)' {
    Push-Location $FrontendDir
    try { npm audit --audit-level=critical } finally { Pop-Location }
}

# -- summary ------------------------------------------------------------------
Write-Host "`n================ GATE SUMMARY ================" -ForegroundColor White
$failed = $false
foreach ($kv in $results.GetEnumerator()) {
    $mark = if ($kv.Value) { 'PASS' } else { 'FAIL'; }
    $color = if ($kv.Value) { 'Green' } else { 'Red' }
    if (-not $kv.Value) { $failed = $true }
    Write-Host ("  {0,-32} {1}" -f $kv.Key, $mark) -ForegroundColor $color
}
Write-Host '=============================================='

if ($failed) { exit 1 }
Write-Host 'All gates green.' -ForegroundColor Green
exit 0
