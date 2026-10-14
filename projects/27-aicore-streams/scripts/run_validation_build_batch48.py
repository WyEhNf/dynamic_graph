"""Actual candidate Release13 + Clang builds; sequential shared functionality."""
import subprocess,sys
from pathlib import Path
cmake='C:/Program Files (x86)/CMake/bin/cmake.exe'
if '--clang-only' not in sys.argv:
    with Path('reports/validation-build-batch48.txt').open('w',encoding='utf-8') as f:
        subprocess.run([cmake,'-S','research/batch48/cmake','-B','research/batch48/validation-build','-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe','-DCMAKE_MAKE_PROGRAM=E:/mingw64/bin/mingw32-make.exe'],stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run([cmake,'--build','research/batch48/validation-build','--parallel','1'],stdout=f,stderr=subprocess.STDOUT,check=True)
    with Path('reports/validation-ctest-batch48.txt').open('w',encoding='utf-8') as f:subprocess.run(['C:/Program Files (x86)/CMake/bin/ctest.exe','--test-dir','research/batch48/validation-build','--output-on-failure'],stdout=f,stderr=subprocess.STDOUT,check=True)
    print('Release13 CTest actualexit0',flush=True)
for label in ('numeric','projection','group'):
    with Path(f'reports/validation-{label}-build-batch48.txt').open('a',encoding='utf-8') as f:subprocess.run(['cmd.exe','/c',str(Path(f'research/batch48/build-validation-{label}-ubsan.cmd'))],stdout=f,stderr=subprocess.STDOUT,check=True)
    print('Clang',label,'actualbuildexit0',flush=True)
