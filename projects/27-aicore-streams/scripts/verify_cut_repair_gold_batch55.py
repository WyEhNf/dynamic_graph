"""Assert actual compiler outputs against frozen pre-execution160 gold only."""
from pathlib import Path
import hashlib,json,sys
P=Path('research/batch55');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
freeze=json.loads((P/'pre-execution-freeze.json').read_text())
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
gold=json.loads((P/'gold160.json').read_text());expected={c['name']:c for c in gold['cases']};results=[]
for compiler in ('gcc','ubsan'):
    path=Path(f'reports/cut-repair-{compiler}-batch55.json');data=json.loads(path.read_text());assert data['count']==160
    assert len(data['cases'])==160 and len({c['name'] for c in data['cases']})==160
    assert set(expected)=={c['name'] for c in data['cases']}
    for c in data['cases']:
        e=expected[c['name']];r=e['expected']
        for k in ('valid','exhausted','work','peak','final_live','pending','order'):assert c[k]==r[k],(compiler,c['name'],k,c[k],r[k])
        fixed=c['fixed_physics'];physics=e['whole_physics'];assert fixed['valid']==physics['valid'],(compiler,c['name'],'fixed validity')
        if physics['valid']:
            assert fixed['T']==physics['T'] and fixed['peak']==physics['peak'],(compiler,c['name'],'fixed physics')
        actual=c['direct_repair_check'];direct=e.get('direct_repair_check')
        assert (actual is None)==(direct is None)
        if direct:
            for k in ('valid','exhausted','work','peak','final_live','order'):assert actual[k]==direct['expected'][k],(compiler,c['name'],'direct',k)
    results.append(dict(compiler=compiler,actual_controls=160,normal_probe=160,direct_routine=16,fixed_physics=160,normal_valid=sum(c['valid'] for c in data['cases']),normal_expected_exhausted=sum(c['exhausted'] for c in data['cases']),fixed_legal=sum(c['fixed_physics']['valid'] for c in data['cases']),all_assertions_passed=True,raw_path=str(path),raw_sha256=sha(path)))
doc=dict(status='ACTUAL_COMPILER_GOLD_ASSERTIONS_PASSED',results=results,preexecution_freeze_sha256=sha(P/'pre-execution-freeze.json'),gold_sha256=sha(P/'gold160.json'),candidate_source_sha256=sha(P/'solution.cpp'),same12_solver_executed=False,performance_unmeasured=True,default_changed=False)
Path('reports/cut-repair-gold-summary-batch55.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc,indent=2))
