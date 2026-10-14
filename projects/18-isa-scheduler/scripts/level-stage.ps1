param([string]$Round, [int]$Seed = 18, [switch]$SkipTests,
      [ValidateSet('research_portfolio','phase_portfolio','consumer_portfolio','reduction_portfolio','age_portfolio')][string]$Strategy = 'research_portfolio',
      [ValidateSet('v14_auto','level_r91','phase_r102')][string]$Baseline = 'v14_auto')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Round) { $Round = 'level-stage-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
if ($Round -notmatch '^[A-Za-z0-9_-]+$') { throw 'Round must contain letters, digits, hyphens or underscores' }
Push-Location $ProjectRoot
try {
    $TaskEvidenceDir = Join-Path $ProjectRoot ('experiments\' + $Round + '-tests')
    if (Test-Path -LiteralPath $TaskEvidenceDir) { throw 'Evidence exists; select a fresh Round' }
    New-Item -ItemType Directory -Path $TaskEvidenceDir | Out-Null
    if (-not $SkipTests) {
        & .\.venv\Scripts\python.exe -m unittest discover -s tests -v *> (Join-Path $TaskEvidenceDir 'tests.log')
        if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed; see preserved tests.log' }
    }
    & .\.venv\Scripts\python.exe scripts\research_fuzz_stage.py --round ($Round + '-10000') --seed $Seed --strategy $Strategy --baseline $Baseline
    if ($LASTEXITCODE -ne 0) { throw 'Small-graph differential failed; evidence preserved' }
    & .\.venv\Scripts\python.exe scripts\research_benchmark.py --round ($Round + '-336') --input experiments\milestone-v14\inputs.jsonl --variants ($Baseline + ',' + $Strategy) --before $Baseline --after $Strategy --time-budget-ms 250
    if ($LASTEXITCODE -ne 0) { throw 'Large-graph independent validation failed' }
    & .\.venv\Scripts\python.exe scripts\research_analysis.py ('experiments\' + $Round + '-336\report.json') --before $Baseline --after $Strategy
    if ($LASTEXITCODE -ne 0) { throw 'Paired analysis failed' }
    & .\.venv\Scripts\python.exe scripts\replay_outputs.py ('experiments\' + $Round + '-336')
    if ($LASTEXITCODE -ne 0) { throw 'Serialized replay failed' }
    & .\.venv\Scripts\python.exe scripts\research_identity_replay.py ('experiments\' + $Round + '-336')
    if ($LASTEXITCODE -ne 0) { throw 'Original identity replay failed' }
    & .\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\official-known-input.json --strategy $Strategy --strict --output (Join-Path $TaskEvidenceDir 'official-submission.json')
    if ($LASTEXITCODE -ne 0) { throw 'Official illustrative input interface failed' }
    Write-Host ('Evidence preserved under experiments\' + $Round + '-*')
} finally { Pop-Location }
