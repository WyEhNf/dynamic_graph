"""Run exactly original61 with all3 recoveries, and6 fresh input-only cases."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
commands=[('cut',['research/batch51/test_release_cut.exe','data/release-cut-gold-batch51.json']),('hard',['research/batch51/diagnostic.exe','data/unresolved-r44-input-only-batch45.json','reports/projection-unresolved-diagnostic-batch51.json']),('heldout',['research/batch51/diagnostic.exe','data/projection-heldout-unresolved-input-only-batch45.json','reports/projection-heldout-unresolved-diagnostic-batch51.json'])]
statuses=[]
for label,cmd in commands:
    t=time.perf_counter();r=subprocess.run(cmd,capture_output=True,text=True);Path(f'reports/projection-{label}-status-batch51.txt').write_text(r.stdout+r.stderr,encoding='utf-8');print(label,r.returncode,r.stdout.strip(),flush=True);statuses.append(dict(label=label,command=cmd,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-t));assert r.returncode==0
summary={}
for label in ('unresolved','heldout-unresolved'):
    before=json.loads(Path(f'reports/projection-{label}-diagnostic-batch48.json').read_text());after=json.loads(Path(f'reports/projection-{label}-diagnostic-batch51.json').read_text());a,b=before['cases'],after['cases'];assert len(a)==len(b) and all(x['name']==y['name'] for x,y in zip(a,b))
    assert all(x['work']<=16000000 for x in b)
    summary[label]=dict(before=before['summary'],after=after['summary'],newly_recovered=[x['name'] for x,y in zip(a,b) if not x['pass'] and y['pass']],lost=[x['name'] for x,y in zip(a,b) if x['pass'] and not y['pass']],after_exhausted=sum(x['exhausted'] for x in b),maximum_charged_work=max(x['work'] for x in b),common_legal=[dict(name=x['name'],before_T=x['T'],after_T=y['T'],before_peak=x['peak_memory'],after_peak=y['peak_memory']) for x,y in zip(a,b) if x['pass'] and y['pass']])
paths=['research/batch51/'+x for x in ('solution.cpp','projection.cpp.inc','release-cut.cpp.inc','diagnostic.cpp','test_release_cut.cpp','diagnostic.exe','test_release_cut.exe','release-cut-full-plans.json')]
paths+=['scripts/'+x for x in ('prepare_batch51.py','make_release_cut_gold_batch51.py','build_batch51.py','run_diagnostic_batch51.py')]
paths+=['include/problem.h','include/local_json.h','src/benchmark.cpp','src/simulator.cpp','include/simulator.h','include/solver_metrics.h','data/release-cut-gold-batch51.json','data/release-cut-fixed-gold-batch51.json','data/unresolved-r44-input-only-batch45.json','data/projection-heldout-unresolved-input-only-batch45.json','reports/release-cut-fixed-result-batch51.json','research/batch48/numeric-validation-ubsan.exe','reports/projection-unresolved-diagnostic-batch51.json','reports/projection-heldout-unresolved-diagnostic-batch51.json']
m=dict(status='isolated full remaining-DIRECT ancestor release cut;not default',source_sha=sha('research/batch51/solution.cpp'),change='Cut<=2M first;R48 projection remainder within total16M charged cap;original threshold/seeds/groups unchanged;no49/50',statuses=statuses,sha256={x:sha(x) for x in paths},summary=summary,default48_source_sha=sha('solution/solution.cpp'),timing='Shared functional only;no performance measurements',fixed_plan_driver='Frozen R48 Clang UBSan driver102 complete fixed plans vsPython bigint;not newly compiled R51 numeric driver')
Path('research/batch51/functional-checkpoint.json').write_text(json.dumps(m,indent=2));print(json.dumps(summary,indent=2),flush=True)
