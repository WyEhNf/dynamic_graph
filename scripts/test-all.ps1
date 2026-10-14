param([switch]$Full, [switch]$WithModel, [switch]$MaxShape, [switch]$SkipProject11)
$ErrorActionPreference='Stop'
if ($SkipProject11 -and $WithModel) { throw '-SkipProject11 cannot be combined with -WithModel while project11 is paused.' }
$workspaceRoot=Split-Path $PSScriptRoot -Parent
$results=@()
Push-Location -LiteralPath $workspaceRoot
try {
  if ($SkipProject11) {
    $results += [ordered]@{project=11;status='skipped_by_request'}
  } else {
    & (Join-Path $workspaceRoot 'projects/11-context-governance/scripts/verify.ps1')
    $results += [ordered]@{project=11;status='harness_passed';report='projects/11-context-governance/artifacts/importance-benchmark.json'}
  }
  if ($Full) {
    & (Join-Path $workspaceRoot 'projects/18-isa-scheduler/scripts/evaluate.ps1') -Count 10000 -Seed 18
  } else { & (Join-Path $workspaceRoot 'projects/18-isa-scheduler/scripts/test.ps1') }
  $results += [ordered]@{project=18;status='harness_passed';report='projects/18-isa-scheduler/outputs/fuzz-10000.json'}
  $profile=if($Full){'full'}else{'quick'}
  $largeShape=if($MaxShape){10000}else{0}
  & (Join-Path $workspaceRoot 'projects/19-dynamic-graph/scripts/test.ps1') -Profile $profile -LargeShape $largeShape
  $results += [ordered]@{project=19;status='harness_passed';report='projects/19-dynamic-graph/artifacts/phase1-tests/test-report.json'}
  & (Join-Path $workspaceRoot 'projects/27-aicore-streams/scripts/test.ps1') -Full:$Full
  $suite=if($Full){'stress'}else{'quick'}
  $results += [ordered]@{project=27;status='harness_passed';report="projects/27-aicore-streams/reports/$suite-summary.json"}
  if ($WithModel) {
    & (Join-Path $workspaceRoot 'projects/11-context-governance/scripts/test-model.ps1')
    $results += [ordered]@{project=11;status='real_model_evaluation_completed';report='projects/11-context-governance/artifacts/model-evaluation-current.json'}
  }
  $recordRoot=Join-Path $workspaceRoot 'outputs/project-validation'
  New-Item -ItemType Directory -Force -Path $recordRoot | Out-Null
  [ordered]@{checked_at=(Get-Date).ToString('o');source='self-created evaluation; not official hidden tests';full=[bool]$Full;max_shape=[bool]$MaxShape;with_model=[bool]$WithModel;skip_project11=[bool]$SkipProject11;results=$results} |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $recordRoot 'test-readiness.json') -Encoding utf8
} finally { Pop-Location }
