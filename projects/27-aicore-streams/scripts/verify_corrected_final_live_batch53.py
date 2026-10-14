"""Corrected fixture qualification and actual same-source two-compiler gold."""
from pathlib import Path
import json
from make_final_live_gold_batch53 import context
P=Path('research/batch53/corrected');expected={c['name']:c for c in json.loads((P/'gold.json').read_text())['cases']}
assert len(expected)==176
for role in ('gcc','ubsan'):
    actual=json.loads(Path(f'reports/final-live-{role}-corrected-batch53.json').read_text());assert len(actual['cases'])==176
    for c in actual['cases']:
        e=expected[c['name']];assert len(c['requests'])==len(e['requests'])
        if e['group']=='fixed_seed_small_dags':
            by,out,_=context(e['nodes']);D=set(e['prefix']);assert any(by[r['producer']]['output_memory']>0 and set(out[r['producer']])-D for r in e['requests'])
        for a,r in zip(c['requests'],e['requests']):
            g=r['candidate_gold']
            for k in ('valid','exhausted','pruned','work','peak','final_live','pending','order'):assert a[k]==g[k],(role,c['name'],k)
            if a['bound'] is not None:
                b=a['bound'];bg=r['bound_gold'];assert b['hi']==bg['hi'] and b['lo']==bg['lo'] and b['work']==bg['work']
                inc=int(r['incumbent_final']) if r['incumbent_final'] is not None else g['final_live'];assert b['dominated']==(int(bg['final'])>inc)
            if 'budget' in a:assert a['budget']=={k:e['bound_budget'][k] for k in ('complete','work')}
fixed=json.loads(Path('reports/final-live-fixed-ubsan-corrected-batch53.json').read_text());assert fixed['total']==fixed['passed']==347
old_summary=json.loads(Path('reports/final-live-summary-batch53.json').read_text())
summary=dict(status='CORRECTED_SMALL_GATE_COMPLETE',controls=176,qualified_random_controls=64,actual_control_checks=352,probe_requests_per_implementation=347,budget_controls=32,fixed_physical_cases=347,expected_legal_fixed=sum(c['valid'] for c in fixed['cases']),expected_invalid_fixed=sum(not c['valid'] for c in fixed['cases']),first_attempt_qualification_failed=7,first_attempt_all_outputs_preserved=True,candidate_source_changed=False,selected12_reused_original_actual_run=True,selected12_summary={k:old_summary[k] for k in ('old_selected12_success','new_selected12_success','recovered','lost','comparison')},remaining63_or_full_or_performance_run=False,default_changed=False)
Path('reports/final-live-corrected-summary-batch53.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='selected12_summary'}),flush=True)
