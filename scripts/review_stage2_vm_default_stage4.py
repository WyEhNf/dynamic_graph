"""Root whole-file/immutable-input/default-contract audit before maximum shape."""
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from review_stage2_vm_measurements import compare_files, sha

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
STAGE = PROJECT / 'artifacts/stage2-vm-default-integration'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest_path = STAGE / 'acceptance-manifest.json'
    manifest = read(manifest_path)
    assert manifest['passed'] and manifest['source_count'] == 134
    for name, expected in manifest['source_sha256'].items():
        assert sha(STAGE / 'candidate-source' / name) == expected, name
    for row in manifest['binaries'].values():
        assert sha(Path(row['path'])) == row['sha256']
    for row in manifest['ctest'].values():
        assert row['passed'] == 12 and row['actual_exit_code'] == 0
        assert sha(Path(row['path'])) == row['sha256']
        assert '100% tests passed, 0 tests failed out of 12' in Path(row['path']).read_text()
    contracts = []
    for row in manifest['contracts']:
        assert row['actual_exit_code'] == 0
        for field in ('exe', 'stdout', 'stderr'):
            assert sha(Path(row[field])) == row[field + '_sha256']
        actual = subprocess.run([row['exe']], capture_output=True, text=True, timeout=30, check=True)
        assert actual.stdout == Path(row['stdout']).read_text() and actual.stderr == Path(row['stderr']).read_text() == ''
        contracts.append(row['label'])
    report_path = Path(manifest['correctness']['report'])
    assert sha(report_path) == manifest['correctness']['sha256']
    report = read(report_path)
    assert report['passed'] and len(report['sources']) == 13 and len(report['runs']) == 378
    for source in report['sources']:
        assert sha(Path(source['source'])) == source['source_sha256']
        assert sha(Path(source['metadata'])) == source['metadata_sha256']
        old = Path(source.get('cached_original_directory', str(Path(source['source']).parent)))
        assert sha(old / 'oracle.c') == source['harness_sha256']
        assert sha(old / 'oracle.exe') == source['oracle_binary_sha256']
    families = defaultdict(list)
    for row in report['runs']:
        size, hashes = compare_files([Path(row['reference']), Path(row['output'])])
        assert size == row['bytes'] and hashes[0] == hashes[1] == row['sha256'] == row['reference_sha256']
        assert sha(Path(row['input'])) == row['input_sha256']
        assert sha(Path(row['metadata'])) == row['metadata_sha256']
        assert row['selected_engine'] == 'vm'
        if row['backend'] == 'new-default':
            assert row['vm_backend'] == 'decoded-threaded'
        if row['backend'] == 'portable-default':
            assert row['vm_backend'] == 'decoded-fallback'
        families[row['source'], row['family']].append(row)
    assert len(families) == 63
    for rows in families.values():
        assert len(rows) == 6
        assert len({r['vm_steps'] for r in rows if r['backend'] != 'ordinary4f73'}) == 1
    for row in report['failures']:
        outcomes = {(r['exit_code'], r['stderr']) for r in row['results']}
        assert len(row['results']) == 6 and len(outcomes) == 1 and next(iter(outcomes))[0] != 0
        assert sha(Path(row['metadata'])) == row['metadata_sha256']
    assert len(report['failures']) == 7
    assert sha(STAGE / 'rollback4f73/snapshot-manifest.json') == manifest['rollback4f73_manifest_sha256']
    plan_path = STAGE / 'maximum-shape/run-plan.json'
    plan = read(plan_path)
    assert plan['acceptance_manifest_sha256'] == sha(manifest_path)
    assert plan['strict_sequential'] and plan['default_must_reject'] and not plan['large_SHA_verified']
    assert plan['full_output_bytes'] == 800000008 and plan['original_steps'] == 1700000012
    assert plan['minimum_free_ram_bytes'] == 2684354560 and plan['default_limit'] == 1000000000
    for row in plan['binaries'].values():
        assert sha(Path(row['path'])) == row['sha256']
    result = dict(passed=True, reviewed_unix=time.time(), actual_C_outputs=378, sources=13, families=63,
                  ctest_per_GNU_and_portable=12, root_rerun_contract_executables=len(contracts), contracts=contracts,
                  CLI_errors=7, candidate_sha256=manifest['binaries']['candidate.exe']['sha256'],
                  portable_sha256=manifest['binaries']['portable-candidate.exe']['sha256'],
                  maximum_plan_sha256=sha(plan_path), evidence={path.relative_to(ROOT).as_posix(): sha(path) for path in (manifest_path, report_path, plan_path)},
                  scope='All378 actual complete C files/input/source/Metadata/reference/harness/oracle SHA,63 six-backend groups, '
                        'all13 frozen contract executables rerun and both actual12CTest logs checked. New auto/default uses GNU threaded '
                        'or portable decoded fallback; original native paths preserved. Maximum resource plan checked but no maximum '
                        'execution or large-file hash yet, no installed-default or broad generic N10000 claim.')
    (ROOT / 'outputs/stage2-root-vm-default-stage4.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope', 'contracts')}))


if __name__ == '__main__':
    main()
