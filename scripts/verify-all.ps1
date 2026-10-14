$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path $PSScriptRoot -Parent
$env:PATH = 'E:\mingw64\bin;C:\Program Files (x86)\CMake\bin;C:\Program Files\LLVM\bin;' + $env:PATH
$results = @()
function Check-NativeExit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}
Push-Location -LiteralPath $workspaceRoot
try {
  & (Join-Path $workspaceRoot 'projects/11-context-governance/scripts/verify.ps1')
  $results += [ordered]@{ project=11; status='passed'; checks='unit tests, CLI, importance benchmark' }
  & (Join-Path $workspaceRoot 'projects/18-isa-scheduler/scripts/test.ps1')
  $results += [ordered]@{ project=18; status='passed'; checks='unit/differential tests, benchmark' }
  $project19 = Join-Path $workspaceRoot 'projects/19-dynamic-graph'
  & cmake --build (Join-Path $project19 'build') --parallel 4
  Check-NativeExit '19 build'
  & ctest --test-dir (Join-Path $project19 'build') --output-on-failure
  Check-NativeExit '19 CTest'
  Push-Location -LiteralPath $project19
  try {
    & .venv/Scripts/python.exe tools/analyze_source.py fixtures/cholesky_reference.c --output artifacts/reference.meta
    Check-NativeExit '19 frontend'
    & .venv/Scripts/python.exe tools/benchmark.py --runtime build/cholesky_runtime.exe --metadata artifacts/reference.meta
    Check-NativeExit '19 end-to-end benchmark'
    & .venv/Scripts/python.exe tools/validate_cli.py --runtime build/cholesky_runtime.exe --metadata artifacts/reference.meta
    Check-NativeExit '19 CLI validation'
  } finally { Pop-Location }
  $results += [ordered]@{ project=19; status='passed'; checks='CMake, CTest, Clang frontend, binary IO, numerical comparison' }
  & (Join-Path $workspaceRoot 'projects/27-aicore-streams/scripts/build.ps1')
  $results += [ordered]@{ project=27; status='passed'; checks='CMake, CTest, official sample simulation, feasible-candidate CLI' }
  $recordRoot = Join-Path $workspaceRoot 'outputs/project-validation'
  New-Item -ItemType Directory -Path $recordRoot -Force | Out-Null
  [ordered]@{ checked_at=(Get-Date).ToString('o'); source='local bootstrap verification; not official hidden evaluation'; results=$results } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $recordRoot 'latest.json') -Encoding utf8
  Write-Host 'All four project checks passed.'
} finally { Pop-Location }
