param(
  [int]$Repeats = 3, [string]$Device = 'auto',
  [string]$Model = 'models/qwen2.5-coder-0.5b-instruct',
  [string]$Suite = 'fixtures/selftest-v2',
  [string]$Output = 'artifacts/model-evaluation-current.json',
  [int]$MaxNewTokens = 512, [int]$PrefillChunk = 1024,
  [ValidateSet('none','nf4')][string]$Quantization = 'none',
  [ValidateSet('resident','offloaded','reclaimed')][string]$KvCachePolicy = 'resident',
  [ValidateRange(0,2147483647)][int]$KvOffloadMinTokens = 16384,
  [ValidateSet('literal-v17','public-contract-v22')][string]$PublicExamplesProtocol = 'literal-v17',
  [switch]$SelfReview, [switch]$ContractFeedback, [switch]$PreparedContext,
  [switch]$CritiqueBeforeReview, [switch]$PublicExampleReview,
  [int]$FeedbackMaxNewTokens = 384,
  [switch]$ImportanceBenchmark
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $projectRoot
try {
  if (-not (Test-Path -LiteralPath (Join-Path $Model 'model-lock.json'))) {
    if ($Model -eq 'models/qwen2.5-coder-0.5b-instruct') { & ./scripts/setup-model.ps1 }
    else { throw "Prepare and verify the requested model first: $Model" }
  }
  if ($ImportanceBenchmark) {
    & .venv-model/Scripts/python.exe -m context_governance.token_benchmark --model $Model
    if ($LASTEXITCODE) { throw 'Real-token importance benchmark failed' }
  }
  $evaluationArgs = @('-m','context_governance.run_local_eval','--model',$Model,'--suite',$Suite,
    '--output',$Output,'--repeats',$Repeats,'--device',$Device,'--max-new-tokens',$MaxNewTokens,
    '--prefill-chunk',$PrefillChunk,'--quantization',$Quantization,
    '--kv-cache-policy',$KvCachePolicy,'--kv-offload-min-tokens',$KvOffloadMinTokens,
    '--public-examples-protocol',$PublicExamplesProtocol)
  if ($SelfReview) { $evaluationArgs += '--self-review' }
  if ($CritiqueBeforeReview) { $evaluationArgs += '--critique-before-review' }
  if ($PublicExampleReview) { $evaluationArgs += '--public-example-review' }
  $evaluationArgs += @('--critique-max-new-tokens',$FeedbackMaxNewTokens)
  if ($ContractFeedback) { $evaluationArgs += '--contract-feedback' }
  if ($PreparedContext) { $evaluationArgs += '--prepared-context' }
  & .venv-model/Scripts/python.exe @evaluationArgs
  if ($LASTEXITCODE) { throw 'Real-model evaluation could not complete' }
  # Model task failures remain in the report. Completion alone is not a quality pass.
  Write-Host "Evaluation completed. Inspect $Output for quality and latency gates."
} finally { Pop-Location }
