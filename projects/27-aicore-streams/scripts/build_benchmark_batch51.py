"""Functional O2 benchmark, separate actual binary from diagnostic driver."""
import subprocess
from pathlib import Path
cmd=['E:/mingw64/bin/g++.exe','-std=c++17','-O2','-Iinclude','src/benchmark.cpp','src/simulator.cpp','research/batch51/solution.cpp','-o','research/batch51/aicore_bench.exe']
with Path('reports/build-benchmark-batch51.txt').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0;print('R51 functional benchmark actualexit0',flush=True)
