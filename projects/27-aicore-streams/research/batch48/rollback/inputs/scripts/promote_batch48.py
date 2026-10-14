"""Authorized quality promotion; snapshot complete R45 rollback first."""
import hashlib,json,shutil,subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch48');old=Path('research/batch45');source='da5dc93e1f0615e0e1a3e4daf1f349eb9fe6d275cbff843d85cbb6da05b178c3'
assert sha(p/'solution.cpp')==source and sha('solution/solution.cpp')==sha(old/'solution.cpp')
assert sha('build/aicore_bench.exe')==sha(old/'default-aicore_bench.exe')
m=json.loads((old/'provenance.json').read_text(encoding='utf-8'));rollback=old/'rollback';paths={}
for section in ('compile_inputs','test_inputs','generation_inputs'):
    for name,expected in m[section].items():
        assert sha(name)==expected
        target=rollback/'inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,target);paths[name]=dict(snapshot=str(target).replace('\\','/'),sha=sha(target))
for name in ('default-aicore_bench.exe','provenance.json','projection.cpp.inc'):
    target=rollback/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,target);paths[f'research/batch45/{name}']=dict(snapshot=str(target).replace('\\','/'),sha=sha(target))
for name in m['release_flags']:
    target=rollback/'flags'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,target);assert target.read_text()==m['release_flags'][name];paths[name]=dict(snapshot=str(target).replace('\\','/'),sha=sha(target))
(rollback/'manifest.json').write_text(json.dumps(dict(status='complete immutable default45 rollback before48 promotion',source_sha=m['source_sha256'],exe_sha=m['default_exe_sha256'],snapshots=paths),indent=2),encoding='utf-8')
shutil.copyfile(p/'solution.cpp','solution/solution.cpp');shutil.copyfile(p/'projection.cpp.inc','solution/projection.cpp.inc')
Path('tests/test_group.cpp').write_text((p/'test_group_template.cpp').read_text(encoding='utf-8').replace('#include "solution.cpp"','#include "../solution/solution.cpp"',1),encoding='utf-8')
q=Path('CMakeLists.txt');s=q.read_text(encoding='utf-8');assert 'consumer_group_bigint_gold' not in s
s+='''
# Independent direct-user groups, stable moves and wide lifetime profile.
add_executable(consumer_group_tests tests/test_group.cpp)
target_include_directories(consumer_group_tests PRIVATE include)
add_test(NAME consumer_group_bigint_gold COMMAND consumer_group_tests
  ${CMAKE_CURRENT_SOURCE_DIR}/data/group-gold-batch48.json)
''';q.write_text(s,encoding='utf-8')
assert sha('solution/solution.cpp')==source
cmake='C:/Program Files (x86)/CMake/bin/cmake.exe'
with Path('reports/build-default-batch48.txt').open('w',encoding='utf-8') as f:
    subprocess.run([cmake,'-S','.','-B','build','-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe','-DCMAKE_MAKE_PROGRAM=E:/mingw64/bin/mingw32-make.exe','-DAICORE_SOLUTION_SOURCE=solution/solution.cpp'],stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run([cmake,'--build','build','--parallel','1'],stdout=f,stderr=subprocess.STDOUT,check=True)
with Path('reports/ctest-default-batch48.txt').open('w',encoding='utf-8') as f:subprocess.run(['C:/Program Files (x86)/CMake/bin/ctest.exe','--test-dir','build','--output-on-failure'],stdout=f,stderr=subprocess.STDOUT,check=True)
shutil.copyfile('build/aicore_bench.exe',p/'default-aicore_bench.exe')
print('Actual default48 build/CTest terminal',sha('solution/solution.cpp'),sha('build/aicore_bench.exe'),flush=True)
