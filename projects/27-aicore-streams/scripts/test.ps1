param([switch]$Full, [int]$Seed = 20261010)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonCommand = (Get-Command python -ErrorAction Stop).Source
Push-Location $projectRoot
try {
  & $pythonCommand scripts/generate_cases.py --quick --seed $Seed --output data/quick.json
  if ($LASTEXITCODE -ne 0) { throw 'Quick case generation failed' }
  & ./scripts/build.ps1
  if ($LASTEXITCODE -ne 0) { throw 'Build/test failed' }
  New-Item -ItemType Directory -Force -Path reports | Out-Null
  $suiteName = 'quick'
  if ($Full) {
    $suiteName = 'stress'
    & $pythonCommand scripts/generate_cases.py --seed $Seed --output data/stress.json
    if ($LASTEXITCODE -ne 0) { throw 'Stress generation failed' }
  }
  & ./build/aicore_bench.exe --input "data/$suiteName.json" --output "reports/$suiteName-results.json" --csv "reports/$suiteName-metrics.csv" --failures "reports/$suiteName-failures.json"
  if ($LASTEXITCODE -ne 0) { throw "Batch tests failed. Replay reports/$suiteName-failures.json" }
  & $pythonCommand scripts/summarize_results.py --results "reports/$suiteName-results.json" --output "reports/$suiteName-summary.json"
  if ($LASTEXITCODE -ne 0) { throw 'Summary generation failed' }
  & 'E:\mingw64\bin\g++.exe' -std=c++17 -O2 -Wall -Wextra -Wpedantic -I include -c solution/solution.cpp -o build/submission.o
  if ($LASTEXITCODE -ne 0) { throw 'Standalone submission compile failed' }
} finally { Pop-Location }
