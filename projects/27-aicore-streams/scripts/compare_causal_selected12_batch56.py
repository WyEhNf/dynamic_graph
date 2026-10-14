"""Future comparison only; never reruns solver or turns baseline successes into gold."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
freeze=json.loads((P/'selected12-plan-freeze.json').read_text());plan=json.loads((P/'selected12-resource-plan.json').read_text())
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
owned=Path(plan['owned_root']);actual_path=owned/'outputs/selected12.json';actual=json.loads(actual_path.read_text())
inputs=json.loads(Path(plan['input_path']).read_text());by_input={c['name']:c for c in inputs['cases']}
assert actual['count']==12 and len(actual['cases'])==12 and len({c['name'] for c in actual['cases']})==12
assert {c['name'] for c in actual['cases']}==set(by_input)
for c in actual['cases']:
    h,w=c['helper'],c['whole'];n=by_input[c['name']]
    assert 0<=h['work']<=16000000,(c['name'],'sharedwork bound')
    if h['valid']:
        assert h['plan'] is not None and len(h['order_ids'])==len(n['nodes'])
        assert set(h['order_ids'])=={v['id'] for v in n['nodes']} and len(set(h['order_ids']))==len(n['nodes'])
        assert h['T']<=n['deadline_us'] and h['peak']<=n['hardware']['memory_limit']
    else:assert h['plan'] is None
    if w['returned']:
        assert w['valid'] and w['plan'] is not None and not w['error']
        assert w['T']<=n['deadline_us'] and w['peak']<=n['hardware']['memory_limit']
        ids=[t['op_id'] for s in w['plan']['streams'] for t in s['tasks']]
        assert len(ids)==len(n['nodes']) and set(ids)=={v['id'] for v in n['nodes']}
    else:assert not w['valid'] and w['plan'] is None and bool(w['error'])
results=[]
for baseline in plan['baselines']:
    before=json.loads(Path(baseline['path']).read_text());old={c['name']:c for c in before['cases']};assert set(old)==set(by_input)
    rows=[]
    for a in actual['cases']:
        b=old[a['name']];row=dict(name=a['name'])
        for stage in ('helper','whole'):
            x,y=b[stage],a[stage]
            row[stage]=dict(before_valid=x['valid'],after_valid=y['valid'],recovered=not x['valid'] and y['valid'],lost=x['valid'] and not y['valid'],before_T=x['T'],after_T=y['T'],before_peak=x['peak'],after_peak=y['peak'],common_plan_equal=x['plan']==y['plan'] if x['valid'] and y['valid'] else None)
        row['helper'].update(before_work=b['helper']['work'],after_work=a['helper']['work'],work_delta=a['helper']['work']-b['helper']['work'],before_evaluations=b['helper']['evaluations'],after_evaluations=a['helper']['evaluations'],before_exhausted=b['helper']['exhausted'],after_exhausted=a['helper']['exhausted'],common_order_equal=b['helper']['order_ids']==a['helper']['order_ids'] if b['helper']['valid'] and a['helper']['valid'] else None)
        row['whole'].update(before_returned=b['whole']['returned'],after_returned=a['whole']['returned'],before_error=b['whole']['error'],after_error=a['whole']['error'],before_metrics=b['whole']['metrics'],after_metrics=a['whole']['metrics'])
        rows.append(row)
    result=dict(baseline=baseline,rows=rows)
    for stage in ('helper','whole'):
        result[stage]=dict(before_success=sum(c[stage]['valid'] for c in old.values()),after_success=sum(c[stage]['valid'] for c in actual['cases']),recovered=sum(r[stage]['recovered'] for r in rows),lost=sum(r[stage]['lost'] for r in rows),after_failed=sum(not c[stage]['valid'] for c in actual['cases']),common_T_equal=sum(r[stage]['before_valid'] and r[stage]['after_valid'] and r[stage]['before_T']==r[stage]['after_T'] for r in rows),common_peak_equal=sum(r[stage]['before_valid'] and r[stage]['after_valid'] and r[stage]['before_peak']==r[stage]['after_peak'] for r in rows))
    result['helper'].update(before_work=sum(c['helper']['work'] for c in old.values()),after_work=sum(c['helper']['work'] for c in actual['cases']),before_exhausted=sum(c['helper']['exhausted'] for c in old.values()),after_exhausted=sum(c['helper']['exhausted'] for c in actual['cases']))
    results.append(result)
doc=dict(status='ACTUAL_ORIGINAL12_SOURCE_ONLY_COMPARISON_NO_PROMOTION',input_path=plan['input_path'],input_sha256=sha(plan['input_path']),raw_path=str(actual_path),raw_sha256=sha(actual_path),exe_sha256=sha(plan['exe_path']),source_sha256=sha(P/'solution.cpp'),comparisons=results,plan_freeze_sha256=sha(P/'selected12-plan-freeze.json'),all_12_preserved=True,whole_failures_retained=True,helper_failures_retained=True,global_feasibility_not_inferred_from_failure=True,performance_unmeasured=True,default_changed=False,scope=plan['scope'])
target=owned/'outputs/selected12-summary.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in doc.items() if k!='comparisons'},indent=2));print(json.dumps([dict(baseline=x['baseline']['version'],helper=x['helper'],whole=x['whole']) for x in results],indent=2))
