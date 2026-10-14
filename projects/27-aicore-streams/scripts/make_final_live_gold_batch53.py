"""176 predeclared original-DAG controls; bigint SET liveness, full physics.

Production computes local live-R+A. Gold final values use H(D union C),
including sinks and original external DIRECT consumers; fee model is separate.
Every case contains all original nodes. Reference orders never enter solver.
"""
from pathlib import Path
import hashlib,itertools,json,random
from collections import Counter
MAX=2**63-1;ROOT=Path('research/batch53')
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()

def context(nodes):
    by={v['id']:v for v in nodes};out={i:[] for i in by};degree={i:len(v['inputs']) for i,v in by.items()}
    for v in nodes:
        for p in v['inputs']:out[p].append(v['id'])
    topo=[i for i in by if not degree[i]]
    for i in topo:
        for c in out[i]:
            degree[c]-=1
            if degree[c]==0:topo.append(c)
    assert len(topo)==len(by)
    return by,out,topo

def live(by,out,done):return sum(by[i]['output_memory'] for i in done if not out[i] or set(out[i])-done)
def replay(nodes,order):
    by,out,_=context(nodes);done=set();peak=0;timeline=[]
    assert len(order)==len(by) and set(order)==set(by)
    for i in order:
        assert set(by[i]['inputs'])<=done
        before=live(by,out,done);begin=before+by[i]['workspace_memory']+by[i]['output_memory'];peak=max(peak,begin)
        done.add(i);timeline.append(dict(id=i,begin=begin,end_live=live(by,out,done)))
    return dict(T=len(order),peak=peak,timeline=timeline)

def closure(by,out,done,p):
    seen=set();stack=list(set(out[p])-done)
    while stack:
        i=stack.pop()
        if i in seen or i in done:continue
        seen.add(i);stack.extend(by[i]['inputs'])
    return seen

def fee_events(nodes,prefix,C):
    """Logical fee ledger only; does not compute F or decide physical validity."""
    by,out,topo=context(nodes);D=set(prefix);pending=[i for i in topo if i in C];ev=[('zero_hits',len(by))];hits=Counter();touched=[]
    for i in pending:
        ev.append(('input_node',1))
        for p in by[i]['inputs']:
            ev.append(('input_edge_and_done',2))
            if p in D:
                ev.append(('first_hit_and_increment',2))
                if not hits[p]:touched.append(p)
                hits[p]+=1
    for p in touched:
        ev.append(('distinct_parent_and_users',2))
        if hits[p]==len(set(out[p])-D):ev.append(('release_read_guard_subtract',3))
    ev.append(('wide_conversion',1))
    for i in pending:
        ev.append(('output_node_and_sink',2));held=not out[i]
        if not held:
            for c in out[i]:
                ev.append(('output_edge_and_two_tests',3))
                if c not in D and c not in C:held=True;break
        if held:ev.append(('held_read_wide_add',2))
    ev.append(('strict_wide_comparison',1));return ev

