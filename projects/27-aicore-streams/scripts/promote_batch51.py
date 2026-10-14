"""Run only after root independently reviews cost and authorizes promotion.

Complete immutable R48 rollback precedes any default mutation. Compiler temp
override applies only to this subprocess environment, never the user's system.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
p, old = Path('research/batch51'), Path('research/batch48')
acceptance = json.loads((p/'acceptance-checkpoint.json').read_text(encoding='utf-8'))
completion = json.loads((p/'paired-completion.json').read_text(encoding='utf-8'))
assert sha(p/'solution.cpp') == acceptance['source_sha'] == completion['source_sha']
assert sha('solution/solution.cpp') == acceptance['default48_source_sha']
assert sha('build/aicore_bench.exe') == sha(old/'default-aicore_bench.exe') == acceptance['default48_exe_sha']
assert sha('reports/project27-research.tex') == acceptance['old_user_open_tex_sha']
m = json.loads((old/'provenance.json').read_text(encoding='utf-8'))
rollback = old/'rollback'
snapshots = {}


def snapshot(original, target, expected=None):
    original, target = Path(original), Path(target)
    expected = expected or sha(original)
    assert sha(original) == expected, str(original)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(target) == expected, f'Existing rollback must not be overwritten: {target}'
    else:
        shutil.copyfile(original, target)
    assert sha(target) == expected
    snapshots[original.as_posix()] = dict(snapshot=target.as_posix(), sha=expected)


for section in ('compile_inputs', 'test_inputs', 'generation_inputs'):
    for name, expected in m[section].items():
        snapshot(name, rollback/'inputs'/name, expected)
for name in ('default-aicore_bench.exe', 'provenance.json', 'solution.cpp', 'projection.cpp.inc'):
    snapshot(old/name, rollback/name)
for name, expected_text in m['release_flags'].items():
    assert Path(name).read_text() == expected_text
    snapshot(name, rollback/'flags'/name)
rollback_manifest = dict(status='Immutable complete R48 rollback before R51 promotion',
                         source_sha=m['source_sha256'], exe_sha=m['default_exe_sha256'],
                         snapshots=snapshots)
manifest_path = rollback/'manifest.json'
if manifest_path.exists():
    assert json.loads(manifest_path.read_text(encoding='utf-8')) == rollback_manifest
else:
    manifest_path.write_text(json.dumps(rollback_manifest, indent=2)+'\n', encoding='utf-8')
shutil.copyfile(p/'solution.cpp', 'solution/solution.cpp')
shutil.copyfile(p/'projection.cpp.inc', 'solution/projection.cpp.inc')
shutil.copyfile(p/'release-cut.cpp.inc', 'solution/release-cut.cpp.inc')
cut_test = (p/'test_release_cut.cpp').read_text(encoding='utf-8')
assert cut_test.count('#include "../../src/benchmark.cpp"') == 1
assert cut_test.count('#include "solution.cpp"') == 1
cut_test = cut_test.replace('#include "../../src/benchmark.cpp"', '#include "../src/benchmark.cpp"')
cut_test = cut_test.replace('#include "solution.cpp"', '#include "../solution/solution.cpp"')
Path('tests/test_release_cut.cpp').write_text(cut_test, encoding='utf-8')
cmake_source = Path('CMakeLists.txt')
text = cmake_source.read_text(encoding='utf-8')
assert 'remaining_direct_release_cut_bigint_gold' not in text
text += '''
# Complete remaining original DIRECT consumers plus ancestor cut; actual default.
add_executable(release_cut_tests tests/test_release_cut.cpp)
target_include_directories(release_cut_tests PRIVATE include)
target_link_libraries(release_cut_tests PRIVATE simulator)
add_test(NAME remaining_direct_release_cut_bigint_gold COMMAND release_cut_tests
  ${CMAKE_CURRENT_SOURCE_DIR}/data/release-cut-gold-batch51.json)
'''
cmake_source.write_text(text, encoding='utf-8')
temp = (p/'compiler-temp').resolve()
temp.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
for name in ('TEMP', 'TMP', 'TMPDIR'):
    env[name] = str(temp)
cmake = 'C:/Program Files (x86)/CMake/bin/cmake.exe'
commands = [[cmake, '-S', '.', '-B', 'build', '-G', 'MinGW Makefiles',
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe',
             '-DCMAKE_MAKE_PROGRAM=E:/mingw64/bin/mingw32-make.exe',
             '-DAICORE_SOLUTION_SOURCE=solution/solution.cpp'],
            [cmake, '--build', 'build', '--parallel', '1'],
            ['C:/Program Files (x86)/CMake/bin/ctest.exe', '--test-dir', 'build', '--output-on-failure']]
statuses = []
for index, command in enumerate(commands):
    log_path = Path('reports/ctest-default-batch51.txt' if index == 2 else 'reports/build-default-batch51.txt')
    with log_path.open('a' if index == 1 else 'w', encoding='utf-8') as log:
        run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
    statuses.append(dict(command=command, actual_exit_code=run.returncode, log=log_path.as_posix()))
    (p/'default-build-status.json').write_text(json.dumps(dict(
        source_sha=sha('solution/solution.cpp'), rollback_manifest_sha=sha(manifest_path),
        process_environment_overrides={name: env[name] for name in ('TEMP','TMP','TMPDIR')},
        system_environment_modified=False, statuses=statuses), indent=2)+'\n', encoding='utf-8')
    assert run.returncode == 0, (command, run.returncode)
assert sha('solution/solution.cpp') == acceptance['source_sha']
assert sha('reports/project27-research.tex') == acceptance['old_user_open_tex_sha']
shutil.copyfile('build/aicore_bench.exe', p/'default-aicore_bench.exe')
print('Actual R51 default build/14CTest terminal', sha('solution/solution.cpp'),
      sha('build/aicore_bench.exe'), flush=True)
