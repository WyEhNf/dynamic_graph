"""Ten actual-default checks; no full979 rerun or cost inference."""
import hashlib
import json
import subprocess
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
hard = json.loads(Path('data/hard-corpus-resumed.json').read_text())['cases']
held = json.loads(Path('data/projection-retention-heldout-batch45.json').read_text())['cases']
hard_results = json.loads(Path('reports/hard-functional-batch51.json').read_text())['cases']
held_results = json.loads(Path('reports/heldout-functional-batch51.json').read_text())['cases']
assert len(hard) == len(hard_results) and len(held) == len(held_results)
recoveries = []
for batch in (45,48,51):
    recoveries += json.loads(Path(f'reports/functional-summary-batch{batch}.json').read_text())['comparisons']['hard']['recovered']
assert len(recoveries) == len(set(recoveries)) == 4
selected = [('hard', i) for i,c in enumerate(hard) if c['name'] in recoveries]
passed = [i for i,r in enumerate(held_results) if r['pass']]
failed = [i for i,r in enumerate(held_results) if not r['pass']]
selected += [('heldout', passed[j]) for j in (0, len(passed)//2, len(passed)-1)]
selected += [('heldout', i) for i in failed[:2]]
selected += [('hard', min((i for i,r in enumerate(hard_results) if not r['pass']), key=lambda i:len(hard[i]['nodes'])))]
inputs, expected = [], []
for family, index in selected:
    case = hard[index] if family == 'hard' else held[index]
    result = hard_results[index] if family == 'hard' else held_results[index]
    assert case['name'] == result['name']
    inputs.append({key:case[key] for key in ('name','hardware','nodes','deadline_us','expected_feasible')})
    expected.append(result)
path = Path('data/default-smoke-batch51.json')
path.write_text(json.dumps(dict(format='aicore-local-v1',cases=inputs)),encoding='utf-8')
command = ['build/aicore_bench.exe','--input',str(path),'--output','reports/default-smoke-batch51.json',
           '--csv','reports/default-smoke-batch51.csv']
run = subprocess.run(command,capture_output=True,text=True)
Path('reports/default-smoke-batch51.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
assert run.returncode == 1
actual = json.loads(Path('reports/default-smoke-batch51.json').read_text())['cases']
assert len(actual) == len(expected) == 10
for a,b in zip(actual,expected):
    assert all(a[key] == b[key] for key in ('name','pass','valid','T','peak_memory','models_equal'))
report = dict(status='Actual default10 matches accepted R51 candidate;known-feasible failures explicit',
              actual_exit_code=run.returncode, count=10, passing=sum(row['pass'] for row in actual),
              unresolved=sum(not row['pass'] for row in actual), four_recoveries=recoveries,
              selection=selected,input_sha=sha(path), report_sha=sha('reports/default-smoke-batch51.json'),
              source_sha=sha('solution/solution.cpp'),exe_sha=sha('build/aicore_bench.exe'),
              timing='Shared functionality only;not a new979 or performance batch',
              witness_or_generation_passed_to_solver=False)
Path('reports/default-smoke-summary-batch51.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report),flush=True)
