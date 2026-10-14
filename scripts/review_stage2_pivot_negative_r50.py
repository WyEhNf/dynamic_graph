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
    checkpoint_path = PROJECT / 'research/batch50/functional-checkpoint.json'
    checkpoint = read(checkpoint_path)
    for filename, expected in checkpoint['sha256'].items():
        assert sha(PROJECT / filename) == expected, filename
    assert all(row['actual_exit_code'] == 0 for row in checkpoint['statuses'])
    results = {}
    heap_count = 0
    common_improvements = []
    for label, count, legal, prefix, inputs_path in [
        ('unresolved', 61, 3, 'projection-unresolved-diagnostic', 'data/unresolved-r44-input-only-batch45.json'),
        ('heldout-unresolved', 6, 0, 'projection-heldout-unresolved-diagnostic', 'data/projection-heldout-unresolved-input-only-batch45.json')]:
        cases = {r['name']: r for r in read(PROJECT / inputs_path)['cases']}
        before = {r['name']: r for r in read(PROJECT / f'reports/{prefix}-batch48.json')['cases']}
        after = {r['name']: r for r in read(PROJECT / f'reports/{prefix}-batch50.json')['cases']}
        assert len(cases) == len(before) == len(after) == count
        assert cases.keys() == before.keys() == after.keys()
        for name, row in after.items():
            assert set(cases[name]) == {'name', 'hardware', 'nodes', 'deadline_us'}
            assert row['pass'] == before[name]['pass'] and row['applicable'] == before[name]['applicable']
            if row['pass']:
                assert row['valid'] and simulate(cases[name], row['plan']) == (row['T'], row['peak_memory'])
                assert row['T'] == before[name]['T'] and row['peak_memory'] <= before[name]['peak_memory']
                if row['peak_memory'] < before[name]['peak_memory']:
                    common_improvements.append(dict(name=name,T=row['T'],before_peak=before[name]['peak_memory'],after_peak=row['peak_memory']))
                heap_count += 1
        assert sum(r['pass'] for r in after.values()) == legal
        summary = checkpoint['summary'][label]
        assert summary['after']['total'] == count and summary['after']['legal'] == legal
        assert not summary['newly_recovered'] and not summary['lost']
        results[label] = dict(inputs=count, legal=legal, newly_recovered=0, lost=0,
                              budget_exhausted=sum(r['exhausted'] for r in after.values()))
    counterexample = read(PROJECT / 'research/batch50/first-pivot-counterexample.json')
    controls = []
    for row in counterexample['results']:
        case = {key: counterexample[key] for key in ('hardware', 'nodes', 'deadline_us')}
        case['hardware'] = dict(case['hardware'], memory_limit=381)
        T, peak = simulate(case, row['fixed_plan'])
        assert (T, peak) == (row['full_schedule']['T'], row['full_schedule']['peak'])
        assert row['original_capacity_feasible'] == (peak <= counterexample['hardware']['memory_limit'])
        controls.append(dict(label=row['label'], T=T, peak=peak, original301_feasible=peak <= 301))
    assert [r['peak'] for r in controls] == [381, 381, 301]
    result = dict(common_memory_improvements=common_improvements, counterexample_controls=controls, passed=True, reviewed_unix=time.time(), suites=results,
                  independent_actual_heap_plans=heap_count,
                  evidence={checkpoint_path.relative_to(ROOT).as_posix(): sha(checkpoint_path)},
                  scope='All67 input-only records retained and all3 passing actual plans independently replayed. '
                        'Candidate source/producer/data/executable/report SHA and recorded real exit codes inspected. '
                        'No newly feasible recovery from first-member insertion pivot; one existing131-node peak1946to1884 improvement retained; do not promote or spend full performance window. '
                        'Root independently replays3 complete counterexample plans with original DAG and broad381 capacity, then checks original301 feasibility; first-member301 versus381 other pivots is genuine full-schedule memory effect. Root did not independently recompute all group-move gold values.')
    (ROOT / 'outputs/stage2-root-group-negative-r50.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
