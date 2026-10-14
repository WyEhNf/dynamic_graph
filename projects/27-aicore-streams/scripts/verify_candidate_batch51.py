"""Explicit979 directR48 baseline, structure36/new72/resource12; all failures."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
start=time.perf_counter();statuses=[]
commands=[['C:/Users/admin/miniconda3/python.exe','scripts/regress_current.py','--label','batch51','--bench','research/batch51/aicore_bench.exe','--source','research/batch51/solution.cpp'],['C:/Users/admin/miniconda3/python.exe','scripts/audit_certificates.py','--label','batch51','--source','research/batch51/solution.cpp']]
for cmd in commands:
    begin=time.perf_counter();r=subprocess.run(cmd,capture_output=True,text=True);label='regression' if '--bench' in cmd else 'audit';Path(f'reports/{label}-validation-batch51.txt').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0;statuses.append(dict(command=cmd,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-begin));print(label,'actualexit0',flush=True)
reg=json.loads(Path('reports/regression-batch51.json').read_text());equal=[]
for label in reg['comparisons']:
    before=Path(f'reports/{label}-batch48.json');after=Path(f'reports/{label}-batch51.json');a=json.loads(before.read_text())['cases'];b=json.loads(after.read_text())['cases'];assert len(a)==len(b) and all(all(x[k]==y[k] for k in ('name','pass','valid','T','peak_memory')) for x,y in zip(a,b));equal.append(dict(suite=label,records=len(a),before=str(before),after=str(after),before_sha=sha(before),after_sha=sha(after)))
assert sum(x['records'] for x in equal)==979
for label,data,before in [('forkjoin','data/nested-forkjoin-new-batch38.json','reports/forkjoin-candidate-batch48.json'),('shallow-heldout','data/shallow-heldout-batch44.json','reports/shallow-heldout-candidate-batch48.json'),('resource-cliques','data/resource-cliques-batch31.json','reports/resource-cliques-candidate-batch48.json')]:
    after=f'reports/{label}-candidate-batch51.json';r=subprocess.run(['research/batch51/aicore_bench.exe','--input',data,'--output',after],capture_output=True,text=True);Path(f'reports/{label}-status-batch51.txt').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0
    a=json.loads(Path(before).read_text())['cases'];b=json.loads(Path(after).read_text())['cases'];assert len(a)==len(b) and all(all(x[k]==y[k] for k in ('name','pass','valid','T','peak_memory')) for x,y in zip(a,b));statuses.append(dict(label=label,actual_exit_code=r.returncode,records=len(b),before_sha=sha(before),after_sha=sha(after),all_fields_equal=True));print(label,'actualexit0',flush=True)
report=dict(status='passed candidate full functional regression',source_sha=sha('research/batch51/solution.cpp'),bench_sha=sha('research/batch51/aicore_bench.exe'),normal979_direct_R48_same_every_record=True,equal_suites=equal,statuses=statuses,shared_functional_wall_seconds=time.perf_counter()-start,timing='Shared functional only; no paired cost conclusion')
Path('reports/full-verification-batch51.json').write_text(json.dumps(report,indent=2));print('R51 actual full functional acceptance exit0',flush=True)
