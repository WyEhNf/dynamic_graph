"""One authorized whole regression. Default44 is not modified."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
bench='research/batch45/aicore_bench.exe';source='research/batch45/solution.cpp';start=time.perf_counter();statuses=[]
def run(label,args):
    t=time.perf_counter();r=subprocess.run(args,capture_output=True,text=True);Path(f'reports/verification-{label}-batch45.txt').write_text(r.stdout+r.stderr,encoding='utf-8');print(label,r.returncode,r.stdout.strip()[-500:]);statuses.append(dict(label=label,command=args,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-t));assert r.returncode==0
py='C:/Users/admin/miniconda3/python.exe'
run('regression',[py,'scripts/regress_current.py','--label','batch45','--bench',bench,'--source',source])
run('certificate',[py,'scripts/audit_certificates.py','--label','batch45','--source',source])
reg=json.loads(Path('reports/regression-batch45.json').read_text());assert reg['case_records']==979
equal=[]
for label in reg['comparisons']:
    a=Path(f'reports/{label}-batch44.json');b=Path(f'reports/{label}-batch45.json');old=json.loads(a.read_text())['cases'];new=json.loads(b.read_text())['cases'];assert len(old)==len(new)
    assert all(tuple(x[k] for k in ['name','pass','valid','T','peak_memory'])==tuple(y[k] for k in ['name','pass','valid','T','peak_memory']) for x,y in zip(old,new))
    equal.append(dict(suite=label,records=len(new),before=str(a),after=str(b),before_sha=sha(a),after_sha=sha(b)))
for label,data,before in [('forkjoin','data/nested-forkjoin-new-batch38.json','reports/forkjoin-functional-batch44.json'),('shallow-heldout','data/shallow-heldout-batch44.json','reports/heldout-after-functional-batch44.json'),('resource-cliques','data/resource-cliques-batch31.json','reports/resource-cliques-batch44.json')]:
    after=f'reports/{label}-candidate-batch45.json';run(label,[bench,'--input',data,'--output',after,'--csv',after.replace('.json','.csv')]);a=json.loads(Path(before).read_text())['cases'];b=json.loads(Path(after).read_text())['cases'];assert len(a)==len(b)
    assert all(tuple(x[k] for k in ['name','pass','valid','T','peak_memory'])==tuple(y[k] for k in ['name','pass','valid','T','peak_memory']) for x,y in zip(a,b)) and all(x['models_equal'] for x in b)
    equal.append(dict(suite=label,records=len(b),before=before,after=after,before_sha=sha(before),after_sha=sha(after)))
report=dict(status='passed candidate functional regression',source_sha=sha(source),bench_sha=sha(bench),normal_979_direct_R44_all_record_equal=True,equal_suites=equal,statuses=statuses,shared_total_wall_seconds=time.perf_counter()-start,default44_source_sha=sha('solution/solution.cpp'),timing='Shared functional execution only; no speed comparison')
Path('reports/full-verification-batch45.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('R45 whole quality passed; default44 preserved')
