"""Predeclared160 ORIGINAL DAG fixtures and literal pre-execution charge gold.

No C++ candidate is compiled or run. Physical gold uses bigint original SET
liveness. Fee transcript follows the frozen logical operation contract.
"""
from pathlib import Path
import copy,hashlib,itertools,json
from collections import Counter
P=Path('research/batch55');MAX=2**63-1
def node(i,w,o,ps=()):return dict(id=i,core_type='AIC',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=list(ps))
def basic(equal=False):
    return [node(0,0,50),node(1,0,20,[0]),node(2,40 if equal else 20,20 if equal else 30,[0]),node(3,60 if equal else 50,0,[1]),node(4,0,0,[2])]
def context(nodes):
    by={v['id']:v for v in nodes};out={i:[] for i in by};d={i:len(v['inputs']) for i,v in by.items()}
    for v in nodes:
        for p in v['inputs']:out[p].append(v['id'])
    topo=[i for i in by if not d[i]]
    for i in topo:
        for c in out[i]:
            d[c]-=1
            if d[c]==0:topo.append(c)
    assert len(topo)==len(by);return by,out,topo
def held(by,out,D):return {p:by[p]['output_memory'] for p in D if not out[p] or set(out[p])-D}
def physics(nodes,order,cap,complete=True):
    by,out,_=context(nodes);D=set();peak=0;rows=[];valid=True
    assert len(order)==len(set(order)) and set(order)<=set(by)
    if complete:assert set(order)==set(by)
    for i in order:
        assert set(by[i]['inputs'])<=D
        h=held(by,out,D);L=sum(h.values());begin=L+by[i]['workspace_memory']+by[i]['output_memory'];peak=max(peak,begin)
        D.add(i);after=held(by,out,D)
        rows.append(dict(id=i,held_before=sorted(h),live_before=L,begin=begin,held_after=sorted(after),live_after=sum(after.values())))
        valid&=begin<=cap
    return dict(valid=valid,T=sum(by[i]['exec_time'] for i in order),peak=peak,rows=rows,complete=complete)
class Exhausted(Exception):pass
class Ledger:
    def __init__(self,limit):self.limit=limit;self.work=0;self.events=[]
    def pay(self,label,amount):
        before=self.work;ok=amount<=self.limit-before;self.work=before+amount if ok else self.limit
        self.events.append(dict(operation=label,amount=amount,work_before=before,work_after=self.work,paid=ok))
        if not ok:raise Exhausted()
