param([int]$Count = 10000, [int]$Seed = 18, [double]$TimeBudgetMs = 100)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & "$PSScriptRoot\setup.ps1"
    & "$PSScriptRoot\test.ps1"
    $FuzzOutput = "outputs\fuzz-$Count.json"
    $Counterexamples = if ($Count -eq 10000) { "outputs\counterexamples" } else { "outputs\counterexamples-$Count" }
    $AuditOutput = if ($Count -eq 10000) { "outputs\register-order-audit.json" } else { "outputs\register-order-audit-$Count.json" }
    & .\.venv\Scripts\python.exe -m isa_scheduler fuzz --count $Count --seed $Seed --time-budget-ms $TimeBudgetMs --output $FuzzOutput --counterexamples $Counterexamples
    if ($LASTEXITCODE -ne 0) { throw "Differential fuzz evaluation failed" }
    & .\.venv\Scripts\python.exe scripts\audit_register_order.py --count $Count --seed $Seed --output $AuditOutput
    if ($LASTEXITCODE -ne 0) { throw "Register-order audit failed" }
    Write-Host "Evidence: outputs\benchmark.json / .csv; $FuzzOutput / .csv; $AuditOutput / .csv; $Counterexamples"
} finally { Pop-Location }