def probe(nodes,prefix,p,cap,incumbent=None,new=True,limit=2000000):
    by,out,topo=context(nodes);done=set(prefix);initial=live(by,out,done);users={i:len(set(out[i])-done) for i in by};degree={i:len(set(v['inputs'])-done) for i,v in by.items()}
    r=dict(pending=[],order=[],peak=initial,final_live=initial,valid=False,exhausted=False,pruned=False,work=0)
    def charge(n):
        if n>limit-r['work']:r['work']=limit;r['exhausted']=True;return False
        r['work']+=n;return True
    if not charge(1):return r
    if p not in done or not by[p]['output_memory'] or not out[p] or not users[p]:return r
    if not charge(4*len(by)):return r
    stack=[];C=set()
    for c in out[p]:
        if not charge(1):return r
        if c not in done:stack.append(c)
    while stack:
        i=stack.pop()
        if not charge(1):return r
        if i in done or i in C:continue
        C.add(i)
        if len(C)>128:return r
        for q in by[i]['inputs']:
            if not charge(1):return r
            if q not in done:stack.append(q)
    for i in topo:
        if not charge(1):return r
        if i in C:r['pending'].append(i)
    if new:
        if not charge(1):return r
        if incumbent is not None:
            for _,amount in fee_events(nodes,prefix,C):
                if not charge(amount):return r
            F=live(by,out,done|C)
            if F>incumbent:r['pruned']=True;return r
    while len(r['order'])<len(C):
        ready=[]
        for i in r['pending']:
            if not charge(1):return r
            if i in done or degree[i]:continue
            v=by[i];allocation=live(by,out,done)+v['workspace_memory']+v['output_memory']
            if allocation>cap:continue
            freed=0
            for q in v['inputs']:
                if not charge(1):return r
                if users[q]==1:freed+=by[q]['output_memory']
            ready.append(((v['output_memory']-freed,min(MAX,v['workspace_memory']+v['output_memory']),i),i,allocation))
        if not ready:return r
        _,i,allocation=min(ready);r['peak']=max(r['peak'],allocation);done.add(i);r['order'].append(i)
        for q in by[i]['inputs']:
            if not charge(1):return r
            users[q]-=1
        for c in out[i]:
            if not charge(1):return r
            degree[c]-=1
    assert users[p]==0
    r['valid']=True;r['final_live']=live(by,out,done);return r

def all_cut_orders(nodes,prefix,C):
    by,out,_=context(nodes);D=set(prefix);answers=[]
    def go(done,remaining,order,peak):
        if not remaining:answers.append(dict(order=order,peak=peak,final_live=live(by,out,done)));return
        for i in sorted(remaining):
            if set(by[i]['inputs'])<=done:
                begin=live(by,out,done)+by[i]['workspace_memory']+by[i]['output_memory']
                go(done|{i},remaining-{i},order+[i],max(peak,begin))
    go(D,set(C),[],live(by,out,D));return answers

def convert(records):return [dict(id=i,core_type='AIC' if k%2 else 'AIV',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=ps) for k,(i,w,o,ps) in enumerate(records)]
BASE=[(11,0,50,[]),(13,0,40,[]),(17,0,30,[]),(101,0,20,[11]),(103,20,30,[11]),(107,0,0,[13]),(109,0,30,[17])]

