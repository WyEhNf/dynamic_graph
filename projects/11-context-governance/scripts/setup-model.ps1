param(
  [string]$Python = 'C:\Users\admin\miniconda3\python.exe',
  [string]$ModelRepo = 'Qwen/Qwen2.5-Coder-0.5B-Instruct',
  [string]$ModelDirectory = 'models/qwen2.5-coder-0.5b-instruct',
  [switch]$Quantization
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $projectRoot
try {
  if (-not (Test-Path -LiteralPath '.venv-model/Scripts/python.exe')) {
    & $Python -m venv --system-site-packages .venv-model
    if ($LASTEXITCODE) { throw 'Model venv creation failed' }
  }
  & .venv-model/Scripts/python.exe -c 'import torch; print(torch.__version__)'
  if ($LASTEXITCODE) { throw 'A compatible PyTorch >=2.2 runtime is required. This workstation inherits its installed CUDA-enabled PyTorch.' }
  & .venv-model/Scripts/python.exe -m pip install -r requirements-model.lock
  if ($LASTEXITCODE) { throw 'Model dependency installation failed' }
  & .venv-model/Scripts/python.exe -m pip install --no-build-isolation -e .
  if ($LASTEXITCODE) { throw 'Editable package installation failed' }
  if ($Quantization) {
    & .venv-model/Scripts/python.exe -m pip install --only-binary=:all: --no-deps -r requirements-quant.lock
    if ($LASTEXITCODE) { throw 'Optional quantization dependency installation failed' }
    & .venv-model/Scripts/python.exe -c 'import accelerate, bitsandbytes; print(accelerate.__version__, bitsandbytes.__version__)'
    if ($LASTEXITCODE) { throw 'Optional quantization runtime dependencies are unavailable' }
  }
  & .venv-model/Scripts/python.exe -m context_governance.prepare_model --source modelscope --repo $ModelRepo --directory $ModelDirectory
  if ($LASTEXITCODE) { throw 'Verified public model download failed' }
} finally { Pop-Location }
