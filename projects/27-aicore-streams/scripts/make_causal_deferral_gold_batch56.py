"""Pre-execution ORIGINAL DAG, bigint physical and literal-fee reference.

Never compiles/runs/loads the C++ candidate; no saved failing-case witness.
Only run after the parent releases any exclusive resource window.
"""
from pathlib import Path
from collections import Counter
import copy,json,hashlib
P=Path('research/batch56');MAX=(1<<63)-1
def node(i,w,o,ps=()):return dict(id=i,core_type='AIC',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=list(ps))
def basic():return [node(0,0,30),node(1,0,50),node(2,50,0,[1]),node(3,0,0,[0,2])]
def context(ns):
    by={v['id']:v for v in ns};out={i:[] for i in by};degree={i:len(by[i]['inputs']) for i in by}
    for v in ns:
        for p in v['inputs']:out[p].append(v['id'])
    topo=[i for i in by if not degree[i]]
    for i in topo:
        for c in out[i]:
            degree[c]-=1
            if not degree[c]:topo.append(c)
    assert len(topo)==len(by);return by,out,topo
def held(by,out,D):return {p for p in D if not out[p] or set(out[p])-D}
def physics(ns,order,cap,whole=False):
    by,out,_=context(ns);D=set();peak=0;rows=[];valid=True;elapsed=0
    assert len(order)==len(set(order)) and set(order)<=set(by)
    if whole:assert set(order)==set(by)
    for i in order:
        assert set(by[i]['inputs'])<=D
        H=held(by,out,D);L=sum(by[p]['output_memory'] for p in H);begin=L+by[i]['workspace_memory']+by[i]['output_memory']
        rows.append(dict(phase='BEGIN',id=i,time=elapsed,held=sorted(H),live=L,memory=begin,fits=begin<=cap))
        if begin>cap:valid=False;break
        peak=max(peak,begin);D.add(i);elapsed+=by[i]['exec_time'];H=held(by,out,D)
        rows.append(dict(phase='END',id=i,time=elapsed,held=sorted(H),live=sum(by[p]['output_memory'] for p in H)))
    return dict(valid=valid,complete=valid and (not whole or D==set(by)),T=elapsed if valid else None,peak=peak if valid else None,rows=rows)
class Exhausted(Exception):pass
class Ledger:
    def __init__(self,limit):self.limit=limit;self.work=0;self.events=[]
    def pay(self,op,fee):
        old=self.work;okay=fee<=self.limit-old;self.work=old+fee if okay else self.limit
        self.events.append(dict(operation=op,amount=fee,work_before=old,work_after=self.work,paid=okay))
        if not okay:raise Exhausted()
def pair_reference(ns,prefix,cap,fee):
    by,out,topo=context(ns);D=set(prefix);users={p:len(set(out[p])-D) for p in by}
    hp=sorted((p for p in D if users[p] and by[p]['output_memory']),key=lambda p:(-by[p]['output_memory'],p))[:24]
    best=None;answer=dict(producer=None,target=None,complete=False,exhausted=False);targets=[]
    pay=fee.pay
    try:
        pay('pair_entry_fields',4);pay('eligible_init',len(by));eligible=set()
        for p in hp:pay('eligible_assign',1);eligible.add(p)
        for j in topo:
            pay('target_visit',1)
            if j in D:continue
            pay('reach_and_pin_init',3*len(by));ancestor=set();descendant=set()
            pay('ancestor_seed',4);ancestor.add(j);stack=[j]
            while stack:
                pay('ancestor_pop',1);i=stack.pop()
                for p in by[i]['inputs']:
                    pay('ancestor_edge',1)
                    if p not in ancestor:pay('ancestor_discover',2);ancestor.add(p);stack.append(p)
            pay('descendant_seed',4);descendant.add(j);stack=[j]
            while stack:
                pay('descendant_pop',1);i=stack.pop()
                for c in out[i]:
                    pay('descendant_edge',1)
                    if c not in descendant:pay('descendant_discover',2);descendant.add(c);stack.append(c)
            pay('forced_WO',3);forced=by[j]['workspace_memory']+by[j]['output_memory'];pinned=set();base_producers=[]
            for p in by:
                pay('producer_visit',1)
                if p==j or not by[p]['output_memory']:continue
                retain=not out[p]
                for c in out[p]:
                    pay('original_direct_edge',1)
                    if c in descendant:retain=True;break
                if retain:
                    pay('pin_assign',1);pinned.add(p)
                    if p in ancestor:pay('ancestor_force_add',2);forced+=by[p]['output_memory'];base_producers.append(p)
            base=forced;pay('base_compare',1)
            if forced>cap:
                targets.append(dict(target=j,base=base,base_producers=base_producers,first_cross=None,skip_base_above_cap=True));continue
            crossed=False;first=None
            for step,p in enumerate(prefix):
                pay('prefix_visit',1)
                if p in pinned and p not in ancestor:
                    pay('independent_force_add',2);forced+=by[p]['output_memory'];pay('strict_cross_compare',1)
                    if not crossed and forced>cap:
                        pay('cross_and_eligibility',6);crossed=True
                        qualifies=p in eligible and p in D and by[p]['output_memory']>0 and users[p]>0 and p not in ancestor and p not in descendant
                        first=dict(step=step,producer=p,forced=forced,eligible=qualifies)
                        if qualifies:
                            pay('pair_score_compare',3);score=(step,j,p)
                            if best is None or score<best:
                                pay('best_pair_fields',5);best=score;answer['producer']=p;answer['target']=j
            targets.append(dict(target=j,base=base,base_producers=base_producers,first_cross=first,terminal_forced=forced,skip_base_above_cap=False))
        pay('complete_scan_flag',1);answer['complete']=True
    except Exhausted:
        answer.update(producer=None,target=None,complete=False,exhausted=True)
    answer['work']=fee.work
    return answer,dict(held_top24=hp,targets=targets)
