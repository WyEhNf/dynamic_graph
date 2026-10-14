@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
"C:\Program Files\LLVM\bin\clang++.exe" -std=c++20 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -fno-fast-math -ffp-contract=off -DCHOL_UPDATE_WIDTH=16 -DCHOL_AVX_ROW_GROUP=0 -DCHOL_PACK_INITIALIZATION=0 -DCHOL_PREPARED_VM=1 -DCHOL_THREADED_VM=1 -DCHOL_HAVE_THREADED_DISPATCH=1 -Iinclude src/runtime.cpp src/tiled_runtime.cpp src/banded_runtime.cpp src/binary_io.cpp src/prepared_vm.cpp src/threaded_vm.cpp tests/threaded_vm_tests.cpp -o artifacts/stage2-prepared-vm-phase3/threaded-contract-ubsan.exe
if errorlevel 1 exit /b %errorlevel%
artifacts\stage2-prepared-vm-phase3\threaded-contract-ubsan.exe
