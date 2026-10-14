$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path $PSScriptRoot -Parent
$taskNode = Get-Command node -ErrorAction Stop
$taskNodeVersion = (& $taskNode.Source --version).Trim()
if ($LASTEXITCODE -ne 0 -or [version]$taskNodeVersion.TrimStart('v') -lt [version]'20.0') {
    throw 'The optional TypeScript adapter requires Node.js 20 or later.'
}
Push-Location (Join-Path $taskProjectRoot 'adapters/typescript')
try {
    npm ci --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Pinned TypeScript installation failed.' }
    Write-Output "TypeScript adapter installed with $taskNodeVersion; package-lock.json records dependency integrity."
} finally {
    Pop-Location
}
