param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.lock
if ($LASTEXITCODE -ne 0) { throw "build dependency installation failed" }
& .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
if ($LASTEXITCODE -ne 0) { throw "editable installation failed" }
