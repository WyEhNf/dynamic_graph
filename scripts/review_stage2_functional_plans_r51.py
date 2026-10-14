"""Root replay of every complete R51 plan against the unchanged input corpus."""
import json
import time
from pathlib import Path
from review_stage2_functional_plans_r44 import simulate, sha

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/27-aicore-streams'


def main():
    suites = []
    validated = 0
    common = 0
    for label, source, before_path, after_path, count, old_legal, new_legal in (
        ('hard', 'data/hard-corpus-resumed.json', 'reports/hard-functional-batch48.json', 'reports/hard-functional-batch51.json', 202, 144, 145),
        ('retention-heldout', 'data/projection-retention-heldout-batch45.json', 'reports/heldout-functional-batch48.json', 'reports/heldout-functional-batch51.json', 48, 42, 42),
    ):
        paths = {k: PROJECT / v for k, v in (('input', source), ('before', before_path), ('after', after_path))}
        cases, before, after = [{r['name']: r for r in json.loads(paths[k].read_text())['cases']} for k in ('input', 'before', 'after')]
        assert set(cases) == set(before) == set(after) and len(cases) == count
        assert sum(r['pass'] for r in before.values()) == old_legal
        assert sum(r['pass'] for r in after.values()) == new_legal
        recovered = []
        for name, row in after.items():
            assert row['models_equal'] and (not before[name]['pass'] or row['pass'])
            if not row['pass']:
                continue
            T, peak = simulate(cases[name], row['plan'])
            assert row['valid'] and (T, peak) == (row['T'], row['peak_memory'])
            validated += 1
            if before[name]['pass']:
                assert (T, peak) == (before[name]['T'], before[name]['peak_memory'])
                common += 1
            else:
                recovered.append(name)
        suites.append(dict(suite=label, records=count, before_legal=old_legal, after_legal=new_legal,
                           remaining_unresolved=count-new_legal, recovered=recovered, lost=0,
                           common_T_peak_identical=True,
                           evidence={p.relative_to(ROOT).as_posix(): sha(p) for p in paths.values()}))
    assert (validated, common) == (187, 186)
    summary = PROJECT / 'reports/functional-summary-batch51.json'
    producer = json.loads(summary.read_text())
    assert sha(PROJECT / 'research/batch51/solution.cpp') == producer['source_sha']
    assert producer['source_sha'] == '8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
    assert all(j['actual_exit_code'] == 1 for j in producer['jobs'])
    result = dict(reviewed_unix=time.time(), passed=True, independently_validated=validated,
                  common_plans=common, suites=suites, producer_summary_sha=sha(summary),
                  source_sha=producer['source_sha'], benchmark_sha=producer['benchmark_sha'],
                  scope='All actual 145+42 candidate full plans replayed by root bigint heap model; one new 140-node recovery, 186 common T/peak unchanged. All 57+6 unresolved records retained. Functional evidence only; default stays R48. Numeric, regression and paired resource gates pending.')
    (ROOT / 'outputs/stage2-root-functional-plans-r51.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
