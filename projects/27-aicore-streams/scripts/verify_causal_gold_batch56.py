"""Future actual gate; consumes frozen independent gold, never produces expected values."""
from pathlib import Path
import hashlib,json,sys
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
freeze=json.loads((P/'compiler-controls-plan-freeze.json').read_text())
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
plan=json.loads((P/'compiler-resource-plan.json').read_text());owned=Path(plan['owned_root'])
gold=json.loads((P/'gold160.json').read_text());expected={c['name']:c for c in gold['cases']}
caller=json.loads((P/'caller-guard-controls16.json').read_text());extra={c['name']:c for c in caller['cases']};results=[]
for compiler in ('gcc','ubsan'):
    path=owned/'outputs'/f'gold-{compiler}.json';data=json.loads(path.read_text())
    assert data['count']==160 and len(data['cases'])==160
    assert len({c['name'] for c in data['cases']})==160
    assert set(expected)=={c['name'] for c in data['cases']}
    for c in data['cases']:
        e=expected[c['name']]
        for k in ('producer','target','complete','exhausted','work'):assert c[k]==e['expected'][k],(compiler,c['name'],k,c[k],e['expected'][k])
        fixed=c['fixed_physics'];physical=e['whole_physics'];assert fixed['valid']==physical['valid'],(compiler,c['name'],'fixed validity')
        if physical['valid']:assert (fixed['T'],fixed['peak'])==(physical['T'],physical['peak'])
        ids=c['whole_order'];original={v['id'] for v in e['nodes']}
        if len(ids)==len(original):
            assert len(set(ids))==len(original) and set(ids)==original
            assert c['whole_physics']['valid'],(compiler,c['name'],'complete candidate must pass physics')
            assert c['whole_physics']['T']<=e['deadline_us']
        # Failure to find a whole order on this helper is retained, not silently
        # replaced by the supplied independent fixed plan or counted as success.
    caller_path=owned/'outputs'/f'caller-{compiler}.json';calls=json.loads(caller_path.read_text())
    assert calls['count']==16 and len(calls['cases'])==16
    assert len({c['name'] for c in calls['cases']})==16 and set(extra)=={c['name'] for c in calls['cases']}
    for c in calls['cases']:
        e=extra[c['name']];f=caller['fixtures'][e['fixture']]
        for k,v in e['expected'].items():
            if k!='T':assert c[k]==v,(compiler,c['name'],k,c[k],v)
        assert c['fixed_physics']==dict(valid=True,T=f['fixed_T'],peak=f['fixed_peak'])
        if e['expected']['valid']:
            assert c['returned_whole_ids']==f['fixed_order']
            assert c['returned_physics']==dict(valid=True,T=f['fixed_T'],peak=f['fixed_peak'])
        else:assert c['returned_whole_ids']==[] and not c['returned_physics']['valid']
    results.append(dict(compiler=compiler,normal_detector_controls=160,direct_caller_guard_controls=16,fixed_whole_physics=160,caller_fixed_physics=16,normal_pairs=sum(c['producer'] is not None for c in data['cases']),normal_expected_exhausted=sum(c['exhausted'] for c in data['cases']),normal_whole_complete=sum(len(c['whole_order'])==len(expected[c['name']]['nodes']) for c in data['cases']),normal_whole_missing=sum(len(c['whole_order'])!=len(expected[c['name']]['nodes']) for c in data['cases']),fixed_legal=sum(c['fixed_physics']['valid'] for c in data['cases']),caller_valid=sum(c['valid'] for c in calls['cases']),caller_exhausted=sum(c['exhausted'] for c in calls['cases']),all_assertions_passed=True,raw_path=str(path),raw_sha256=sha(path),caller_path=str(caller_path),caller_sha256=sha(caller_path)))
doc=dict(status='ACTUAL_COMPILER_GOLD_ASSERTIONS_PASSED',results=results,plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json'),gold_sha256=sha(P/'gold160.json'),caller_gold_sha256=sha(P/'caller-guard-controls16.json'),candidate_source_sha256=sha(P/'solution.cpp'),coverage_limitations=['No runtime per-operation source fee trace; exact aggregate fee/boundary controls only.','No original R52twelve/remaining63/whole250/performance/default execution.','The artificial160 helper whole orders are physically validated but not assumed guaranteed or optimal.'],same12_solver_executed=False,performance_unmeasured=True,default_changed=False)
target=owned/'outputs'/'gold-summary.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc,indent=2))
