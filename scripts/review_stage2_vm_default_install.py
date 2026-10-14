"""Verify the installed binary against immutable release and all actual C files."""
import json
import time
from collections import Counter
from pathlib import Path
from review_stage2_vm_measurements import compare_files, sha

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
STAGE = PROJECT / 'artifacts/stage2-vm-default-integration'
FOLDER = STAGE / 'ordinary-install'


def read(path):
    return json.loads(path.read_text())


def main():
    release_path, report_path = FOLDER / 'release-manifest.json', FOLDER / 'verification-report.json'
    release, report = read(release_path), read(report_path)
    assert release['passed'] and report['passed'] and report['status'] == 'complete'
    assert sha(report_path) == release['verification_report_sha256']
    assert sha(Path(release['installed_runtime'])) == sha(Path(release['frozen_runtime'])) == release['runtime_sha256'] == report['actual_runtime_sha256']
    for name, expected in release['source_sha256'].items():
        assert sha(FOLDER / 'released-source' / name) == expected, name
    assert len(release['source_sha256']) == release['source_count'] == 136
    assert sha(STAGE / 'acceptance-manifest.json') == release['isolated_acceptance_sha256'] == report['source_acceptance_sha256']
    assert sha(STAGE / 'maximum-shape/report.json') == release['maximum_shape_report_sha256'] == report['maximum_report_sha256']
    assert sha(Path(release['ordinary_rollback'])) == release['ordinary_rollback_sha256']
    assert sha(PROJECT / 'build-memory/cholesky_runtime.exe') == release['memory_unchanged_sha256']
    ctest = report['installed_ctest']
    assert ctest['tests'] == 8 and ctest['actual_exit_code'] == 0
    assert sha(FOLDER / 'ctest.stdout') == ctest['stdout_sha256'] and sha(FOLDER / 'ctest.stderr') == ctest['stderr_sha256']
    assert '100% tests passed, 0 tests failed out of 8' in (FOLDER / 'ctest.stdout').read_text()
    counts = Counter()
    for row in report['runs']:
        counts[row['scope']] += 1
        assert row['actual_exit_code'] == 0
        size, hashes = compare_files([Path(row['reference']), Path(row['output'])])
        assert size == row['bytes'] and hashes[0] == hashes[1] == row['sha256'] == row['reference_sha256']
        assert sha(Path(row['input'])) == row['input_sha256']
        assert sha(Path(row['metadata'])) == row['metadata_sha256']
        if row['scope'] == 'generic':
            assert row['selected_engine'] == 'vm' and row['vm_backend'] == 'decoded-threaded'
    assert dict(counts) == report['scope_counts'] == dict(generic=63, wire=60, smallest=24)
    assert len(report['runs']) == release['installed_whole_C_outputs'] == 147
    prior = {r['source']: r['results'][0] for r in read(STAGE / 'correctness/report.json')['failures']}
    for row in report['failures']:
        assert row['actual_exit_code'] == prior[row['source']]['exit_code'] != 0
        assert row['stderr'] == prior[row['source']]['stderr']
        cmd = row['command']
        assert sha(Path(cmd[cmd.index('--metadata') + 1])) == row['metadata_sha256']
        assert sha(Path(cmd[cmd.index('--input') + 1])) == row['input_sha256']
        assert not Path(cmd[cmd.index('--output') + 1]).exists()
    assert len(report['failures']) == release['installed_error_contracts'] == 7
    assert release['default_step_limit'] == 1000000000 and not release['maximum_shape_default_budget_passed']
    assert release['maximum_shape_explicit_budget_passed'] and release['native_AUTO_unchanged'] and release['strict_FP_flags_unchanged']
    result = dict(passed=True, reviewed_unix=time.time(), actual_installed_sha256=release['runtime_sha256'],
                  immutable_source_files=136, installed_ctest=8, actual_complete_C_outputs=147,
                  scopes=dict(counts), error_contracts=7, default_budget_passed=False,
                  maximum_explicit_budget_passed=True,
                  evidence={p.relative_to(ROOT).as_posix(): sha(p) for p in (release_path, report_path)},
                  scope='Actual installed99a8 binary and immutable archive/source/Release flags checked;147 actual completeC files '
                        '(63 generic,60 wire,24 smallest),8 installed CTest and7 exact errors checked. Separate isolated378 files '
                        'and GNU/portable12CTest, explicit1e10 N10000 resource proof remain frozen. Default1e9 generic N10000 '
                        'rejection retained. Old4f73 complete rollback and memory7da06 preserved. No new performance inference.')
    (ROOT / 'outputs/stage2-root-vm-default-install.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
