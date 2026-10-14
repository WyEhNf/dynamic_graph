@echo off
call "C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
if errorlevel 1 exit /b 1
"C:/Program Files/LLVM/bin/clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude research\batch56\caller-controls-driver.cpp src/simulator.cpp -Xlinker "/PDB:G:/Hackathon-project27-owned/batch56-3a4f184d/bin/caller-ubsan.pdb" -Xlinker "/ILK:G:/Hackathon-project27-owned/batch56-3a4f184d/bin/caller-ubsan.ilk" -o "G:/Hackathon-project27-owned/batch56-3a4f184d/bin/caller-ubsan.exe"
if errorlevel 1 exit /b 1
exit /b 0
