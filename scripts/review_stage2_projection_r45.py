"""Freeze and independently replay the first input-only ancestor-closure recoveries."""
import hashlib
import json
import shutil
import time
from pathlib import Path
from review_stage2_functional_plans_r44 import simulate

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/27-aicore-streams'
SNAPSHOT = ROOT/'outputs/stage2-projection-r45-root-snapshot'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    SNAPSHOT.mkdir(exist_ok=True)
    sources = {
        'inputs.json':'data/unresolved-r44-input-only-batch45.json',
        'diagnostic.json':'reports/projection-unresolved-diagnostic-batch45.json',
        'solution.cpp':'research/batch45/solution.cpp',
        'projection.cpp.inc':'research/batch45/projection.cpp.inc',
        'diagnostic.exe':'research/batch45/diagnostic.exe',
    }
    for name, relative in sources.items():
        destination = SNAPSHOT/name
        # Keep the exact reviewed milestone even while research moves on.
        if not destination.exists():
            shutil.copyfile(PROJECT/relative,destination)
    cases = {r['name']:r for r in json.loads((SNAPSHOT/'inputs.json').read_text())['cases']}
    diagnostic = json.loads((SNAPSHOT/'diagnostic.json').read_text())
    rows = diagnostic['cases']
    original = {r['name']:r for r in json.loads((PROJECT/'data/hard-corpus-resumed.json').read_text())['cases']}
    before = {r['name']:r for r in json.loads((PROJECT/'reports/hard-functional-batch44.json').read_text())['cases']}
    assert set(cases) == {r['name'] for r in rows} and len(cases) == 61
    recovered = []
    for row in rows:
        case = cases[row['name']]
        assert set(case) == {'name','hardware','nodes','deadline_us'}
        for key in ('hardware','nodes','deadline_us'):
            assert case[key] == original[row['name']][key]
        assert not before[row['name']]['pass']
        if row['pass']:
            T, peak = simulate(case,row['plan'])
            assert row['valid'] and (T,peak) == (row['T'],row['peak_memory'])
            recovered.append(dict(name=row['name'],nodes=len(case['nodes']),T=T,peak=peak,
                                  capacity=case['hardware']['memory_limit'],stream_count=len(row['plan']['streams'])))
    assert len(recovered) == 2 and sum(row['applicable'] for row in rows) == 35
    result = dict(reviewed_unix=time.time(),passed=True,records=61,applicable=35,
                  recovered_records=2,recovered=recovered,
                  evidence={p.relative_to(ROOT).as_posix():digest(p) for p in SNAPSHOT.iterdir() if p.is_file()},
                  verifier_sha256=digest(ROOT/'scripts/review_stage2_functional_plans_r44.py'),
                  scope='Root independent Python bigint heap-event replay of2 actual complete serial plans, same original nodes/hardware/deadline. Input-only61 subset contains no witness/generation fields. Both were previously unresolved in frozenR44. One topology with2 root-memory parameter settings; no default promotion, broad solver validity, performance or official score claim. All61 statuses retained.')
    (ROOT/'outputs/stage2-root-projection-r45.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))


if __name__ == '__main__':
    main()
