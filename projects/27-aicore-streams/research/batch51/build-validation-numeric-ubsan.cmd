@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
"C:\Program Files\LLVM\bin\clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude research/batch51/numeric_checks.cpp src/simulator.cpp -o research/batch51/numeric-validation-ubsan.exe
