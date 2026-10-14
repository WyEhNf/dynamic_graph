"""Compare actual C++ results to frozen bigint SET/physical and fee gold."""
import json,hashlib
from pathlib import Path

def main():
    gold=json.loads(Path('data/final-live-gold-batch53.json').read_text());expected={c['name']:c for c in gold['cases']};checks=[]
    for role in ('gcc','ubsan'):
        actual=json.loads(Path(f'reports/final-live-{role}-batch53.json').read_text());assert len(actual['cases'])==176
        for c in actual['cases']:
            e=expected[c['name']];assert len(c['requests'])==len(e['requests'])
            for a,r in zip(c['requests'],e['requests']):
                g=r['candidate_gold'];assert a['producer']==r['producer']
                for k in ('valid','exhausted','pruned','work','peak','final_live','pending','order'):assert a[k]==g[k],(role,c['name'],k,a[k],g[k])
                if a['bound'] is not None:
                    b=a['bound'];bg=r['bound_gold'];assert b['hi']==bg['hi'] and b['lo']==bg['lo'] and b['work']==bg['work'],(role,c['name'],'bound',b,bg)
                    inc=int(r['incumbent_final']) if r['incumbent_final'] is not None else g['final_live']
                    assert b['dominated']==(int(bg['final'])>inc)
                if 'budget' in a:
                    assert a['budget']['complete']==e['bound_budget']['complete'] and a['budget']['work']==e['bound_budget']['work'],(role,c['name'],'budget')
            checks.append(dict(role=role,name=c['name'],pass_all=True))
    numeric=json.loads(Path('reports/final-live-fixed-ubsan-batch53.json').read_text());assert numeric['total']==numeric['passed']==347
    # Whole source-only diagnostics share original R52 input and default baseline.
    old=json.loads(Path('reports/observer-baseline-batch52.json').read_text())['cases']
    new=json.loads(Path('reports/final-live-selected12-batch53.json').read_text())['cases']
    assert len(old)==len(new)==12
    comparison=[]
    for b,a in zip(old,new):
        assert b['name']==a['name'];ow=b['whole'];nw=a['whole']
        comparison.append(dict(name=a['name'],before_success=ow['valid'],after_success=nw['valid'],before_T=ow['T'],after_T=nw['T'],before_peak=ow['peak'],after_peak=nw['peak'],before_helper_work=b['helper']['work'],after_helper_work=a['helper']['work'],before_evaluations=b['helper']['evaluations'],after_evaluations=a['helper']['evaluations'],helper_order_equal=b['helper']['order_ids']==a['helper']['order_ids'],whole_plan_equal=ow['plan']==nw['plan'],before_whole_metrics=ow['metrics'],after_whole_metrics=nw['metrics']))
        assert a['helper']['work']<=16000000
    summary=dict(status='SMALL_FUNCTIONAL_TERMINAL',controls=176,actual_gold_runs=2,actual_gold_control_checks=len(checks),probe_requests=347,budget_controls=32,fixed_physical_cases=numeric['total'],fixed_expected_valid=sum(c['valid'] for c in numeric['cases']),fixed_expected_invalid=sum(not c['valid'] for c in numeric['cases']),old_selected12_success=sum(c['before_success'] for c in comparison),new_selected12_success=sum(c['after_success'] for c in comparison),recovered=sum(not c['before_success'] and c['after_success'] for c in comparison),lost=sum(c['before_success'] and not c['after_success'] for c in comparison),comparison=comparison,scope='176 predeclared gold + same original R52 12; not remaining63/full250/1099/performance/default',cost_claim='Shared functional timings only. No matched performance measurement or speedup claim.',default_changed=False)
    Path('reports/final-live-summary-batch53.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='comparison'}),flush=True)
if __name__=='__main__':main()
