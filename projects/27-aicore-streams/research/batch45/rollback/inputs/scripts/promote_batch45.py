"""Authorized R45 promotion: byte-identical source, default gold test only."""
import hashlib,json,shutil,subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch45');source='5116d8d9c859662a26d1aba7dd1b0916097cb2bd87e466007adf2cbede391dd9'
assert sha(p/'solution.cpp')==source
assert sha('solution/solution.cpp')==sha('research/batch44/solution.cpp')
assert sha('build/aicore_bench.exe')==sha('research/batch44/default-aicore_bench.exe')
cost=json.loads(Path('reports/resource-cost-summary-batch45.json').read_text())
assert cost['hard']['counts']==dict(all=202,common_success=141,common_failure=59,recovered=2)
assert cost['heldout']['counts']==dict(all=48,common_success=42,common_failure=6,recovered=0)
assert all(r['source_sha']==source and len(r['rounds'])==3 for r in cost.values())
shutil.copyfile(p/'solution.cpp','solution/solution.cpp')
text=(p/'test_projection.cpp').read_text().replace('#include "solution.cpp"','#include "../solution/solution.cpp"',1)
Path('tests/test_projection.cpp').write_text(text,encoding='utf-8')
cmake=Path('CMakeLists.txt');text=cmake.read_text()
assert 'workspace_projection_bigint_gold' not in text
text+='''
# Actual default source against full-ancestor/prefix-live-set bigint gold.
add_executable(workspace_projection_tests tests/test_projection.cpp)
target_include_directories(workspace_projection_tests PRIVATE include)
add_test(NAME workspace_projection_bigint_gold COMMAND workspace_projection_tests
  ${CMAKE_CURRENT_SOURCE_DIR}/data/projection-gold-batch45.json)
'''
cmake.write_text(text,encoding='utf-8')
assert sha('solution/solution.cpp')==source
cmd=['C:/Program Files (x86)/CMake/bin/cmake.exe','-S','.','-B','build','-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe','-DCMAKE_MAKE_PROGRAM=E:/mingw64/bin/mingw32-make.exe','-DAICORE_SOLUTION_SOURCE=solution/solution.cpp']
with Path('reports/build-default-batch45.txt').open('w',encoding='utf-8') as f:
    subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run([cmd[0],'--build','build','--parallel','1'],stdout=f,stderr=subprocess.STDOUT,check=True)
with Path('reports/ctest-default-batch45.txt').open('w',encoding='utf-8') as f:
    subprocess.run(['C:/Program Files (x86)/CMake/bin/ctest.exe','--test-dir','build','--output-on-failure'],stdout=f,stderr=subprocess.STDOUT,check=True)
shutil.copyfile('build/aicore_bench.exe',p/'default-aicore_bench.exe')
print('Actual default build/CTest terminal',sha('solution/solution.cpp'),sha('build/aicore_bench.exe'),flush=True)
