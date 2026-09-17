# Run Alembic using the project venv (avoids Windows MAX_PATH when repo is under a deep folder).
$ErrorActionPreference = "Stop"
$backend = Split-Path $PSScriptRoot -Parent
Set-Location $backend

function Get-ProjectPython {
    $venvRoot = Join-Path $backend "venv"
    $item = Get-Item $venvRoot -Force
    if ($item.LinkType -eq "Junction" -and $item.Target) {
        return Join-Path $item.Target[0] "Scripts\python.exe"
    }
    return Join-Path $venvRoot "Scripts\python.exe"
}

$python = Get-ProjectPython
if (-not (Test-Path $python)) { throw "venv python not found: $python" }

# Prefer short junction path for cwd when available (WhatsApp transfer paths).
$shortBackend = "C:\eduspark-backend"
if (Test-Path $shortBackend) { Set-Location $shortBackend }

& $python -m alembic @args
