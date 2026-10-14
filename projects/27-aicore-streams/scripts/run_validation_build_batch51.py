"""Run only after root releases19 performance window; sequential Release14."""
import subprocess,sys
from pathlib import Path
cmake='C:/Program Files (x86)/CMake/bin/cmake.exe'
if '--clang-only' not in sys.argv:
    with Path('reports/validation-build-batch51.txt').open('w',encoding='utf-8') as f:
        subprocess.run([cmake,'-S','research/batch51/cmake','-B','research/batch51/validation-build','-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe','-DCMAKE_MAKE_PROGRAM=E:/mingw64/bin/mingw32-make.exe'],stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run([cmake,'--build','research/batch51/validation-build','--parallel','1'],stdout=f,stderr=subprocess.STDOUT,check=True)
    with Path('reports/validation-ctest-batch51.txt').open('w',encoding='utf-8') as f:subprocess.run(['C:/Program Files (x86)/CMake/bin/ctest.exe','--test-dir','research/batch51/validation-build','--output-on-failure'],stdout=f,stderr=subprocess.STDOUT,check=True)
    print('Release14 CTest actualexit0',flush=True)
for label in ('numeric','projection','group','cut'):
    with Path(f'reports/validation-{label}-build-batch51.txt').open('w',encoding='utf-8') as f:subprocess.run(['cmd.exe','/c',str(Path(f'research/batch51/build-validation-{label}-ubsan.cmd'))],stdout=f,stderr=subprocess.STDOUT,check=True)
    print('Clang',label,'actualbuildexit0',flush=True)
