"""Independent full-batch plan replay for the isolated ancestor projection candidate."""
import json
import time
from pathlib import Path
from review_stage2_functional_plans_r44 import simulate, sha

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/27-aicore-streams'


def main():
    suites = []
    for label, source, before_path, after_path, count, old_legal, new_legal in (
        ('hard','data/hard-corpus-resumed.json','reports/hard-functional-batch44.json','reports/hard-functional-batch45.json',202,141,143),
        ('retention-heldout','data/projection-retention-heldout-batch45.json','reports/heldout-before-functional-batch45.json','reports/heldout-after-functional-batch45.json',48,42,42),
    ):
        paths = {k:PROJECT/v for k,v in (('input',source),('before',before_path),('after',after_path))}
        cases,before,after = [{row['name']:row for row in json.loads(paths[k].read_text())['cases']} for k in ('input','before','after')]
        assert set(cases) == set(before) == set(after) and len(cases) == count
        assert sum(r['pass'] for r in before.values()) == old_legal
        assert sum(r['pass'] for r in after.values()) == new_legal
        recovered = []
        for name,row in after.items():
            assert row['models_equal'] and (not before[name]['pass'] or row['pass'])
            if not row['pass']:
                continue
            T,peak = simulate(cases[name],row['plan'])
            assert row['valid'] and (T,peak) == (row['T'],row['peak_memory'])
            if before[name]['pass']:
                assert (T,peak) == (before[name]['T'],before[name]['peak_memory'])
            else:
                recovered.append(name)
        suites.append(dict(suite=label,records=count,before_legal=old_legal,after_legal=new_legal,
                           remaining_unknown=count-new_legal,recovered=recovered,lost=0,
                           common_T_peak_identical=True,
                           evidence={p.relative_to(ROOT).as_posix():sha(p) for p in paths.values()}))
    result = dict(reviewed_unix=time.time(),passed=True,independently_validated=185,
                  suites=suites,scope='All actual143+42 plans independently replayed by root bigint heap model. Two old hard failures recovered, same topology/2 parameter settings; fresh48 seeds retain42 legal/6 unresolved, zero fresh recovery. Candidate remains isolated; original default44 remains141/202. DifferentO2/O3 and shared functionalCPU timings cannot support speed/cost/promotion claims.')
    (ROOT/'outputs/stage2-root-functional-plans-r45.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
