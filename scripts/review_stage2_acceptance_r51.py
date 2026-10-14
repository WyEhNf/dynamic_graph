"""Root verification of completed R51 regression and sanitizer gates."""
import json
import time
from pathlib import Path
from review_stage2_acceptance_r48 import sha, read

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/27-aicore-streams'


def main():
    path = P/'research/batch51/acceptance-checkpoint.json'; m = read(path)
    assert sha(path) == '5d302ad593c744d54f76f879f6268b4ec8eeb453c7a1f1e49f869138aecffa63'
    assert m['source_sha'] == '8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
    for group in ('compile_inputs', 'generation_inputs', 'data_inputs', 'executables', 'reports'):
        for name, expected in m[group].items():
            assert sha(P/name) == expected, name
    for name, expected in m['compile_flags'].items():
        assert (P/name).read_text() == expected
        assert '-O3' in expected and '-DNDEBUG' in expected
    assert sha(P/'research/batch51/validation-plan.json') == m['validation_plan_sha']
    repair = read(P/'research/batch51/environment-repair.json')
    assert sha(P/'research/batch51/environment-repair.json') == m['environment_repair_sha']
    assert repair['initial_actual_exit'] == 1 and repair['retry_actual_exit'] == 0
    assert not repair['initial_tests_started']
    assert 'No space left on device' in (P/'reports/validation-build-initial-enospc-batch51.txt').read_text()
    assert '100% tests passed, 0 tests failed out of 14' in (P/'reports/validation-ctest-batch51.txt').read_text()
    report = read(P/'reports/full-verification-batch51.json'); suites = list(report['equal_suites'])
    for status in report['statuses']:
        assert status['actual_exit_code'] == 0
        if 'label' not in status:
            continue
        label = status['label']
        suites.append(dict(suite=label, records=status['records'],
            before=f'reports/{label}-candidate-batch48.json', after=f'reports/{label}-candidate-batch51.json',
            before_sha=status['before_sha'], after_sha=status['after_sha']))
    checked = []
    for suite in suites:
        before, after = P/suite['before'], P/suite['after']
        assert sha(before) == suite['before_sha'] and sha(after) == suite['after_sha']
        lhs, rhs = read(before)['cases'], read(after)['cases']
        assert len(lhs) == len(rhs) == suite['records']
        for a, b in zip(lhs, rhs):
            assert all(a[k] == b[k] for k in ('name', 'pass', 'valid', 'T', 'peak_memory'))
            assert b['pass']
        checked.append(dict(suite=suite['suite'], records=len(rhs)))
    assert sum(s['records'] for s in checked) == 1099
    gold = read(ROOT/'outputs/stage2-root-heap-numeric-gold-r44.json')
    numeric = read(P/'reports/full-numeric-verification-batch51.json')
    data_paths = [ROOT/r['path'] for r in gold['results']] + [P/'data/release-cut-fixed-gold-batch51.json']
    controls = 0
    for data_path, run in zip(data_paths, numeric['runs'][:5]):
        output = P/f"reports/{run['label']}-validation-ubsan-batch51.json"
        assert sha(data_path) == run['input_sha'] and sha(output) == run['output_sha']
        assert sha(output.with_suffix('.txt')) == run['log_sha']
        assert run['actual_exit_code'] == 0
        data, rows = read(data_path)['cases'], read(output)['cases']
        assert len(data) == len(rows) == run['controls']
        for case, row in zip(data, rows):
            assert row['name'] == case['name'] and row['pass']
            assert row['valid'] == row['production_valid'] == case['gold_valid']
            if row['valid']:
                assert (row['T'], row['peak']) == (int(case['gold_T']), int(case['gold_peak']))
        controls += len(rows)
    assert controls == 625 and numeric['UBSan_runtime_errors'] == 0
    for label, input_path, expected in (
        ('projection', 'data/projection-gold-batch45.json', '495 independent full-ancestor/live-set bigint controls passed'),
        ('group', 'data/group-gold-batch48.json', '83 recognition controls / 210 group moves: independent bigint passed'),
        ('cut', 'data/release-cut-gold-batch51.json', '102 original remaining-DIRECT/ancestor cut bigint controls passed'),
    ):
        run = next(r for r in numeric['runs'] if r['label'] == label)
        log = P/f'reports/{label}-profile-ubsan-batch51.txt'
        assert run['actual_exit_code'] == 0 and sha(P/input_path) == run['input_sha']
        assert sha(log) == run['log_sha'] and log.read_text().strip() == expected == run['output']
        assert 'runtime error:' not in log.read_text()
    assert sha(P/'solution/solution.cpp') == m['default48_source_sha']
    assert sha(P/'build/aicore_bench.exe') == m['default48_exe_sha']
    assert sha(P/'reports/project27-research.tex') == m['old_user_open_tex_sha'] == 'e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
    full = read(ROOT/'outputs/stage2-root-functional-plans-r51.json')
    cut = read(ROOT/'outputs/stage2-root-release-cut-gold-r51.json')
    assert full['passed'] and full['independently_validated'] == 187
    assert cut['passed'] and cut['independent_cut_controls'] == 102
    result = dict(passed=True, reviewed_unix=time.time(), same_regression_records=1099,
        numeric_fixed_controls=625, release_ctest=14, workspace_profile_controls=495,
        group_recognition_controls=83, group_moved_profiles=210, release_cut_controls=102,
        independent_actual_full_candidate_plans=187, suites=checked,
        candidate_source_sha256=m['source_sha'],
        frozen_release_sha256=m['executables']['research/batch51/release-candidate-frozen-aicore_bench.exe'],
        environment_initial_failure_preserved=True,
        evidence={p.relative_to(ROOT).as_posix(): sha(p) for p in (path, P/'reports/full-verification-batch51.json', P/'reports/full-numeric-verification-batch51.json', P/'research/batch51/environment-repair.json')},
        scope='All1099 before/after records and625 actual Clang sanitizer fixed-plan results verified; 102 new cut gold/full plans separately independently recomputed by root. All frozen source/flags/data/executable/report hashes and actual14CTest terminal log checked. Original ENOSPC retained; process-local F temp repair only. Default R48 and open historical TeX preserved. Paired resources and promotion pending.')
    (ROOT/'outputs/stage2-root-acceptance-r51.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence', 'suites')}))


if __name__ == '__main__':
    main()
