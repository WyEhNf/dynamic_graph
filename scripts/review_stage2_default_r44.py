"""Verify default R44 provenance and all actual saved normal regression records."""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/27-aicore-streams'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PROJECT/'reports/final-checkpoint-batch44.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest_path.read_bytes() == (PROJECT/'research/batch44/provenance.json').read_bytes()
    checked = 0
    for group in ('compile_inputs', 'test_inputs', 'generation_inputs', 'measured_build_inputs'):
        for name, expected in manifest[group].items():
            path = PROJECT/name
            if group == 'measured_build_inputs' and name == 'CMakeLists.txt':
                path = PROJECT/manifest['measured_CMake_snapshot']
            assert digest(path) == expected, str(path)
            checked += 1
    for name, expected in (
        ('solution/solution.cpp', manifest['source_sha256']),
        ('build/aicore_bench.exe', manifest['default_exe_sha256']),
        ('research/batch44/build/aicore_bench.exe', manifest['measured_exe_sha256']),
        ('research/batch44/measured-release-aicore_bench.exe', manifest['measured_exe_sha256']),
        ('research/batch43/solution.cpp', manifest['old_default_R43_source_sha']),
        ('research/batch43/default-aicore_bench.exe', manifest['old_default_R43_exe_sha']),
        ('reports/project27-research.tex', manifest['old_frozen_R31_tex_sha']),
    ):
        assert digest(PROJECT/name) == expected, name
    log_path = PROJECT/'reports/ctest-batch44.txt'
    assert digest(log_path) == manifest['ctest_report_sha']
    log = log_path.read_text(encoding='utf-8')
    assert '100% tests passed, 0 tests failed out of 11' in log
    direct_path = PROJECT/'reports/direct-normal-r43-batch44.json'
    direct = json.loads(direct_path.read_text())
    count = 0
    for suite in direct['suites']:
        before = PROJECT/Path(suite['before'].replace('\\', '/'))
        after = PROJECT/Path(suite['after'].replace('\\', '/'))
        assert digest(before) == suite['before_sha'] and digest(after) == suite['after_sha']
        lhs, rhs = json.loads(before.read_text())['cases'], json.loads(after.read_text())['cases']
        assert len(lhs) == len(rhs) == suite['records']
        for left, right in zip(lhs,rhs):
            assert left['name'] == right['name']
            for field in ('pass','valid','T','peak_memory'):
                assert left[field] == right[field], (left['name'], field)
            assert right['pass']
        count += len(rhs)
    assert count == 979
    result = dict(reviewed_unix=time.time(), passed=True, normal_records=count,
                  hashed_build_test_generation_inputs=checked, ctest=11,
                  default_source_sha256=manifest['source_sha256'],
                  default_exe_sha256=manifest['default_exe_sha256'],
                  measured_exe_sha256=manifest['measured_exe_sha256'],
                  evidence={str(p.relative_to(ROOT)).replace('\\','/'):digest(p)
                            for p in (manifest_path,direct_path,log_path)},
                  scope='Current default source/binary, frozen historical R43, measured Release source/recipe/binary, exact recorded build inputs, terminal CTest log and every979 normal saved before/after record checked. Original open TeX unchanged. No fresh979 solver rerun claimed.')
    (ROOT/'outputs/stage2-root-default-r44.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
