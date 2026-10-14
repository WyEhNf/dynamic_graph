param([int]$Seed = 20261011, [int]$Repetitions = 3)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonCommand = (Get-Command python -ErrorAction Stop).Source
Push-Location $projectRoot
try {
  & ./scripts/build.ps1
  if ($LASTEXITCODE -ne 0) { throw 'Build/tests failed' }
  & $pythonCommand scripts/generate_research_cases.py --seed $Seed --output data/research-final.json
  if ($LASTEXITCODE -ne 0) { throw 'Development generation failed' }
  & $pythonCommand scripts/generate_research_cases.py --seed ($Seed + 10000) --output data/research-holdout-final.json
  if ($LASTEXITCODE -ne 0) { throw 'Holdout generation failed' }
  & $pythonCommand scripts/paired_benchmark.py --suite data/research-final.json --prefix reports/paired-final --repetitions $Repetitions
  if ($LASTEXITCODE -ne 0) { throw 'Development benchmark failed' }
  & $pythonCommand scripts/paired_benchmark.py --suite data/research-holdout-final.json --prefix reports/paired-holdout-final --repetitions $Repetitions
  if ($LASTEXITCODE -ne 0) { throw 'Holdout benchmark failed' }
  & $pythonCommand scripts/generate_cases.py --output data/stress.json
  if ($LASTEXITCODE -ne 0) { throw 'Incremental stress generation failed' }
  & $pythonCommand scripts/paired_benchmark.py --baseline research/batch6/aicore_bench.exe --suite data/stress.json --prefix reports/paired-stream-priority --repetitions $Repetitions
  if ($LASTEXITCODE -ne 0) { throw 'Stream priority increment benchmark failed' }
  & $pythonCommand scripts/write_research_report.py
  if ($LASTEXITCODE -ne 0) { throw 'Research report generation failed' }
} finally { Pop-Location }
