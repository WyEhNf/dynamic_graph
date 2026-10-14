"""Mirror local drivers so direct include tests really use candidate45."""
from pathlib import Path
import re
p=Path('research/batch45');(p/'cmake').mkdir(exist_ok=True);(p/'tests').mkdir(exist_ok=True)
for t in Path('tests').glob('*.cpp'):
    s=t.read_text(encoding='utf-8').replace('../solution/solution.cpp','../solution.cpp').replace('../src/benchmark.cpp','../../../src/benchmark.cpp')
    (p/'tests'/t.name).write_text(s,encoding='utf-8')
s=Path('CMakeLists.txt').read_text(encoding='utf-8')
s=s.replace('project(aicore_streams LANGUAGES CXX)','project(aicore_streams_candidate45 LANGUAGES CXX)\nset(PROJECT27_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")')
s=s.replace('"solution/solution.cpp"','"${PROJECT27_ROOT}/research/batch45/solution.cpp"')
s=re.sub(r'(?<![\w/])(src/[\w]+\.cpp)',r'${PROJECT27_ROOT}/\1',s)
s=re.sub(r'(?<![\w/])(tests/[\w]+\.cpp)',r'${PROJECT27_ROOT}/research/batch45/\1',s)
s=s.replace('PUBLIC include','PUBLIC "${PROJECT27_ROOT}/include"').replace('PRIVATE include','PRIVATE "${PROJECT27_ROOT}/include"').replace('${CMAKE_CURRENT_SOURCE_DIR}/data','${PROJECT27_ROOT}/data')
s+='''\nadd_executable(workspace_profile_tests ${PROJECT27_ROOT}/research/batch45/test_projection.cpp)
target_include_directories(workspace_profile_tests PRIVATE "${PROJECT27_ROOT}/include")
add_test(NAME workspace_projection_bigint_gold COMMAND workspace_profile_tests ${PROJECT27_ROOT}/data/projection-gold-batch45.json)
'''
(p/'cmake/CMakeLists.txt').write_text(s,encoding='utf-8')
for file in ['numeric_checks.cpp']:(p/file).write_bytes(Path('research/batch44',file).read_bytes())
for label,code in [('numeric','research/batch45/numeric_checks.cpp src/simulator.cpp'),('projection','research/batch45/test_projection.cpp')]:
    cmd='@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul\n"C:\\Program Files\\LLVM\\bin\\clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude '+code+' -o research/batch45/'+label+'-validation-ubsan.exe\n'
    (p/f'build-validation-{label}-ubsan.cmd').write_text(cmd,encoding='utf-8')
print('Isolated candidate45 CMake/tests prepared; direct includes retargeted')
