"""Verify actual promoted default against frozen R48 acceptance and source."""
import json
import time
from pathlib import Path
from review_stage2_acceptance_r48 import ROOT, PROJECT, sha, read
from review_stage2_functional_plans_r44 import simulate


def main():
    manifest_path = PROJECT/'reports/final-checkpoint-batch48.json'
    manifest = read(manifest_path)
    assert manifest_path.read_bytes() == (PROJECT/'research/batch48/provenance.json').read_bytes()
    rollback = read(PROJECT/manifest['rollback_manifest_path'])
    assert sha(PROJECT/manifest['rollback_manifest_path']) == manifest['rollback_manifest_sha']
    for row in rollback['snapshots'].values():
        assert sha(PROJECT/row['snapshot']) == row['sha']
    checked = 0
    for group in ('compile_inputs','test_inputs','generation_inputs','reports'):
        for name, expected in manifest[group].items():
            assert sha(PROJECT/name) == expected, name
            checked += 1
    for name, text in manifest['release_flags'].items():
        assert (PROJECT/name).read_text() == text, name
    for name, expected in [
        ('solution/solution.cpp',manifest['source_sha256']),
        (manifest['default_exe_path'],manifest['default_exe_sha256']),
        (manifest['default_archive'],manifest['default_exe_sha256']),
        (manifest['measured_exe_path'],manifest['measured_exe_sha256']),
        ('research/batch45/solution.cpp',manifest['old_default_R45_source_sha']),
        ('research/batch45/default-aicore_bench.exe',manifest['old_default_R45_exe_sha']),
        ('reports/project27-research.tex',manifest['old_frozen_R31_tex_sha']),
    ]:
        assert sha(PROJECT/name) == expected, name
    log = (PROJECT/'reports/ctest-default-batch48.txt').read_text()
    assert '100% tests passed, 0 tests failed out of 13' in log
    test = (PROJECT/'tests/test_projection.cpp').read_text()
    assert '#include "../solution/solution.cpp"' in test
    assert 'solution/solution.cpp' in (PROJECT/'build/CMakeCache.txt').read_text()
    smoke = manifest['default_smoke']
    input_path = PROJECT/'data/default-smoke-batch48.json'
    output_path = PROJECT/'reports/default-smoke-batch48.json'
    assert sha(input_path) == smoke['input_sha']
    assert sha(output_path) == smoke['report_sha']
    cases, outputs = read(input_path)['cases'], read(output_path)['cases']
    assert len(cases) == len(outputs) == 9
    candidates = {label:read(PROJECT/path)['cases'] for label,path in [
        ('hard','reports/paired-hard-batch48-1-after.json'),
        ('heldout','reports/paired-heldout-batch48-1-after.json')]}
    passing = 0
    for case,row,(family,index) in zip(cases,outputs,smoke['selection']):
        assert not any('witness' in key or 'generation' in key for key in case)
        original = candidates[family][index]
        for field in ('name','pass','valid','T','peak_memory','models_equal'):
            assert row[field] == original[field]
        assert case['name'] == row['name']
        if row['pass']:
            assert simulate(case,row['plan']) == (row['T'],row['peak_memory'])
            passing += 1
    assert passing == 6 and smoke['actual_exit_code'] == 1
    result = dict(passed=True,reviewed_unix=time.time(),source_sha256=manifest['source_sha256'],
                  default_exe_sha256=manifest['default_exe_sha256'],
                  measured_exe_sha256=manifest['measured_exe_sha256'],
                  checked_inputs=checked,ctest=13,actual_default_cases=9,
                  independent_heap_replays=passing,explicit_unresolved=3,
                  hard_legal=144,hard_unresolved=58,fresh48_legal=42,fresh48_unresolved=6,
                  evidence={path.relative_to(ROOT).as_posix():sha(path) for path in (manifest_path,input_path,output_path)},
                  scope='Actual default source/binary/archive/Release flags/tests/input provenance,13 default CTest and9 actual representative records checked against accepted candidate. Root arbitrary-precision heap independently replays6 passing actual default outputs,3 known feasible failures explicit. Measured991e remains distinct from default54fc; R45 rollback intact, open old TeX unchanged. Full979/numeric/186-plan evidence from frozen candidate is not claimed rerun on this default executable.')
    (ROOT/'outputs/stage2-root-default-r48.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
