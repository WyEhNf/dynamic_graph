"""Sequential functional O2 builds, not performance measurements."""
import subprocess,time
from pathlib import Path
commands=[['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','research/batch48/test_group_template.cpp','-o','research/batch48/test_group.exe'],['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','research/batch48/test_projection.cpp','-o','research/batch48/test_projection.exe'],['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','research/batch48/diagnostic.cpp','src/simulator.cpp','-o','research/batch48/diagnostic.exe']]
with Path('reports/build-functional-batch48.txt').open('a',encoding='utf-8') as log:
    for cmd in commands:
        print('build',cmd[-1],flush=True);r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT);assert r.returncode==0
print('Three R48 actual builds exit0',flush=True)
