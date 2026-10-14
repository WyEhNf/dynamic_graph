"""Mirror all default drivers to candidate48; keep default45 unchanged."""
from pathlib import Path
import re
p=Path('research/batch48');(p/'cmake').mkdir(exist_ok=True);(p/'tests').mkdir(exist_ok=True)
for t in Path('tests').glob('*.cpp'):
    s=t.read_text(encoding='utf-8').replace('../solution/solution.cpp','../solution.cpp').replace('../src/benchmark.cpp','../../../src/benchmark.cpp');(p/'tests'/t.name).write_text(s,encoding='utf-8')
(p/'tests/test_group.cpp').write_text((p/'test_group_template.cpp').read_text(encoding='utf-8').replace('#include "solution.cpp"','#include "../solution.cpp"',1),encoding='utf-8')
s=Path('CMakeLists.txt').read_text(encoding='utf-8').replace('project(aicore_streams LANGUAGES CXX)','project(aicore_streams_candidate48 LANGUAGES CXX)\nset(PROJECT27_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")').replace('"solution/solution.cpp"','"${PROJECT27_ROOT}/research/batch48/solution.cpp"')
s=re.sub(r'(?<![\w/])(src/[\w]+\.cpp)',r'${PROJECT27_ROOT}/\1',s);s=re.sub(r'(?<![\w/])(tests/[\w]+\.cpp)',r'${PROJECT27_ROOT}/research/batch48/\1',s)
s=s.replace('PUBLIC include','PUBLIC "${PROJECT27_ROOT}/include"').replace('PRIVATE include','PRIVATE "${PROJECT27_ROOT}/include"').replace('${CMAKE_CURRENT_SOURCE_DIR}/data','${PROJECT27_ROOT}/data')
s+='''
add_executable(consumer_group_tests ${PROJECT27_ROOT}/research/batch48/tests/test_group.cpp)
target_include_directories(consumer_group_tests PRIVATE "${PROJECT27_ROOT}/include")
add_test(NAME consumer_group_bigint_gold COMMAND consumer_group_tests ${PROJECT27_ROOT}/data/group-gold-batch48.json)
'''
(p/'cmake/CMakeLists.txt').write_text(s,encoding='utf-8')
(p/'numeric_checks.cpp').write_bytes(Path('research/batch45/numeric_checks.cpp').read_bytes())
for label,code in [('numeric','research/batch48/numeric_checks.cpp src/simulator.cpp'),('projection','research/batch48/test_projection.cpp'),('group','research/batch48/test_group_template.cpp')]:
    cmd='@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul\n"C:\\Program Files\\LLVM\\bin\\clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude '+code+' -o research/batch48/'+label+'-validation-ubsan.exe\n';(p/f'build-validation-{label}-ubsan.cmd').write_text(cmd,encoding='utf-8')
print('Candidate48 mirror13 tests and3 Clang scripts prepared',flush=True)