def closure(ns,D,p):
    by,out,_=context(ns);C=set();stack=[i for i in out[p] if i not in D]
    while stack:
        i=stack.pop()
        if i in D or i in C:continue
        C.add(i);stack.extend(by[i]['inputs'])
    return C
def transform(ns,prefix,order,variant):
    ns=copy.deepcopy(ns);ids=[v['id'] for v in ns]
    # Fixed representation metamorphism, never a runtime selector.
    mapping={i:(i if variant==0 else 1700000000-(len(ids)-k)*113 if variant%2 else 100000007+k*997) for k,i in enumerate(ids)}
    for k,v in enumerate(ns):
        v['id']=mapping[v['id']];v['inputs']=[mapping[i] for i in v['inputs']]
        if variant%2:v['inputs'].reverse()
        if variant%3==2:v['core_type']='AIV' if k%2 else 'AIC'
    if variant%2:ns.reverse()
    return ns,[mapping[i] for i in prefix],[mapping[i] for i in order]
cases=[]
def emit(family,label,ns,prefix,order,cap,scale=1,variant=0,limit=2000000):
    ns=copy.deepcopy(ns)
    for v in ns:v['workspace_memory']*=scale;v['output_memory']*=scale
    cap*=scale;ns,prefix,order=transform(ns,prefix,order,variant)
    assert all(0<=v[k]<=MAX for v in ns for k in ('workspace_memory','output_memory')) and 0<=cap<=MAX
    pre=physics(ns,prefix,cap);assert pre['valid']
    fee=Ledger(limit);expected,evidence=pair_reference(ns,prefix,cap,fee);by,out,_=context(ns)
    closure_size=None
    if expected['producer'] is not None:
        p=expected['producer'];j=expected['target'];D=set(prefix)
        assert p in D and j not in D and by[p]['output_memory'] and set(out[p])-D
        closure_size=len(closure(ns,D,p))
    row=dict(name=f'{family}-{label}-s{scale}-v{variant}',family=family,nodes=ns,
             hardware=dict(aic_core_num=1,aiv_core_num=1,stream_num=1,memory_limit=cap,event_record_time=0,event_wait_time=0),
             deadline_us=len(ns),prefix=prefix,limit=limit,supplied_whole_order=order,
             qualifier=dict(original_prefix_ideal=True,prefix_physical_valid=True,complete_pair=expected['producer'] is not None,
                            original_remaining_direct_closure_size=closure_size,cut128_semantics='Preserved cap, not pair qualification or graph feasibility'),
             expected=expected,pair_evidence=evidence,prefix_physics=pre,whole_physics=physics(ns,order,cap,True),
             charge_histogram=dict(Counter(e['operation'] for e in fee.events)))
    if family=='F':row['charge_events']=fee.events
    cases.append(row);return row
# 48: strict, equal, static-base-too-large, and relaxed-but-still-obstructed.
for scale in (1,2,3,7):
    for label,cap in [('strict',100),('equal',130),('base-above',99),('relaxed',101)]:
        for variant in range(3):emit('A',label,basic(),[0,1],[1,2,0,3],cap,scale,variant)
# 32: full external-user retention, shared ancestors, sink exclusion, O0.
for label in ('external','shared','sink','zero'):
    ns=basic();prefix=[0,1];order=[1,2,0,3]
    if label=='external':ns.append(node(4,0,0,[1,2]));order=[1,2,4,0,3]
    elif label=='shared':
        ns.append(node(4,0,5));ns[0]['inputs']=[4];ns[1]['inputs']=[4];ns[2]['inputs']=[1,4];ns[2]['workspace_memory']=45
        prefix=[4,0,1];order=[4,1,2,0,3]
    elif label=='sink':ns[3]['inputs']=[2];order=[1,2,3,0]
    else:ns[0]['output_memory']=0;order=[0,1,2,3]
    for scale in (1,2,3,7):
        for variant in range(2):emit('B',label,ns,prefix,order,100,scale,variant)
