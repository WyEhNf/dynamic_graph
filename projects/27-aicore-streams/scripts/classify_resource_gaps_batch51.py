"""Input-only resource/structure audit after two negative isolated moves.

No plan/witness/generation/order is read to construct features or bounds.
Past pass flags only select the fixed58 unresolved inputs; old diagnostics
provide separately labelled heuristic gap evidence, never a feasibility proof.
"""
import collections,hashlib,json,time
from pathlib import Path
MAX=2**63-1
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bits(mask):
    while mask:
        low=mask&-mask;yield low.bit_length()-1;mask^=low

def classify(c,diagnostic):
    nodes=c['nodes'];n=len(nodes);index={v['id']:i for i,v in enumerate(nodes)}
    parents=[[index[x] for x in v['inputs']] for v in nodes];children=[[] for _ in nodes]
    for i,ps in enumerate(parents):
        for p in ps:children[p].append(i)
    degree=list(map(len,parents));topo=[i for i,d in enumerate(degree) if d==0]
    for i in topo:
        for ch in children[i]:
            degree[ch]-=1
            if degree[ch]==0:topo.append(ch)
    assert len(topo)==n and len(index)==n
    ancestors=[0]*n;descendants=[0]*n;childmask=[sum(1<<x for x in cs) for cs in children]
    for i in topo:
        for p in parents[i]:ancestors[i]|=ancestors[p]|(1<<p)
    for i in reversed(topo):
        for ch in children[i]:descendants[i]|=descendants[ch]|(1<<ch)
    cap=c['hardware']['memory_limit'];deadline=c['deadline_us']
    direct_lb=strong_lb=individual=0;strong_at=None;strong_count=0
    for i,v in enumerate(nodes):
        req=v['workspace_memory']+v['output_memory'];individual=max(individual,req)
        direct_lb=max(direct_lb,req+sum(nodes[p]['output_memory'] for p in parents[i]))
        future=descendants[i]|(1<<i)
        held=[p for p in bits(ancestors[i]) if childmask[p]&future]
        bound=req+sum(nodes[p]['output_memory'] for p in held)
        if bound>strong_lb:strong_lb=bound;strong_at=v['id'];strong_count=len(held)
    sink_output=sum(nodes[i]['output_memory'] for i,cs in enumerate(children) if not cs)
    memory_lb=max(strong_lb,sink_output)
    path=[0]*n
    for i in topo:path[i]=nodes[i]['exec_time']+max((path[p] for p in parents[i]),default=0)
    serial=sum(v['exec_time'] for v in nodes)
    corebounds={};heavy={}
    for typ,field in [('AIC','aic_core_num'),('AIV','aiv_core_num')]:
        pool=c['hardware'][field]
        weighted=sum(v['exec_time']*v['core_num'] for v in nodes if v['core_type']==typ)
        corebounds[typ]=(weighted+pool-1)//pool
        heavy[typ]=sum(v['exec_time'] for v in nodes if v['core_type']==typ and v['core_num']>pool//2)
    memory_heavy=sum(v['exec_time'] for v in nodes if 2*(v['workspace_memory']+v['output_memory'])>cap)
    time_lb=max(max(path,default=0),memory_heavy,*corebounds.values(),*heavy.values())
    positive=sorted(v['workspace_memory'] for v in nodes if v['workspace_memory']>0)
    threshold=min(MAX,4*positive[(len(positive)-1)//2]) if positive else 0
    indeg2={i for i in range(n) if len(parents[i])>=2}
    median_pass={i for i in indeg2 if positive and nodes[i]['workspace_memory']>=threshold}
    local_pass={i for i in indeg2 if all(nodes[i]['workspace_memory']>nodes[p]['workspace_memory'] for p in parents[i])}
    targets=median_pass&local_pass
    app=n<=4096 and 2<=len(targets)<=512
    external=collections.Counter();complete=collections.Counter()
    for p,cs in enumerate(children):
        if p in targets or not nodes[p]['output_memory'] or len(cs)<2:continue
        label='2..4' if len(cs)<=4 else ('5..16' if len(cs)<=16 else '>16')
        (complete if set(cs)<=targets else external)[label]+=1
    # Exact target-stop closure size in the search's input-only model.
    closure_size=0;frontier_union=set()
    if app:
        for i in targets:
            seen=set();stack=[i]
            while stack:
                v=stack.pop()
                if v in seen:continue
                seen.add(v)
                for p in parents[v]:
                    if p in targets:frontier_union.add(p)
                    else:stack.append(p)
            closure_size+=len(seen)
    unit=n+len(targets)**2+sum(map(len,parents))+closure_size if app else None
    best=diagnostic['best_peak_hi']*(2**64)+diagnostic['best_peak_lo'] if diagnostic['applicable'] else None
    return dict(name=c['name'],input_sha=hashlib.sha256(json.dumps({k:c[k] for k in ('hardware','nodes','deadline_us')},sort_keys=True,separators=(',',':')).encode()).hexdigest(),n=n,edges=sum(map(len,parents)),max_indegree=max(map(len,parents)),max_outdegree=max(map(len,children)),roots=sum(not ps for ps in parents),sinks=sum(not cs for cs in children),zero_output=sum(v['output_memory']==0 for v in nodes),core_types=dict(collections.Counter(v['core_type'] for v in nodes)),memory_limit=cap,deadline_us=deadline,necessary_memory=dict(individual=individual,direct_parent_overlap=direct_lb,strict_ancestor_future_direct_overlap=strong_lb,strict_overlap_at=strong_at,strict_overlap_producer_count=strong_count,sink_retention=sink_output,lower_bound=memory_lb,slack=cap-memory_lb),necessary_time=dict(critical_path=max(path,default=0),pool_core_work=corebounds,pool_strict_majority=heavy,memory_strict_majority=memory_heavy,lower_bound=time_lb,slack=deadline-time_lb,serial_time=serial,serial_meets_deadline=serial<=deadline),projection=dict(threshold=threshold,indegree_at_least2=len(indeg2),median_pass=len(median_pass),workspace_greater_than_all_parents=len(local_pass),targets=len(targets),applicable=app,inapplicable_reason=None if app else ('n>4096' if n>4096 else ('targets>512' if len(targets)>512 else 'targets<2')),complete_direct_producer_groups=dict(complete),excluded_external_user_producers=dict(external),total_closure_nodes=closure_size,unit=unit,maximum_evaluations_at16M=16000000//unit if unit else 0),heuristic_only=dict(source='isolated R50, actual diagnostic; not optimum or infeasibility proof',best_peak=best,best_gap_above_capacity=best-cap if best is not None else None,evaluations=diagnostic['evaluations'],charged_work=diagnostic['work'],exhausted=diagnostic['exhausted']))

def main():
    start=time.perf_counter();p=Path('research/batch51');p.mkdir(exist_ok=True)
    source='research/batch49/unresolved-r48-input-only.json'
    inputs=json.loads(Path(source).read_text())['cases'];assert len(inputs)==58
    diagnostics=json.loads(Path('reports/projection-unresolved-diagnostic-batch50.json').read_text())['cases'];diag={x['name']:x for x in diagnostics}
    assert all('witness_plan' not in c and 'generation' not in c and not diag[c['name']]['pass'] for c in inputs)
    records=[classify(c,diag[c['name']]) for c in inputs]
    summary=dict(total=len(records),serial_meets_deadline=sum(r['necessary_time']['serial_meets_deadline'] for r in records),parallel_required=sum(not r['necessary_time']['serial_meets_deadline'] for r in records),projection_applicable=sum(r['projection']['applicable'] for r in records),projection_inapplicable_reasons=dict(collections.Counter(r['projection']['inapplicable_reason'] for r in records if not r['projection']['applicable'])),applicable_exhausted=sum(r['projection']['applicable'] and r['heuristic_only']['exhausted'] for r in records),memory_lower_bound_violations=sum(r['necessary_memory']['slack']<0 for r in records),time_lower_bound_violations=sum(r['necessary_time']['slack']<0 for r in records),stronger_than_direct=sum(r['necessary_memory']['strict_ancestor_future_direct_overlap']>r['necessary_memory']['direct_parent_overlap'] for r in records),applicable_with_small_complete_groups=sum(r['projection']['applicable'] and r['projection']['complete_direct_producer_groups'].get('2..4',0)>0 for r in records),with_external_small_group_producers=sum(r['projection']['excluded_external_user_producers'].get('2..4',0)>0 for r in records))
    report=dict(status='input-only original-DAG necessary bounds and classifier coverage; no solving/no performance/no promotion',summary=summary,cases=records,sha256={f:sha(f) for f in (source,'reports/projection-unresolved-diagnostic-batch50.json','research/batch50/solution.cpp',__file__)},explanation='At v BEGIN, strict ancestor output p is unavoidably live if an ORIGINAL DIRECT consumer is v or a descendant of v. Count distinct p once plus Wv+Ov. Sinks hold to globalT. Time lower bounds ignore event overhead, use independent AIC/AIV pools and simultaneous BEGIN W+O strict-half mutual exclusion. Bounds are necessary only; known witnesses are neither read nor reconstructed.',shared_analysis_seconds=time.perf_counter()-start)
    Path('reports/resource-gap-classification-batch51.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
