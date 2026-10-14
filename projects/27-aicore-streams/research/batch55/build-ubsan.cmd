@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
"C:\Program Files\LLVM\bin\clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude research/batch55/gold-driver.cpp src/simulator.cpp -o research/batch55/gold-ubsan.exe
if errorlevel 1 exit /b 1
exit /b 0