# 32: target not-ready and two independent retained identities/crossing choice.
for label in ('not-ready','two-identities'):
    ns=basic();prefix=[0,1];order=[1,2,0,3];cap=100
    if label=='not-ready':ns.append(node(4,0,0,[1]));ns[2]['inputs']=[1,4];order=[1,4,2,0,3]
    else:
        ns.extend([node(4,0,30),node(5,0,0,[4,2])]);prefix=[0,4,1];order=[1,2,0,3,4,5];cap=130
    for scale in (1,2,3,7):
        for variant in range(4):emit('C',label,ns,prefix,order,cap,scale,variant)
# 32: exact integer endpoints, original rank23/24 and cut128/129.
for label in ('MAX','aboveMAX','history','equal','rank23','rank24','cut128','cut129'):
    ns=basic();prefix=[0,1];order=[1,2,0,3];cap=100
    if label=='MAX':ns[0]['output_memory']=MAX//4;ns[1]['output_memory']=MAX//2;ns[2]['workspace_memory']=MAX-MAX//2;cap=MAX
    elif label=='aboveMAX':ns[0]['output_memory']=1;ns[1]['output_memory']=MAX;ns[2]['workspace_memory']=1;prefix=[0];cap=MAX
    elif label=='history':
        ns[0]['output_memory']=MAX//4;ns[1]['output_memory']=MAX//2;ns[2]['workspace_memory']=MAX-MAX//2;cap=MAX
        ns.extend([node(4,0,MAX//2),node(5,0,0,[4]),node(6,0,MAX//2,[5]),node(7,0,0,[6])]);prefix=[4,5,6,7,0,1];order=[4,5,6,7,1,2,0,3]
    elif label=='equal':cap=130
    elif label.startswith('rank'):
        pads=int(label[4:]);ns.extend(node(4+2*k,0,31) for k in range(pads));ns.extend(node(5+2*k,0,0,[4+2*k]) for k in range(pads))
        prefix=list(range(4,4+2*pads,2))+[0,1];order=[x for k in range(pads) for x in (4+2*k,5+2*k)]+[1,2,0,3]
        cap=100+31*pads;ns[2]['workspace_memory']=cap-50
    else:
        count=int(label[3:]);ns.extend(node(i,0,0,[0]) for i in range(4,count+2));assert len(closure(ns,set(prefix),0))==count
        order=[1,2,0]+list(range(4,count+2))+[3]
    for variant in range(4):emit('D',label,ns,prefix,order,cap,variant=variant)
# 16 literal budgets determined from this source-only ledger, not C++ output.
literal=[]
for label in ('basic','not-ready'):
    ns=basic();prefix=[0,1];order=[1,2,0,3]
    if label=='not-ready':ns.append(node(4,0,0,[1]));ns[2]['inputs']=[1,4];order=[1,4,2,0,3]
    fee=Ledger(2000000);expected,evidence=pair_reference(ns,prefix,100,fee)
    first_pair=next(e['work_after'] for e in fee.events if e['operation']=='best_pair_fields')
    complete=fee.work;limits=[0,3,4,first_pair-1,first_pair,complete-1,complete,complete+1]
    literal.append(dict(template=label,first_pair_fields=first_pair,complete_scan=complete,limits=limits,events=fee.events,expected=expected,evidence=evidence))
    for k,limit in enumerate(limits):emit('F',f'{label}-budget{k}',ns,prefix,order,100,limit=limit)
counts=Counter(c['family'] for c in cases);assert len(cases)==160 and counts==dict(A=48,B=32,C=32,D=32,F=16)
(P/'gold160.json').write_text(json.dumps(dict(status='PRE_CANDIDATE_ORIGINAL_DAG_BIGINT_REFERENCE',count=160,families=dict(counts),cases=cases),indent=2)+'\n',encoding='utf-8')
driver=[{k:c[k] for k in ('name','nodes','hardware','deadline_us','prefix','limit','supplied_whole_order')} for c in cases]
(P/'gold-driver-input.json').write_text(json.dumps(dict(cases=driver),indent=2)+'\n',encoding='utf-8')
(P/'literal-charge-gold.json').write_text(json.dumps(dict(status='PRE_CANDIDATE_LITERAL_FEES',templates=literal),indent=2)+'\n',encoding='utf-8')
summary=dict(status='PRE_CANDIDATE_ONLY',count=160,families=dict(counts),qualified_pairs=sum(c['expected']['producer'] is not None for c in cases),
             exhausted=sum(c['expected']['exhausted'] for c in cases),whole_fixed_legal=sum(c['whole_physics']['valid'] for c in cases),
             source_sha256=hashlib.sha256((P/'solution.cpp').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(P/'fixture-qualifier-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))
