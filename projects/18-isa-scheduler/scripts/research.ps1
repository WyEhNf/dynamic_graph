param(
    [int]$Count = 10000,
    [int]$Seed = 18,
    [int]$Samples = 2,
    [double]$TimeBudgetMs = 250,
    [string]$Round = ("replay-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "Run scripts/setup.ps1 first." }
if ($Round -notmatch '^[A-Za-z0-9_-]+$') { throw "Round must be a simple name." }
$evidence = Join-Path $projectRoot ("experiments\" + $Round)
if (Test-Path -LiteralPath $evidence) { throw "Choose a new Round; preserve existing evidence." }
New-Item -ItemType Directory -Path $evidence | Out-Null
Push-Location $projectRoot
try {
    & $pythonExe -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath (Join-Path $evidence "tests.log")
    if ($LASTEXITCODE -ne 0) { throw "Regression tests failed." }
    & $pythonExe -m isa_scheduler fuzz --count $Count --seed $Seed --output (Join-Path $evidence "fuzz.json") --counterexamples (Join-Path $evidence "counterexamples") --time-budget-ms 100
    if ($LASTEXITCODE -ne 0) { throw "Fuzz verification failed." }
    & $pythonExe scripts/research_benchmark.py --round $Round --seed 100001 --sizes 64,256,1024,4096 --samples $Samples --variants v02_auto,current_auto --time-budget-ms $TimeBudgetMs
    if ($LASTEXITCODE -ne 0) { throw "Paired research verification failed." }
    & $pythonExe scripts/research_analysis.py (Join-Path $evidence "report.json")
    if ($LASTEXITCODE -ne 0) { throw "Analysis failed." }
    Write-Output "Evidence: $evidence"
} finally { Pop-Location }
