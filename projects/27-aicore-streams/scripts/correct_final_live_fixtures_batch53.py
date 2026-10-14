"""Preserve attempt1; fix seven declared-prefix prerequisite violations ONLY.

Same original random graphs/hardware/deadlines/seeds; no control deletion,
production source or algorithm change. New paths leave frozen attempt1 intact.
"""
from pathlib import Path
import hashlib,json
from make_final_live_gold_batch53 import context,live,closure,probe,fee_events,all_cut_orders,replay
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
P=Path('research/batch53/corrected');P.mkdir(exist_ok=True)
mapping=json.loads((P/'revision-map.json').read_text());assert mapping['status']=='FROZEN_BEFORE_CORRECTED_GOLD'
assert sha('data/final-live-gold-batch53.json')==mapping['initial_data_sha256']
original=json.loads(Path('data/final-live-gold-batch53.json').read_text());changes=[]
for c in original['cases']:
    if c['group']!='fixed_seed_small_dags':continue
    by,out,topo=context(c['nodes']);D=set(c['prefix'])
    if any(set(out[r['producer']])-D for r in c['requests']):continue
    before=json.loads(json.dumps(c));p=c['requests'][0]['producer']
    assert not by[p]['inputs'] and by[p]['output_memory']>0 and out[p]
    c['prefix']=[p];D={p};assert live(by,out,D)<=c['hardware']['memory_limit']
    cap=c['hardware']['memory_limit'];C=closure(by,out,D,p)
    F=live(by,out,D|C);baseline=probe(c['nodes'],c['prefix'],p,cap,new=False);candidate=probe(c['nodes'],c['prefix'],p,cap,new=True)
    bound=dict(final=str(F),hi=F>>64,lo=F%(2**64),events=fee_events(c['nodes'],c['prefix'],C),work=sum(a for _,a in fee_events(c['nodes'],c['prefix'],C)))
    c['requests']=[dict(producer=p,incumbent_source=None,incumbent_final=None,baseline_gold=baseline,candidate_gold=candidate,bound_gold=bound)]
    orders=all_cut_orders(c['nodes'],c['prefix'],C);assert orders and all(o['final_live']==F for o in orders)
    c['enumeration']=[dict(producer=p,orders=orders)];c['selected_gold']=candidate if candidate['valid'] else None
    partial=c['prefix']+baseline['order'];order=partial+[i for i in topo if i not in set(partial)];full=replay(c['nodes'],order)
    plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])])
    c['full_plans']=[dict(producer=p,fixed_plan=plan,gold_T=str(full['T']),gold_peak=str(full['peak']),gold_valid=full['peak']<=cap,timeline=full['timeline'])]
    assert all(before[k]==c[k] for k in ('name','group','hardware','nodes','deadline_us'))
    planned=next(x for x in mapping['changes'] if x['name']==c['name'])
    canonical=lambda v:hashlib.sha256(json.dumps({k:v[k] for k in ('hardware','nodes','deadline_us','prefix')}|dict(producers=[r['producer'] for r in v['requests']]),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert canonical(before)==planned['before_fixture_input_sha256'] and canonical(c)==planned['after_fixture_input_sha256']
    changes.append(planned)
assert len(changes)==7
for c in original['cases']:
    if c['group']=='fixed_seed_small_dags':
        by,out,_=context(c['nodes']);D=set();
        for i in c['prefix']:assert set(by[i]['inputs'])<=D;D.add(i)
        assert any(r['producer'] in D and by[r['producer']]['output_memory']>0 and set(out[r['producer']])-D and closure(by,out,D,r['producer']) for r in c['requests'])
assert len(original['cases'])==176
(P/'gold.json').write_text(json.dumps(original),encoding='utf-8')
fixed=[dict(name=f"{c['name']}_producer{f['producer']}",hardware=c['hardware'],nodes=c['nodes'],deadline_us=c['deadline_us'],**{k:v for k,v in f.items() if k in ('fixed_plan','gold_T','gold_peak','gold_valid')}) for c in original['cases'] for f in c['full_plans']]
(P/'fixed-gold.json').write_text(json.dumps(dict(format='aicore-local-fixed-plan-bigint-v1',cases=fixed)),encoding='utf-8')
minimal=dict(cases=[{k:c[k] for k in ('name','hardware','nodes','deadline_us','prefix','bound_budget')}|dict(requests=[dict(producer=r['producer']) for r in c['requests']]) for c in original['cases']])
(P/'driver-input.json').write_text(json.dumps(minimal),encoding='utf-8')
meta=dict(status='INITIAL_QUALIFICATION_GATE_FAILED_7_PREFIXES_CORRECTED_NO_TESTS_YET',changes=changes,controls=176,initial_eligible_random_controls=57,corrected_eligible_random_controls=64,initial_frozen_completion_sha256=sha('research/batch53/completion.json'),initial_data_sha256=sha('data/final-live-gold-batch53.json'),candidate_source_sha256=sha('research/batch53/solution.cpp'),source_changed=False,initial_artifacts_preserved_in_place=True,requests=sum(len(c['requests']) for c in original['cases']),enumerated_cut_orders=sum(len(e['orders']) for c in original['cases'] for e in c['enumeration']),full_plans=len(fixed),expected_legal_full_plans=sum(f['gold_valid'] for f in fixed),expected_invalid_full_plans=sum(not f['gold_valid'] for f in fixed),all_new_paths=True)
(P/'qualification-remediation.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta),flush=True)
