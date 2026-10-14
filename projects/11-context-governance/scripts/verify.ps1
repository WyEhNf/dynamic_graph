$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "tests failed" }
& .\.venv\Scripts\python.exe -m context_governance.cli fixtures/demo.json --output artifacts/demo-result.json
if ($LASTEXITCODE -ne 0) { throw "demo failed" }
& .\.venv\Scripts\python.exe -m context_governance.benchmark
if ($LASTEXITCODE -ne 0) { throw "benchmark failed" }
