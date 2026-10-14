"""Root review of frozen R45 acceptance, without executing project code."""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/27-aicore-streams'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest_path = PROJECT/'research/batch48/acceptance-checkpoint.json'
    manifest = read(manifest_path)
    for group in ('compile_inputs', 'generation_inputs', 'data_inputs', 'executables', 'reports'):
        for name, expected in manifest[group].items():
            assert sha(PROJECT/name) == expected, name
    for name, expected in manifest['compile_flags'].items():
        assert (PROJECT/name).read_text() == expected, name
    report_path = PROJECT/'reports/full-verification-batch48.json'
    report = read(report_path)
    suites = []
    equal = list(report['equal_suites'])
    prior = read(PROJECT/'reports/full-verification-batch45.json')['equal_suites']
    for status in report['statuses']:
        if 'label' not in status:continue
        label=status['label']
        before=next(r['after'] for r in prior if r['suite']==label)
        equal.append(dict(suite=label,records=status['records'],before=before,
                          after=f'reports/{label}-candidate-batch48.json',
                          before_sha=status['before_sha'],after_sha=status['after_sha']))
    for suite in equal:
        before = PROJECT/suite['before']
        after = PROJECT/suite['after']
        assert sha(before) == suite['before_sha']
        assert sha(after) == suite['after_sha']
        lhs, rhs = read(before)['cases'], read(after)['cases']
        assert len(lhs) == len(rhs) == suite['records']
        for left, right in zip(lhs, rhs):
            for field in ('name', 'pass', 'valid', 'T', 'peak_memory'):
                assert left[field] == right[field], (suite['suite'], field)
            assert right['pass']
        suites.append({'suite': suite['suite'], 'records': len(rhs)})
    assert sum(row['records'] for row in suites) == 1099
    assert all(row['actual_exit_code'] == 0 for row in report['statuses'])
    assert '100% tests passed, 0 tests failed out of 13' in (PROJECT/'reports/validation-ctest-batch48.txt').read_text()
    gold = read(ROOT/'outputs/stage2-root-heap-numeric-gold-r44.json')
    numeric = read(PROJECT/'reports/full-numeric-verification-batch48.json')
    controls = 0
    for original, execution in zip(gold['results'], numeric['runs']):
        data_path = ROOT/original['path']
        output_path = PROJECT/f"reports/{execution['label']}-validation-ubsan-batch48.json"
        log_path = output_path.with_suffix('.txt')
        assert sha(data_path) == original['sha256'] == execution['input_sha']
        assert sha(output_path) == execution['output_sha']
        assert sha(log_path) == execution['log_sha']
        assert execution['actual_exit_code'] == 0
        data, output = read(data_path)['cases'], read(output_path)['cases']
        assert len(data) == len(output) == execution['controls']
        for case, row in zip(data, output):
            assert case['name'] == row['name'] and row['pass']
            assert row['valid'] == row['production_valid'] == case['gold_valid']
            if row['valid']:
                assert row['T'] == int(case['gold_T'])
                assert row['peak'] == int(case['gold_peak'])
        controls += len(output)
    assert controls == 523 and numeric['UBSan_runtime_errors'] == 0
    assert sha(PROJECT/'solution/solution.cpp') == manifest['baseline45_source_sha']
    assert sha(PROJECT/'build/aicore_bench.exe') == manifest['baseline45_exe_sha']
    old_tex = PROJECT/'reports/project27-research.tex'
    assert sha(old_tex) == 'e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
    result = dict(passed=True, reviewed_unix=time.time(), same_regression_records=1099,
                  normal_records=979, additional_structure_records=120, numeric_controls=controls,
                  source_files=len(manifest['compile_inputs']), ctest=13, suites=suites,
                  candidate_source_sha256=manifest['source_sha'],
                  measured_release_sha256=manifest['executables']['research/batch48/release-candidate-frozen-aicore_bench.exe'],
                  evidence={str(path.relative_to(ROOT)).replace('\\', '/'):sha(path)
                            for path in (manifest_path, report_path, PROJECT/'reports/full-numeric-verification-batch48.json')},
                  scope='Every1099 actual before/after name/pass/valid/T/peak record,523 actual sanitizer outputs vs previously independent bigint gold, frozen compile/source/binary/report hashes and13 terminal CTest log checked. Root186 independent heap-plan replay remains separate. R48 is isolated, defaultR45 and open TeX unchanged; no performance or universal feasibility claim.')
    (ROOT/'outputs/stage2-root-acceptance-r48.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
