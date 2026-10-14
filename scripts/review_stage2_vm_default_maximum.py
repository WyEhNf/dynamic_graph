"""Stream exact N10000 files with <=5MiB buffers; no matrix loading."""
import json
import time
from pathlib import Path
from review_stage2_vm_measurements import compare_files, sha

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
STAGE = PROJECT / 'artifacts/stage2-vm-default-integration'


def read(path):
    return json.loads(path.read_text())


def main():
    folder = STAGE / 'maximum-shape'
    plan_path, report_path = folder / 'run-plan.json', folder / 'report.json'
    plan, report = read(plan_path), read(report_path)
    assert report['passed'] and report['status'] == 'complete'
    assert sha(plan_path) == report['plan_sha256']
    assert report['large_SHA_verified'] and not report['default_budget_passed'] and report['explicit_budget_passed']
    assert sha(STAGE / 'acceptance-manifest.json') == plan['acceptance_manifest_sha256']
    old = PROJECT / 'artifacts/stage2-prepared-vm-phase1/maximum-shape'
    for name, expected in plan['historical_sha256'].items():
        assert sha(old / name) == expected, name
    for row in plan['binaries'].values():
        assert sha(Path(row['path'])) == row['sha256']
    assert sha(folder / 'test-script.py') == plan['script_sha256']
    assert sha(folder / 'windows_resource_probe.py') == plan['resource_probe_sha256']
    files = [Path(plan['historical_C_output']), folder / 'oracle.bin'] + [Path(r['output']) for r in report['runs']]
    size, hashes = compare_files(files)
    assert size == 800000008 and len(set(hashes)) == 1 and hashes[0] == plan['historical_sha256']['oracle.bin']
    assert report['oracle']['actual_exit_code'] == 0 and report['oracle']['bytes'] == size and report['oracle']['sha256'] == hashes[0]
    assert len(report['runs']) == 3 and [r['backend'] for r in report['runs']] == plan['backend_order']
    resources = []
    for row in report['runs']:
        assert row['actual_exit_code'] == 0 and row['bytes'] == size and row['sha256'] == hashes[0]
        assert row['explicit_budget'] == 10000000000 and row['vm_steps'] == 1700000012
        assert row['selected_engine'] == 'vm'
        assert row['vm_backend'] == {'GNUauto': 'decoded-threaded', 'GNUdecoded': 'decoded', 'portableauto': 'decoded-fallback'}[row['backend']]
        assert row['available_ram_before_bytes'] >= plan['minimum_free_ram_bytes']
        assert row['resource_samples'] > 0 and row['process_peak_working_set_bytes'] > 0 and row['process_peak_commit_bytes'] > 0
        resources.append({field: row[field] for field in ('backend', 'vm_backend', 'vm_steps', 'available_ram_before_bytes',
            'process_peak_working_set_bytes', 'process_peak_commit_bytes', 'host_available_ram_min_bytes', 'host_busy_percent_during_process')})
    assert all(r['passed'] and r['available_ram_bytes'] >= plan['minimum_free_ram_bytes'] for r in report['resource_gates'])
    negative = report['default_failure']
    assert negative['actual_exit_code'] == 1 and negative['default_budget'] == 1000000000 and negative['unpublished_output']
    assert negative['stderr'] == 'error: VM instruction limit exceeded\n'
    assert not (folder / 'default-budget-rejected.bin').exists() and not (folder / 'default-budget-rejected.bin.partial').exists()
    result = dict(passed=True, reviewed_unix=time.time(), n=10000, actual_C_reference_rerun=True,
                  complete_files_stream_compared=5, full_bytes_per_file=size, explicit_backends=resources,
                  default_budget_passed=False, explicit_budget_passed=True,
                  evidence={p.relative_to(ROOT).as_posix(): sha(p) for p in (plan_path, report_path)},
                  scope='Independent root stream comparison of historicalC, new actualC and three actual backend800000008byte files, '
                        'including headers; historical source/Meta/input/harness/oracle/executable SHA rechecked with bounded buffers. '
                        'Original1700000012 steps and sequential fresh>=2.5GiB RAM gates checked. Default1e9 rejection explicit; '
                        'explicit1e10 only proves this N10000 copy source, not all generic sources/default-budget acceptance or paired performance.')
    (ROOT / 'outputs/stage2-root-vm-default-maximum.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
