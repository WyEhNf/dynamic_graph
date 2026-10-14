"""Freeze positive isolated diagnostic, without promotion or timing claims."""
import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch48');hard={x['name']:x for x in json.loads(Path('data/hard-corpus-resumed.json').read_text())['cases']}
inputs=json.loads(Path('data/unresolved-r44-input-only-batch45.json').read_text())['cases'];outputs=json.loads(Path('reports/projection-unresolved-diagnostic-batch48.json').read_text())['cases'];selected=[];plans=[]
for c,r in zip(inputs,outputs):
    assert c['name']==r['name']
    if not r['pass']:continue
    original=hard[c['name']]
    assert all(c[k]==original[k] for k in ('name','hardware','nodes','deadline_us'))
    assert 'witness_plan' not in c and 'generation' not in c
    selected.append(c);plans.append(r)
assert len(selected)==3
q=p/'actual-recoveries-input-only.json';q.write_text(json.dumps(dict(format='aicore-local-v1',cases=selected)),encoding='utf-8')
v=p/'actual-recoveries-plans.json';v.write_text(json.dumps(dict(cases=plans)),encoding='utf-8')
checkpoint=json.loads((p/'functional-checkpoint.json').read_text());paths=['research/batch48/actual-recoveries-input-only.json','research/batch48/actual-recoveries-plans.json','reports/projection-actual-plan-bigint-batch48.json','scripts/review_projection_plans_batch48.py','reports/group-gold-generation-batch48.json','reports/build-functional-batch48.txt']
manifest=dict(status='positive isolated diagnostic;full202+48 pending;default45 unchanged',source_sha=sha(p/'solution.cpp'),source_path='research/batch48/solution.cpp',input_sha=sha(q),actual_plans_sha=sha(v),diagnostic_exe_sha=sha(p/'diagnostic.exe'),functional_checkpoint_sha=sha(p/'functional-checkpoint.json'),functional_checkpoint=checkpoint,evidence={x:sha(x) for x in paths},default45_source_sha=sha('solution/solution.cpp'),recovered_from_default45=['irregular_consumers_local_k24_ret1_seed20273418'],old_two_preserved=True,selection_rule='Only original input producer direct-user sets2..4 all selected workspace targets; original45 threshold/seed count/16Mcap retained, noR46/R47',applicable=35,input_count=61,gold_recognition_cases=83,gold_moved_profiles=210,old_workspace_profiles=495,bigint_actual_serial_plans=3,scope='Three physically valid/direct-lifetime deadline-legal serial diagnostic plans; no generic parallel or performance claim',compile_fix='Initial missing <map> failed compiler log retained; only isolation candidate header corrected before successful builds')
(p/'diagnostic-checkpoint.json').write_text(json.dumps(manifest,indent=2));print(sha(p/'diagnostic-checkpoint.json'),flush=True)
