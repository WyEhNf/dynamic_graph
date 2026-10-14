param([string]$PythonExe = "python")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath ".venv-cpsat\Scripts\python.exe")) {
        & $PythonExe -m venv .venv-cpsat
        if ($LASTEXITCODE -ne 0) { throw "Optional venv creation failed" }
    }
    & .\.venv-cpsat\Scripts\python.exe -m pip install -r requirements-cpsat.lock
    if ($LASTEXITCODE -ne 0) { throw "Optional dependencies failed to install" }
    & .\.venv-cpsat\Scripts\python.exe -m unittest tests.test_retention_cpsat
    if ($LASTEXITCODE -ne 0) { throw "Optional CP-SAT boundary tests failed" }
} finally { Pop-Location }
