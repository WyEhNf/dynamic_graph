"""Two sequential O2 functional builds, no isolated cost measurement."""
import subprocess
from pathlib import Path
commands=[['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','research/batch51/test_release_cut.cpp','src/simulator.cpp','-o','research/batch51/test_release_cut.exe'],['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','research/batch51/diagnostic.cpp','src/simulator.cpp','-o','research/batch51/diagnostic.exe']]
with Path('reports/build-functional-batch51.txt').open('w',encoding='utf-8') as log:
    for cmd in commands:
        print('build',cmd[-1],flush=True);r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT);assert r.returncode==0
print('Two R51 actual builds exit0',flush=True)