def repair(nodes,prefix,p,pending,cap,ledger):
    by,out,_=context(nodes);initial_live=sum(held(by,out,set(prefix)).values());cnt=len(pending);n=len(by);pay=ledger.pay
    result=dict(valid=False,exhausted=False,order=[],peak=initial_live,final_live=initial_live)
    try:
        pay('repair_entry_and_shape',1)
        if not cnt or cnt>128:return result
        pay('initialize_C_positions',n);pay('assign_C_positions',cnt);pos={i:j for j,i in enumerate(pending)}
        pay('initialize_U_positions',n);U=[];up={}
        for i in pending:
            pay('visit_C_for_U',1)
            for q in [i]:
                if q not in up:pay('assign_U',1);up[q]=len(U);U.append(q)
            for q in by[i]['inputs']:
                pay('visit_input_build_U',1)
                if q not in up:pay('assign_U',1);up[q]=len(U);U.append(q)
        pay('initialize_compact_adjacency_headers',2*cnt);ins=[];succ=[]
        for i in pending:
            ps=[];cs=[]
            for q in by[i]['inputs']:pay('build_compact_input',1);ps.append(up[q])
            for c in out[i]:
                pay('scan_original_output',1)
                if c in pos:pay('append_internal_successor',1);cs.append(pos[c])
            ins.append(ps);succ.append(cs)
        pay('initialize_state_scalars',6);pay('copy_initial_users_degree',len(U)+cnt)
        initial=dict(users=[len(set(out[i])-set(prefix)) for i in U],degree=[len(set(by[i]['inputs'])-set(prefix)) for i in pending],mask=0,live=initial_live,peak=initial_live,parent=-1,last=-1)
        pay('initial_beam_move',1);beam=[initial];links=[]
        for depth in range(cnt):
            nex=[]
            for state in beam:
                choices=[]
                for j,i in enumerate(pending):
                    pay('visit_candidate',1)
                    if state['mask']&(1<<j) or state['degree'][j]:continue
                    v=by[i]
                    if state['live']+v['workspace_memory']+v['output_memory']>cap:continue
                    freed=0
                    for q in ins[j]:
                        pay('score_parent_edge',1)
                        if state['users'][q]==1:freed+=by[U[q]]['output_memory']
                    score=(v['output_memory']-freed,v['workspace_memory']+v['output_memory'],i);slot=0
                    while slot<len(choices):
                        pay('candidate_comparison',1)
                        if score<choices[slot][0]:break
                        slot+=1
                    if slot<2:
                        size_after_discard=1 if len(choices)==2 else len(choices);shifted=max(0,size_after_discard-slot)
                        pay('candidate_slot_fields',4*(shifted+1))
                        if len(choices)==2:choices.pop()
                        choices.insert(slot,(score,j))
                for _,j in choices:
                    i=pending[j];v=by[i];pay('copy_child_state',len(U)+cnt+6);child=copy.deepcopy(state)
                    pay('apply_scalar_transition',4);child['peak']=max(child['peak'],child['live']+v['workspace_memory']+v['output_memory']);child['live']+=v['output_memory'];child['last']=j;child['mask']|=1<<j
                    for q in ins[j]:
                        pay('apply_direct_parent_edge',1);child['users'][q]-=1
                        if child['users'][q]==0:child['live']-=by[U[q]]['output_memory']
                    for c in succ[j]:pay('apply_internal_successor_edge',1);child['degree'][c]-=1
                    pay('path_link_and_parent_fields',3);links.append((state['parent'],i));child['parent']=len(links)-1
                    identical=-1
                    for k,x in enumerate(nex):
                        pay('exact_mask_comparison',2)
                        if x['mask']==child['mask']:identical=k;break
                    if identical>=0:
                        pay('identical_mask_peak_comparison',1)
                        if child['peak']<nex[identical]['peak']:pay('selected_state_move',1);nex[identical]=child
                    elif len(nex)<2:pay('selected_state_move',1);nex.append(child)
                    else:
                        pay('different_mask_rank_comparison',1)
                        if (child['live'],child['peak'])<(nex[1]['live'],nex[1]['peak']):pay('selected_state_move',1);nex[1]=child
                    if len(nex)==2:
                        pay('selected_rank_comparison',1)
                        if (nex[1]['live'],nex[1]['peak'])<(nex[0]['live'],nex[0]['peak']):pay('selected_state_swap_moves',3);nex[0],nex[1]=nex[1],nex[0]
            if not nex:return result
            pay('layer_move',1);beam=nex
        pay('producer_and_completion_check',2)
        if p not in up or beam[0]['users'][up[p]]:return result
        order=[];link=beam[0]['parent']
        while link>=0:pay('reconstruct_path_node',3);parent,i=links[link];order.append(i);link=parent
        pay('reverse_order_swaps',len(order)//2);order.reverse();pay('result_pending_copy',cnt)
        result.update(valid=True,order=order,peak=beam[0]['peak'],final_live=beam[0]['live'])
    except Exhausted:result['exhausted']=True
    return result
def probe(nodes,prefix,p,cap,limit=2000000):
    by,out,topo=context(nodes);D=set(prefix);users={i:len(set(out[i])-D) for i in by};degree={i:len(set(v['inputs'])-D) for i,v in by.items()};L=sum(held(by,out,D).values());ledger=Ledger(limit);pay=ledger.pay
    r=dict(pending=[],order=[],peak=L,final_live=L,valid=False,exhausted=False,repair_invoked=False)
    try:
        pay('original_probe_entry',1)
        if p not in D or not by[p]['output_memory'] or not out[p] or not users[p]:return r,ledger
        pay('original_copy_arrays',4*len(by));stack=[];C=set()
        for c in out[p]:
            pay('original_producer_user_edge',1)
            if c not in D:stack.append(c)
        while stack:
            i=stack.pop();pay('original_closure_pop',1)
            if i in D or i in C:continue
            C.add(i)
            if len(C)>128:return r,ledger
            for q in by[i]['inputs']:
                pay('original_closure_input_edge',1)
                if q not in D:stack.append(q)
        for i in topo:
            pay('original_pending_topo_visit',1)
            if i in C:r['pending'].append(i)
        while len(r['order'])<len(C):
            chosen=None;best=None
            for i in r['pending']:
                pay('original_greedy_candidate_visit',1)
                if i in D or degree[i] or L+by[i]['workspace_memory']+by[i]['output_memory']>cap:continue
                freed=0
                for q in by[i]['inputs']:
                    pay('original_greedy_score_edge',1)
                    if users[q]==1:freed+=by[q]['output_memory']
                score=(by[i]['output_memory']-freed,by[i]['workspace_memory']+by[i]['output_memory'],i)
                if chosen is None or score<best:chosen=i;best=score
            if chosen is None:
                r['repair_invoked']=True;rep=repair(nodes,prefix,p,r['pending'],cap,ledger)
                pay('repair_result_status_predicates',2)
                if rep['valid']:r.update(rep)
                elif rep['exhausted']:r['exhausted']=True
                return r,ledger
            i=chosen;r['peak']=max(r['peak'],L+by[i]['workspace_memory']+by[i]['output_memory']);L+=by[i]['output_memory'];D.add(i);r['order'].append(i)
            for q in by[i]['inputs']:
                pay('original_apply_input_edge',1);users[q]-=1
                if users[q]==0:L-=by[q]['output_memory']
            for c in out[i]:pay('original_apply_output_edge',1);degree[c]-=1
        if not users[p]:r.update(valid=True,final_live=L)
    except Exhausted:r['exhausted']=True
    return r,ledger
cases=[]
def emit(family,label,nodes,cap,order,prefix=[0],producer=0,scale=1,variant=0,limit=2000000):
    ns=copy.deepcopy(nodes)
    for v in ns:v['workspace_memory']*=scale;v['output_memory']*=scale
    cap=cap*scale
    mappings=[{i:i for i in [v['id'] for v in ns]},{i:1000000019-i*31 for i in [v['id'] for v in ns]},{i:17+i*10007 for i in [v['id'] for v in ns]},{i:2140000000-i*101 for i in [v['id'] for v in ns]}];m=mappings[variant%4]
    for v in ns:v['id']=m[v['id']];v['inputs']=[m[i] for i in v['inputs']]
    if variant%2:ns.reverse()
    pref=[m[i] for i in prefix];p=m[producer];ordr=[m[i] for i in order];by,out,topo=context(ns);D=set(pref)
    pr=physics(ns,pref,cap,False);assert pr['valid']
    C=set();stack=list(set(out[p])-D)
    while stack:
        i=stack.pop()
        if i in D or i in C:continue
        C.add(i);stack.extend(by[i]['inputs'])
    eligible=p in D and by[p]['output_memory']>0 and bool(set(out[p])-D)
    result,fee=probe(ns,pref,p,cap,limit)
    qual=dict(prefix_is_original_ideal=all(set(by[i]['inputs'])<=D for i in D),prefix_physical_valid=pr['valid'],producer_completed=p in D,producer_positive_output=by[p]['output_memory']>0,remaining_original_DIRECT_users=sorted(set(out[p])-D),closure_original_ids=[i for i in topo if i in C],closure_nonempty=bool(C),eligible=bool(eligible),within128=len(C)<=128)
    assert qual['prefix_is_original_ideal']
    expected=dict(**result,work=fee.work)
    if result['valid']:
        cutphysical=physics(ns,pref+result['order'],cap,False);assert cutphysical['valid'];assert cutphysical['rows'][-1]['live_after']==result['final_live'];assert max([sum(held(by,out,D).values())]+[x['begin'] for x in cutphysical['rows'][len(pref):]])==result['peak']
    counts=Counter(e['operation'] for e in fee.events);amounts=Counter()
    for e in fee.events:amounts[e['operation']]+=e['work_after']-e['work_before']
    c=dict(name=f'{family}-{label}-s{scale}-v{variant}',family=family,hardware=dict(aic_core_num=1,aiv_core_num=1,stream_num=1,memory_limit=cap,event_record_time=0,event_wait_time=0),deadline_us=len(ns),nodes=ns,prefix=pref,producer=p,limit=limit,qualifier=qual,expected=expected,supplied_whole_order=ordr,whole_physics=physics(ns,ordr,cap),charge_histogram=[dict(operation=o,count=counts[o],charged=amounts[o]) for o in counts])
    # At wide cap the production greedy is already successful and MUST stay
    # unchanged. A separate direct routine assertion (not production dispatch)
    # exercises SAME completed mask reached by both valid cut orders.
    if family=='C' and label=='samemaskpeak':
        directledger=Ledger(2000000);direct=repair(ns,pref,p,qual['closure_original_ids'],cap,directledger)
        assert direct['valid'];c['direct_repair_check']=dict(expected=dict(**direct,work=directledger.work),pending=qual['closure_original_ids'],limit=2000000,role='unit-only-no-production-trigger-or-quality-claim')
    # Full deterministic per-operation transcripts are frozen for the manual
    # two templates and16 exact boundary requests. Large mask controls use
    # histograms to keep the verifier input small on the shared low-RAM host.
    if family=='F':c['charge_events']=fee.events
    if len(ns)<=7:
        opts=[]
        for o in itertools.permutations(by):
            done=set();okay=True
            for i in o:
                if not set(by[i]['inputs'])<=done:okay=False;break
                done.add(i)
            if okay:opts.append(physics(ns,o,cap)['peak'])
        c['independent_all_topological_order_peaks']=dict(count=len(opts),minimum=min(opts),legal=sum(v<=cap for v in opts))
    cases.append(c);return c
for s in (1,2,3,7):
    for mode,cap in [('obstruction',100),('wide',130),('onebelow',None)]:
        for v in range(4):
            if cap is None:
                ns=basic()
                for n in ns:n['workspace_memory']*=s;n['output_memory']*=s
                c=emit('A',mode,ns,100*s-1,[0,2,1,4,3],variant=v);c['name']=f'A-onebelow-s{s}-v{v}'
            else:emit('A',mode,basic(),cap,[0,2,1,4,3],scale=s,variant=v)
for t in ('external','shared','dependent','sinks'):
    ns=basic();cap=100;order=[0,2,1,4,3];prefix=[0]
    if t=='external':ns.append(node(5,0,0,[1]));ns[3]['inputs']=[1,5];order=[0,2,1,4,5,3]
    elif t=='shared':ns.append(node(5,0,5));ns[1]['inputs'].append(5);ns[2]['inputs'].append(5);cap=105;order=[0,5,2,1,4,3];prefix=[0,5]
    elif t=='dependent':ns[1]['inputs'].append(2)
    else:ns[3]['output_memory']=ns[4]['output_memory']=1
    for s in (1,2,3,7):
        for v in range(2):emit('B',t,ns,cap,order,prefix=prefix,scale=s,variant=v)
for t,cap in [('differentidentity',110),('samemaskpeak',140)]:
    for s in (1,2,3,7):
        for v in range(4):emit('C',t,basic(True),cap,[0,2,1,4,3],scale=s,variant=v)
for size in (127,128,129,130):
    ns=basic()+[node(i,0,0,[0]) for i in range(5,size+3)];assert len(ns)==size+3
    order=[0]+list(range(5,size+3))+[2,1,4,3]
    for v in range(2):
        for pool in ('AIC','AIV'):
            nodes=copy.deepcopy(ns)
            for n in nodes:n['core_type']=pool
            emit('D',f'cap{size}-{pool}',nodes,100,order,variant=v)
for t in range(8):
    for v in range(2):
        ns=basic();cap=MAX;order=[0,2,1,4,3];prefix=[0]
        if t==0:
            s=MAX//100
            for n in ns:n['workspace_memory']*=s;n['output_memory']*=s
            ns[0]['output_memory']+=MAX-100*s
        elif t==1:
            for n in ns:n['workspace_memory']=n['output_memory']=0
            cap=0
        elif t==2:ns=[node(0,0,1),node(1,6*10**18,6*10**18,[0])];order=[0,1]
        elif t==3:ns=[node(0,0,MAX-1),node(1,2,0,[0]),node(2,0,0,[0])];order=[0,2,1]
        elif t==4:
            q=MAX*3//5;ns=[node(0,0,q),node(1,0,0,[0]),node(2,0,q,[1]),node(3,0,0,[2])];order=[0,1,2,3]
        elif t==5:
            q=MAX//2+v;ns=[node(0,0,1),node(1,0,q,[0]),node(2,0,q,[0])];order=[0,1,2]
        elif t==6:
            ns=[node(0,0,1),node(1,0,8,[0]),node(2,0,1+v,[0]),node(3,0,MAX-10),node(4,0,0,[3])];prefix=[3,0];order=[3,0,4,1,2]
        else:ns=[node(0,0,1),node(1,0,0,[0]),node(2,0,MAX//2),node(3,0,MAX-MAX//2+v)];order=[0,1,2,3]
        emit('E',f'numeric{t}',ns,cap,order,prefix=prefix,variant=v)
# Boundary limits are literal pre-execution ledger values; never learned from
# the candidate. Freeze the unlimited hand-template trace separately below.
literal=[]
for eq in (False,True):
    nodes=basic(eq);cap=110 if eq else 100;r,L=probe(nodes,[0],0,cap)
    setup=next(e['work_after'] for e in L.events if e['operation']=='initial_beam_move');child=next(e['work_after'] for e in L.events if e['operation']=='path_link_and_parent_fields');full=L.work
    limits=[0,setup-1,setup,child-1,child,full-1,full,full+1]
    literal.append(dict(template='equal' if eq else 'obstruction',setup=setup,first_valid_child=child,complete_repair=full,limits=limits,result=r,events=L.events))
    for k,lim in enumerate(limits):emit('F',f'{eq}-budget{k}',nodes,cap,[0,2,1,4,3],limit=lim)
assert len(cases)==160
counts={f:sum(c['family']==f for c in cases) for f in 'ABCDEF'};assert counts==dict(A=48,B=32,C=32,D=16,E=16,F=16)
for c in cases:
    assert c['qualifier']['prefix_is_original_ideal'] and c['qualifier']['prefix_physical_valid']
    assert all(0<=n['workspace_memory']<=MAX and 0<=n['output_memory']<=MAX for n in c['nodes'])
    assert c['expected']['work']<=c['limit']
doc=dict(status='PRE_EXECUTION_ORIGINAL_DAG_REFERENCE_GOLD',candidate_executed=False,count=len(cases),families=counts,cases=cases)
(P/'gold160.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
(P/'gold-driver-input.json').write_text(json.dumps(dict(format='original-dag-cut-context-and-independent-fixed-plan',cases=[dict(**{k:c[k] for k in ('name','hardware','deadline_us','nodes','prefix','producer','limit','supplied_whole_order')},direct_repair_check={k:c['direct_repair_check'][k] for k in ('pending','limit')} if 'direct_repair_check' in c else None) for c in cases]),indent=2)+'\n',encoding='utf-8')
(P/'literal-charge-gold.json').write_text(json.dumps(dict(status='PRE_EXECUTION_LITERAL_HAND_TEMPLATE_FEE_TRANSCRIPTS',templates=literal),indent=2)+'\n',encoding='utf-8')
summary=dict(status=doc['status'],count=160,families=counts,eligible=sum(c['qualifier']['eligible'] for c in cases),within128=sum(c['qualifier']['within128'] for c in cases),reference_valid=sum(c['expected']['valid'] for c in cases),reference_exhausted=sum(c['expected']['exhausted'] for c in cases),repair_invoked=sum(c['expected']['repair_invoked'] for c in cases),direct_routine_only_same_mask_assertions=sum('direct_repair_check' in c for c in cases),whole_supplied_legal=sum(c['whole_physics']['valid'] for c in cases),literal_boundaries=[{k:v for k,v in x.items() if k not in ('events','result')} for x in literal],source_sha256=hashlib.sha256((P/'solution.cpp').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(P/'fixture-qualifier-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))
