param([switch]$Clean)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$compiler = 'E:\mingw64\bin\g++.exe'
$make = 'E:\mingw64\bin\mingw32-make.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Set compiler/make paths in scripts/build.ps1 or configure CMake manually.' }
$env:PATH = 'E:\mingw64\bin;' + $env:PATH
$buildRoot = Join-Path $projectRoot 'build'
if ($Clean -and (Test-Path -LiteralPath $buildRoot)) {
  $resolvedBuild = [IO.Path]::GetFullPath($buildRoot)
  if ($resolvedBuild -ne [IO.Path]::GetFullPath((Join-Path $projectRoot 'build'))) {throw 'Unexpected build directory'}
  Remove-Item -LiteralPath $resolvedBuild -Recurse -Force
}
cmake -S $projectRoot -B $buildRoot -G 'MinGW Makefiles' "-DCMAKE_CXX_COMPILER=$compiler" "-DCMAKE_MAKE_PROGRAM=$make" -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) {throw 'CMake configure failed'}
cmake --build $buildRoot --parallel 4
if ($LASTEXITCODE -ne 0) {throw 'Build failed'}
ctest --test-dir $buildRoot --output-on-failure
if ($LASTEXITCODE -ne 0) {throw 'CTest failed'}
& (Join-Path $buildRoot 'aicore_demo.exe')
if ($LASTEXITCODE -ne 0) {throw 'Baseline failed validation'}
