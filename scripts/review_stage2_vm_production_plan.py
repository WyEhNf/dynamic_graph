"""Check the frozen ordinary-default paired experiment before authorizing it."""
import hashlib
import json
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'projects/19-dynamic-graph'
F = P / 'artifacts/stage2-vm-default-integration/production-performance'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def headers(path):
    sizes = []
    with path.open('rb') as f:
        count, = struct.unpack('<I', f.read(4))
        for _ in range(count):
            n, = struct.unpack('<I', f.read(4))
            assert 3 <= n <= 10000
            sizes.append(n)
            f.seek(8*n*n, 1)
        assert f.tell() == path.stat().st_size and f.read() == b''
    return sizes


def main():
    plan = json.loads((F/'run-plan.json').read_text())
    assert sha(F/'run-plan.json') == '808f6a035f036d83b9b7f48cee327a388af30cc25c2e9620e15a5da23cbde6c6'
    assert (plan['records'], plan['pairs'], plan['rounds'], len(plan['cases'])) == (130, 65, 5, 13)
    assert not plan['CLI_backend_override'] and not plan['CLI_budget_override']
    assert plan['engine'] == 'auto' and plan['both_default_budget'] == 1000000000
    assert not plan['new_oracle_execution'] and not plan['timing_based_case_selection']
    assert plan['same_cached_C_repetition'] and not (F/'report.json').exists()
    for key, prefix in [('old-default', '4f73'), ('new-default', '99a8')]:
        row = plan['binaries'][key]
        assert row['sha256'].startswith(prefix) and sha(Path(row['path'])) == row['sha256']
    assert sha(P/'build/cholesky_runtime.exe') == plan['binaries']['new-default']['sha256']
    assert sha(P/'tools/benchmark_vm_production_default_stage4.py') == sha(F/'benchmark-script.py') == plan['script_sha256']
    assert sha(P/'tools/windows_resource_probe.py') == sha(F/'windows_resource_probe.py') == plan['resource_probe_sha256']
    for name, digest in plan['source_snapshot_sha256'].items():
        assert sha(F/'source-frozen'/name) == digest, name
    previous = P/'artifacts/stage2-prepared-vm-phase3/performance/run-plan.json'
    assert sha(previous) == plan['phase3_cohort_plan_sha256']
    prior = {c['source']: c for c in json.loads(previous.read_text())['cases']}
    assert set(prior) == {c['source'] for c in plan['cases']}
    for case in plan['cases']:
        assert case['hashes'] == prior[case['source']]['hashes']
        assert not case['fresh_source'] and not case['fresh_shape'] and case['reused_frozen_cohort']
        assert case['expected_new_reported_steps'] == prior[case['source']]['original_steps']
        folder = F/case['source']
        for name, digest in case['hashes'].items():
            assert sha(folder/name) == digest
        assert headers(folder/'input.bin') == headers(folder/'oracle.bin') == case['input_matrix_headers']
        assert case['input_matrix_headers'] == case['sizes']*case['whole_stream_repeats']
    result = dict(passed=True, reviewed_unix=time.time(), plan_sha=sha(F/'run-plan.json'),
                  frozen_source_files=len(plan['source_snapshot_sha256']), cases=13, records=130, pairs=65,
                  scope='Actual installed default versus old default; complete immutable phase3 cohort reused. No backend/budget override, no invented old counters, no new holdout claim. Performance not yet executed.')
    (ROOT/'outputs/stage2-root-vm-production-plan.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
