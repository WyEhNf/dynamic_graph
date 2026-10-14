param(
  [ValidateSet('quick','full')][string]$Profile='full',
  [int]$LargeShape=0
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$env:PATH='E:\mingw64\bin;C:\Program Files (x86)\CMake\bin;C:\Program Files\LLVM\bin;'+$env:PATH
Push-Location -LiteralPath $projectRoot
try {
  & cmake --preset local-mingw
  if($LASTEXITCODE) { throw 'CMake configure failed' }
  & cmake --build --preset local-mingw --parallel 4
  if($LASTEXITCODE) { throw 'CMake build failed' }
  & build/runtime_tests.exe
  if($LASTEXITCODE) { throw 'Core runtime test failed' }
  & .venv/Scripts/python.exe tools/test_project.py --profile $Profile --large-shape $LargeShape
  if($LASTEXITCODE) { throw 'Source-to-Metadata-to-runtime test failed' }
} finally { Pop-Location }