def main():
    frozen=json.loads((ROOT/'pre-gold-freeze.json').read_text())
    for f in frozen['files']:assert sha(f['path'])==f['sha256'],f['path']
    spec=json.loads((ROOT/'gold-declaration.json').read_text());cases=[]
    def add(group,name,recs,prefix,producers,cap,budget_stage=None):
        ns=convert(recs);by,out,topo=context(ns);D=set();prefixpeak=0
        for i in prefix:
            assert set(by[i]['inputs'])<=D
            prefixpeak=max(prefixpeak,live(by,out,D)+by[i]['workspace_memory']+by[i]['output_memory']);D.add(i)
        assert prefixpeak<=cap,(name,'invalid prefix')
        requests=[];inc=None;incsource=None;enumeration=[];fixed=[];expectedselected=None
        for p in producers:
            baseline=probe(ns,prefix,p,cap,new=False);C=closure(by,out,D,p) if p in D else set()
            eligible=p in D and by[p]['output_memory']>0 and bool(out[p]) and bool(set(out[p])-D)
            bound=None
            if eligible and len(C)<=128:
                F=live(by,out,D|C);bound=dict(final=str(F),hi=F>>64,lo=F%(2**64),events=fee_events(ns,prefix,C),work=sum(n for _,n in fee_events(ns,prefix,C)))
                if len(ns)<=8:
                    orders=all_cut_orders(ns,prefix,C);assert orders
                    assert all(o['final_live']==F for o in orders)
                    enumeration.append(dict(producer=p,orders=orders))
            candidate=probe(ns,prefix,p,cap,inc,new=True)
            if candidate['pruned']:assert inc is not None and bound and int(bound['final'])>inc and not candidate['valid']
            requests.append(dict(producer=p,incumbent_source=incsource,incumbent_final=None if inc is None else str(inc),baseline_gold=baseline,candidate_gold=candidate,bound_gold=bound))
            # Whole physical plan retains all original nodes, even invalid probes.
            partial=prefix+baseline['order'];order=partial+[i for i in topo if i not in set(partial)];full=replay(ns,order)
            plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])])
            fixed.append(dict(producer=p,fixed_plan=plan,gold_T=str(full['T']),gold_peak=str(full['peak']),gold_valid=full['peak']<=cap,timeline=full['timeline']))
            if baseline['valid']:assert bound and baseline['final_live']==int(bound['final'])
            if candidate['valid'] and (expectedselected is None or (candidate['final_live'],candidate['peak'])<(expectedselected['final_live'],expectedselected['peak'])):
                expectedselected=candidate;inc=candidate['final_live'];incsource=len(requests)-1
        budget=None
        if budget_stage is not None:
            # Source must be an actually legal first cut, not oracle threshold.
            target=requests[1];assert target['incumbent_source']==0 and requests[0]['candidate_gold']['valid']
            ev=target['bound_gold']['events'];ends=[sum(a for _,a in ev[:k+1]) for k in range(len(ev))]
            stage=budget_stage//2%len(ends);limit=ends[stage]-(budget_stage%2)
            budget=dict(request=1,limit=limit,complete=limit>=target['bound_gold']['work'],work=min(limit,target['bound_gold']['work']),stage=ev[stage][0],one_unit_short=bool(budget_stage%2))
        cases.append(dict(name=name,group=group,hardware=dict(aic_core_num=1,aiv_core_num=1,stream_num=1,memory_limit=cap,event_record_time=0,event_wait_time=0),nodes=ns,deadline_us=len(ns),prefix=prefix,requests=requests,selected_gold=expectedselected,enumeration=enumeration,full_plans=fixed,bound_budget=budget))
    add('manual_competing_equal_first','three_legal',BASE,[11,13,17],[11,13,17],200)
    add('manual_competing_equal_first','invalid_cuts_but_whole_feasible',[(i,40 if i in (101,109) else w,o,ps) for i,w,o,ps in BASE],[11,13,17],[11,13,17],150)
    for name,a,b in [('equal_better',50,10),('equal_tie',50,50),('equal_worse',10,50)]:
        add('manual_competing_equal_first',name,[(11,0,40,[]),(13,0,40,[]),(101,a,0,[11]),(103,b,0,[13])],[11,13],[11,13],150)
    shared=[(11,0,40,[]),(13,0,30,[]),(101,0,5,[11,13]),(103,0,5,[11]),(107,0,0,[13])]
    add('manual_competing_equal_first','shared_external',shared,[11,13],[11,13],200)
    add('manual_competing_equal_first','first_large_final',BASE,[11,13,17],[11],200)
    add('manual_competing_equal_first','lower_final_invalid_still_runs',[(i,151 if i==107 else w,o,ps) for i,w,o,ps in BASE],[11,13,17],[11,13],200)
    for k in range(24):
        recs=[(i,w,o,[11,13] if i==103 and k%2 else ps) for i,w,o,ps in shared]+[(211,0,k%7,[])]
        if k%3:recs.append((213,0,k%4,[101])) # cut-internal output has external consumer
        if k%4==0:recs.append((217,0,0,[13]))
        add('external_users_and_sinks',f'external_sink_{k}',recs,[11,13,211],[11,13],300)
    for k in range(16):
        recs=[(11,0,40,[]),(13,0,k%3,[]),(101,k%4,k%5,[11,13]),(103,k%5,0,[11,101]),(107,0,k%2,[103])]
        add('cross_dependencies_and_zero',f'cross_zero_{k}',recs,[11,13],[11,13],100)
    recipes=spec['explicit_boundary_recipes'][:3]
    for k in range(24):
        r=recipes[k%3];recs=[(v['id'],v['W'],v['O'],v['inputs']) for v in r['nodes']]
        prefix=r['prefix'];producers=r.get('candidate_producers',[r.get('producer',11)])
        if k>=18:
            u=MAX//3;recs=[(11,0,u,[]),(101,0,u,[11]),(103,0,u,[101]),(107,0,u,[103]),(109,0,0,[107])];prefix=[11];producers=[11]
        add('integer_limits',f'integer_{k}',recs,prefix,producers,MAX)
    for k in range(8):
        count=128+k%2;recs=[(11,0,1,[])]+[(1001+j,0,0,[11]) for j in range(count)]
        if k>=4:recs.append((13,0,0,[]));prefix=[11,13]
        else:prefix=[11]
        add('closure_128_129',f'complete_closure_{count}_variant{k}',recs,prefix,[11],1+(k//2)%2)
    for seed in spec['fixed_random_seeds']:
        rng=random.Random(seed)
        for k in range(16):
            n=3+k%6;ids=rng.sample(range(1000,1000000000),n);recs=[]
            for j in range(n):
                parents=rng.sample(ids[:j],rng.randrange(min(3,j)+1))
                if j==1:parents=[ids[0]]
                recs.append((ids[j],rng.randrange(8),rng.randrange(1,16) if j==0 else rng.randrange(16),parents))
            ns=convert(recs);full=replay(ns,ids);prefix=ids[:1+k%(n-1)];by,out,_=context(ns)
            producers=[i for i in prefix if by[i]['output_memory'] and set(out[i])-set(prefix)]
            if not producers:producers=[ids[0]] # invalid consumed producer explicitly tested
            producers.sort(key=lambda i:(-by[i]['output_memory'],i));rng.shuffle(recs)
            add('fixed_seed_small_dags',f'random_{seed}_{k}',recs,prefix,producers,full['peak'])
    for k in range(32):add('charged_work_boundaries',f'charge_boundary_{k}',BASE,[11,13,17],[11,13,17],200,budget_stage=k)
    counts=dict(Counter(c['group'] for c in cases));assert counts==spec['planned_control_counts'] and len(cases)==176,(counts,len(cases))
    data=dict(format='aicore-local-final-live-gold-v1',cases=cases)
    fixed=[dict(name=f"{c['name']}_producer{f['producer']}",hardware=c['hardware'],nodes=c['nodes'],deadline_us=c['deadline_us'],**{k:v for k,v in f.items() if k in ('fixed_plan','gold_T','gold_peak','gold_valid')}) for c in cases for f in c['full_plans']]
    for rel,obj in [('data/final-live-gold-batch53.json',data),('data/final-live-fixed-gold-batch53.json',dict(format='aicore-local-fixed-plan-bigint-v1',cases=fixed))]:Path(rel).write_text(json.dumps(obj),encoding='utf-8')
    summary=dict(status='GENERATED_AND_PYTHON_MATH_PHYSICS_CHECKED',controls=len(cases),counts=counts,requests=sum(len(c['requests']) for c in cases),bound_budget_controls=32,enumerated_original_cut_orders=sum(len(e['orders']) for c in cases for e in c['enumeration']),full_plans=len(fixed),legal_full_plans=sum(f['gold_valid'] for f in fixed),expected_invalid_full_plans=sum(not f['gold_valid'] for f in fixed),strictly_dominated=sum(r['candidate_gold']['pruned'] for c in cases for r in c['requests']),reference='Independent bigint H(D union C) SET values and full original BEGIN/END physics; local fee ledger follows pre-gold frozen logical units, not production liveness arithmetic',pre_gold_freeze_sha256=sha(ROOT/'pre-gold-freeze.json'),data_sha256={f:sha(f) for f in ('data/final-live-gold-batch53.json','data/final-live-fixed-gold-batch53.json')})
    Path('reports/final-live-generation-batch53.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
