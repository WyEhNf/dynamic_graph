"""Nine actual-default behavior checks, not repeat full acceptance or timing."""
import hashlib,json,subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
hard=json.loads(Path('data/hard-corpus-resumed.json').read_text())['cases'];held=json.loads(Path('data/projection-retention-heldout-batch45.json').read_text())['cases']
hard_results=json.loads(Path('reports/hard-functional-batch48.json').read_text())['cases'];held_results=json.loads(Path('reports/heldout-functional-batch48.json').read_text())['cases'];assert len(hard)==len(hard_results) and len(held)==len(held_results)
recovered=json.loads(Path('reports/functional-summary-batch48.json').read_text())['comparisons']['hard']['recovered']+json.loads(Path('reports/functional-summary-batch45.json').read_text())['comparisons']['hard']['recovered'];assert len(recovered)==3
selected=[('hard',i) for i,c in enumerate(hard) if c['name'] in recovered]
passed=[i for i,r in enumerate(held_results) if r['pass']];failed=[i for i,r in enumerate(held_results) if not r['pass']]
selected += [('heldout',passed[j]) for j in (0,len(passed)//2,len(passed)-1)]+[('heldout',i) for i in failed[:2]]
selected += [('hard',min((i for i,r in enumerate(hard_results) if not r['pass']),key=lambda i:len(hard[i]['nodes'])))]
inputs=[];expected=[]
for family,i in selected:
    c=hard[i] if family=='hard' else held[i];r=hard_results[i] if family=='hard' else held_results[i];assert c['name']==r['name'];inputs.append({k:c[k] for k in ('name','hardware','nodes','deadline_us','expected_feasible')});expected.append(r)
p=Path('data/default-smoke-batch48.json');p.write_text(json.dumps(dict(format='aicore-local-v1',cases=inputs)),encoding='utf-8')
run=subprocess.run(['build/aicore_bench.exe','--input',str(p),'--output','reports/default-smoke-batch48.json','--csv','reports/default-smoke-batch48.csv'],capture_output=True,text=True);Path('reports/default-smoke-batch48.txt').write_text(run.stdout+run.stderr,encoding='utf-8');assert run.returncode==1
actual=json.loads(Path('reports/default-smoke-batch48.json').read_text())['cases'];assert len(actual)==len(expected)==9
for a,b in zip(actual,expected):assert all(a[k]==b[k] for k in ('name','pass','valid','T','peak_memory','models_equal'))
report=dict(status='actual default9 unchanged vs fully accepted candidate;three witness-feasible failures remain explicit',actual_exit_code=run.returncode,count=9,passing=sum(r['pass'] for r in actual),unresolved=sum(not r['pass'] for r in actual),three_recoveries=recovered,selection=selected,input_sha=sha(p),report_sha=sha('reports/default-smoke-batch48.json'),source_sha=sha('solution/solution.cpp'),exe_sha=sha('build/aicore_bench.exe'),timing='Shared functionality;no new full979 or performance inference',witness_or_generation_passed_to_solver=False)
Path('reports/default-smoke-summary-batch48.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
