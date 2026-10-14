$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
    & .\.venv\Scripts\python.exe -m isa_scheduler benchmark --output outputs\benchmark.json
    if ($LASTEXITCODE -ne 0) { throw "Benchmark command failed" }
} finally { Pop-Location }

