param([string]$PythonExe = "python")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
        & $PythonExe -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Python venv creation failed" }
    }
    & .\.venv\Scripts\python.exe -c "import sys; assert sys.version_info >= (3,11); print(sys.version)"
    if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required" }
    Write-Host "Environment ready. No third-party runtime dependencies."
} finally { Pop-Location }

