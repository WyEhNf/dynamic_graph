param([string]$Python = "C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PATH = "E:\mingw64\bin;C:\Program Files (x86)\CMake\bin;C:\Program Files\LLVM\bin;" + $env:PATH
& $Python -m venv .venv
if ($LASTEXITCODE) { throw "venv failed" }
& cmake --preset local-mingw
if ($LASTEXITCODE) { throw "configure failed" }
& cmake --build --preset local-mingw --parallel 4
if ($LASTEXITCODE) { throw "build failed" }
& ctest --preset local-mingw
if ($LASTEXITCODE) { throw "ctest failed" }
& .venv\Scripts\python.exe tools\analyze_source.py fixtures\cholesky_reference.c --output artifacts\reference.meta
if ($LASTEXITCODE) { throw "source analysis failed" }
& .venv\Scripts\python.exe tools\benchmark.py --runtime build\cholesky_runtime.exe --metadata artifacts\reference.meta
if ($LASTEXITCODE) { throw "benchmark failed" }
& .venv\Scripts\python.exe tools\validate_cli.py --runtime build\cholesky_runtime.exe --metadata artifacts\reference.meta
if ($LASTEXITCODE) { throw "CLI validation failed" }
