"""Independent preserved-denominator/actual-plan review of a negative candidate."""
import hashlib
import json
import time
from pathlib import Path
from review_stage2_functional_plans_r44 import simulate

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/27-aicore-streams'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    checkpoint_path = PROJECT / 'research/batch49/functional-checkpoint.json'
    checkpoint = read(checkpoint_path)
    for filename, expected in checkpoint['sha256'].items():
        assert sha(PROJECT / filename) == expected, filename
    assert all(row['actual_exit_code'] == 0 for row in checkpoint['statuses'])
    results = {}
    heap_count = 0
    for label, count, legal, prefix, inputs_path in [
        ('unresolved', 61, 3, 'projection-unresolved-diagnostic', 'data/unresolved-r44-input-only-batch45.json'),
        ('heldout-unresolved', 6, 0, 'projection-heldout-unresolved-diagnostic', 'data/projection-heldout-unresolved-input-only-batch45.json')]:
        cases = {r['name']: r for r in read(PROJECT / inputs_path)['cases']}
        before = {r['name']: r for r in read(PROJECT / f'reports/{prefix}-batch48.json')['cases']}
        after = {r['name']: r for r in read(PROJECT / f'reports/{prefix}-batch49.json')['cases']}
        assert len(cases) == len(before) == len(after) == count
        assert cases.keys() == before.keys() == after.keys()
        for name, row in after.items():
            assert set(cases[name]) == {'name', 'hardware', 'nodes', 'deadline_us'}
            assert row['pass'] == before[name]['pass'] and row['applicable'] == before[name]['applicable']
            if row['pass']:
                assert row['valid'] and simulate(cases[name], row['plan']) == (row['T'], row['peak_memory'])
                assert (row['T'], row['peak_memory']) == (before[name]['T'], before[name]['peak_memory'])
                heap_count += 1
        assert sum(r['pass'] for r in after.values()) == legal
        summary = checkpoint['summary'][label]
        assert summary['after']['total'] == count and summary['after']['legal'] == legal
        assert not summary['newly_recovered'] and not summary['lost']
        results[label] = dict(inputs=count, legal=legal, newly_recovered=0, lost=0,
                              budget_exhausted=sum(r['exhausted'] for r in after.values()))
    result = dict(passed=True, reviewed_unix=time.time(), suites=results,
                  independent_actual_heap_plans=heap_count,
                  evidence={checkpoint_path.relative_to(ROOT).as_posix(): sha(checkpoint_path)},
                  scope='All67 input-only records retained and all3 passing actual plans independently replayed. '
                        'Candidate source/producer/data/executable/report SHA and recorded real exit codes inspected. '
                        'No recovery from group upper limit4to16; do not promote or spend full performance window. '
                        'Independent root did not recompute all342 group-move gold values; those remain producer tests.')
    (ROOT / 'outputs/stage2-root-group-negative-r49.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
