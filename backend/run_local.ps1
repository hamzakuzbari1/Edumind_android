# Start EduSpark API locally (PostgreSQL on localhost — no Docker)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-ProjectPython {
    foreach ($venvName in @("venv", ".venv")) {
        $venvRoot = Join-Path $PSScriptRoot $venvName
        $pythonRel = Join-Path $venvRoot "Scripts\python.exe"
        if (-not (Test-Path $pythonRel)) { continue }

        $item = Get-Item $venvRoot -Force
        if ($item.LinkType -eq "Junction" -and $item.Target) {
            $resolved = Join-Path $item.Target[0] "Scripts\python.exe"
            if (Test-Path $resolved) { return $resolved }
        }
        return (Resolve-Path $pythonRel).Path
    }

    $rootVenvPython = Join-Path $PSScriptRoot "..\eduspark-venv310\Scripts\python.exe"
    if (Test-Path $rootVenvPython) { return (Resolve-Path $rootVenvPython).Path }

    throw @"
No Python venv found under backend\venv, backend\.venv, or ..\eduspark-venv310.
Recreate with:
  py -3.12 -m venv C:\Users\$env:USERNAME\venvs\eduspark-backend
  cmd /c mklink /J "$PSScriptRoot\venv" "C:\Users\$env:USERNAME\venvs\eduspark-backend"
  <venv>\Scripts\python.exe -m pip install -r requirements.txt -r requirements-voice.txt
"@
}

$python = Get-ProjectPython
$env:PYTHONPATH = (Get-Location).Path
Write-Host "Using Python: $python"
Write-Host "Voice/STT requires: pip install -r requirements-voice.txt (faster-whisper turbo)"
Write-Host "EduSpark API -> http://127.0.0.1:8000/docs"
Write-Host "PostgreSQL should be running on localhost (see scripts/setup_local_db.sql)"
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
