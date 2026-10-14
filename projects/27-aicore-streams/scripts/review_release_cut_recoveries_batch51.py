"""Saved actual complete schedules; original input and independent bigint."""
import hashlib,json
from pathlib import Path
from make_first_pivot_gold_batch50 import replay
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=json.loads(Path('data/unresolved-r44-input-only-batch45.json').read_text())['cases']
before=json.loads(Path('reports/projection-unresolved-diagnostic-batch48.json').read_text())['cases']
after=json.loads(Path('reports/projection-unresolved-diagnostic-batch51.json').read_text())['cases']
assert len(inputs)==len(before)==len(after)==61
cases=[];records=[]
for c,a,b in zip(inputs,before,after):
    assert c['name']==a['name']==b['name']
    if a['pass'] or not b['pass']:continue
    assert 'witness_plan' not in c and 'generation' not in c
    p=b['plan'];assert len(p['streams'])==1
    assert all(not t['wait_before'] and t['record_after']==-1 for t in p['streams'][0]['tasks'])
    order=[t['op_id'] for t in p['streams'][0]['tasks']]
    for v in c['nodes']:
        assert 1<=v['core_num']<=min(128,c['hardware']['aic_core_num' if v['core_type']=='AIC' else 'aiv_core_num'])
    full=replay(c['nodes'],order)
    assert full['peak']<=c['hardware']['memory_limit'] and full['T']<=c['deadline_us']
    assert full['peak']==b['peak_memory'] and full['T']==b['T']
    cases.append(c);records.append(dict(name=c['name'],hardware=c['hardware'],nodes=c['nodes'],deadline_us=c['deadline_us'],actual_plan=p,full_bigint_schedule=full,n=len(c['nodes']),T=full['T'],peak=full['peak'],capacity=c['hardware']['memory_limit'],old_pass=a['pass'],source_sha=sha('research/batch51/solution.cpp'),diagnostic_exe_sha=sha('research/batch51/diagnostic.exe')))
assert len(records)==1
paths={'research/batch51/actual-recoveries-input-only.json':dict(format='aicore-local-v1',cases=cases),'research/batch51/actual-recoveries-plans.json':dict(cases=records)}
for f,x in paths.items():Path(f).write_text(json.dumps(x,indent=2),encoding='utf-8')
report=dict(status='PASS independently replayed one saved actual input-only complete original-DAG serial schedule',cases=[{k:v for k,v in r.items() if k not in ('nodes','actual_plan','full_bigint_schedule')} for r in records],sha256={f:sha(f) for f in list(paths)+['data/unresolved-r44-input-only-batch45.json','reports/projection-unresolved-diagnostic-batch48.json','reports/projection-unresolved-diagnostic-batch51.json','research/batch51/functional-checkpoint.json',__file__]},limits='Serial actual no-events schedule; independent Python bigint prefix/future ORIGINAL DIRECT-user set plus W+O BEGIN and last-consumer END. Not an optimality proof, not a whole202 or cost measurement; default48 unchanged')
Path('reports/release-cut-actual-plan-bigint-batch51.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['cases']),flush=True)
