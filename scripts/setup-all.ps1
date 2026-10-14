param(
  [string]$Python11 = 'python',
  [string]$PythonBase = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
)
$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $workspaceRoot
try {
  & (Join-Path $workspaceRoot 'projects/11-context-governance/scripts/setup.ps1') -Python $Python11
  & (Join-Path $workspaceRoot 'projects/18-isa-scheduler/scripts/setup.ps1') -PythonExe $PythonBase
  & (Join-Path $workspaceRoot 'projects/19-dynamic-graph/scripts/bootstrap.ps1') -Python $PythonBase
  & (Join-Path $workspaceRoot 'projects/27-aicore-streams/scripts/build.ps1')
  Write-Host 'All four environments configured.'
} finally { Pop-Location }
