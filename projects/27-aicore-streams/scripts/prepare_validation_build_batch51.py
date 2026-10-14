"""Static gate preparation. Does not configure/build/run any candidate."""
from pathlib import Path
import re
p=Path('research/batch51');(p/'cmake').mkdir(exist_ok=True);(p/'tests').mkdir(exist_ok=True)
for t in Path('tests').glob('*.cpp'):
    s=t.read_text(encoding='utf-8').replace('../solution/solution.cpp','../solution.cpp').replace('../src/benchmark.cpp','../../../src/benchmark.cpp')
    (p/'tests'/t.name).write_text(s,encoding='utf-8')
s=Path('CMakeLists.txt').read_text(encoding='utf-8').replace('project(aicore_streams LANGUAGES CXX)','project(aicore_streams_candidate51 LANGUAGES CXX)\nset(PROJECT27_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")').replace('"solution/solution.cpp"','"${PROJECT27_ROOT}/research/batch51/solution.cpp"')
s=re.sub(r'(?<![\w/])(src/[\w]+\.cpp)',r'${PROJECT27_ROOT}/\1',s)
s=re.sub(r'(?<![\w/])(tests/[\w]+\.cpp)',r'${PROJECT27_ROOT}/research/batch51/\1',s)
s=s.replace('PUBLIC include','PUBLIC "${PROJECT27_ROOT}/include"').replace('PRIVATE include','PRIVATE "${PROJECT27_ROOT}/include"').replace('${CMAKE_CURRENT_SOURCE_DIR}/data','${PROJECT27_ROOT}/data')
s+='''
add_executable(release_cut_tests ${PROJECT27_ROOT}/research/batch51/test_release_cut.cpp)
target_include_directories(release_cut_tests PRIVATE "${PROJECT27_ROOT}/include")
target_link_libraries(release_cut_tests PRIVATE simulator)
add_test(NAME remaining_direct_release_cut_bigint_gold COMMAND release_cut_tests ${PROJECT27_ROOT}/data/release-cut-gold-batch51.json)
'''
(p/'cmake/CMakeLists.txt').write_text(s,encoding='utf-8')
(p/'numeric_checks.cpp').write_bytes(Path('research/batch48/numeric_checks.cpp').read_bytes())
(p/'test_group_template.cpp').write_bytes(Path('research/batch48/test_group_template.cpp').read_bytes())
for label,code in [('numeric','research/batch51/numeric_checks.cpp src/simulator.cpp'),('projection','research/batch51/test_projection.cpp'),('group','research/batch51/test_group_template.cpp'),('cut','research/batch51/test_release_cut.cpp src/simulator.cpp')]:
    cmd='@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul\n"C:\\Program Files\\LLVM\\bin\\clang++.exe" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude '+code+' -o research/batch51/'+label+'-validation-ubsan.exe\n'
    (p/f'build-validation-{label}-ubsan.cmd').write_text(cmd,encoding='utf-8')
print('Static candidate51 mirror14 tests and4 Clang scripts prepared; none executed',flush=True)
