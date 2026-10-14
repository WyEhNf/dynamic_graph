"""Input-only count of additional5..16 DIRECT target-user groups.

Prepare now; execute once after the coordinated performance window. No
ancestor/order/profile search, compiler, witness or timing benchmark here.
"""
import hashlib,json,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
MAX=2**63-1
def classify(c):
    nodes=c['nodes'];index={v['id']:i for i,v in enumerate(nodes)};assert len(index)==len(nodes)
    parents=[[index[p] for p in v['inputs']] for v in nodes];children=[[] for _ in nodes]
    for i,ps in enumerate(parents):
        assert len(set(ps))==len(ps)
        for p in ps:children[p].append(i)
    positive=sorted(v['workspace_memory'] for v in nodes if v['workspace_memory']);threshold=min(MAX,positive[(len(positive)-1)//2]*4) if positive else 0
    targets={i for i,v in enumerate(nodes) if len(parents[i])>=2 and positive and v['workspace_memory']>=threshold and all(v['workspace_memory']>nodes[p]['workspace_memory'] for p in parents[i])}
    applicable=len(nodes)<=4096 and 2<=len(targets)<=512
    buckets={'2..4':{},'5..16':{}};producers={'2..4':0,'5..16':0};excluded_external=0
    if applicable:
        for p,cs in enumerate(children):
            if p in targets or nodes[p]['output_memory']==0 or not 2<=len(cs)<=16:continue
            if not set(cs)<=targets:excluded_external+=1;continue
            label='2..4' if len(cs)<=4 else '5..16';key=tuple(sorted(cs));buckets[label][key]=min(MAX,buckets[label].get(key,0)+nodes[p]['output_memory']);producers[label]+=1
    return dict(name=c['name'],n=len(nodes),edges=sum(map(len,parents)),roots=sum(not ps for ps in parents),root_output=sum(nodes[i]['output_memory'] for i,ps in enumerate(parents) if not ps),sinks=sum(not cs for cs in children),threshold=threshold,raw_target_count=len(targets),applicable=applicable,inapplicable_reason=None if applicable else ('n>4096' if len(nodes)>4096 else 'targets outside2..512'),groups={label:len(groups) for label,groups in buckets.items()},contributing_producers=producers,excluded_outside_target_direct_users=excluded_external,large_group_sizes=sorted(len(x) for x in buckets['5..16']),large_group_priorities=[str(w) for w in sorted(buckets['5..16'].values(),reverse=True)],input_hw_nodes_deadline_sha=hashlib.sha256(json.dumps({k:c[k] for k in ('hardware','nodes','deadline_us')},sort_keys=True,separators=(',',':')).encode()).hexdigest())
def main():
    start=time.perf_counter();p=Path('research/batch49');p.mkdir(exist_ok=True)
    original=json.loads(Path('data/unresolved-r44-input-only-batch45.json').read_text())['cases'];full=json.loads(Path('reports/hard-functional-batch48.json').read_text())['cases'];failed={r['name'] for r in full if not r['pass']};assert len(failed)==58
    inputs=[c for c in original if c['name'] in failed];assert len(inputs)==58 and {c['name'] for c in inputs}==failed
    assert all('witness_plan' not in c and 'generation' not in c for c in inputs)
    path=p/'unresolved-r48-input-only.json';path.write_text(json.dumps(dict(format='aicore-local-v1',cases=inputs)),encoding='utf-8')
    records=[classify(c) for c in inputs];summary=dict(records=len(records),applicable=sum(r['applicable'] for r in records),with_small_groups=sum(r['groups']['2..4']>0 for r in records),with_large_groups=sum(r['groups']['5..16']>0 for r in records),new_large_only=sum(r['groups']['5..16']>0 and r['groups']['2..4']==0 for r in records),total_large_groups=sum(r['groups']['5..16'] for r in records))
    report=dict(status='input-only counts;not solution/order/feasibility evidence',summary=summary,cases=records,input_sha=sha(path),original_input_sha=sha('data/unresolved-r44-input-only-batch45.json'),selection_result_sha=sha('reports/hard-functional-batch48.json'),algorithm_source_sha=sha('research/batch48/solution.cpp'),script_sha=sha(__file__),selection='Current58 unresolved selected by full R48 output; all group counts derive solely from original full input nodes and DIRECT edges, include all roots/output/core types/hardware/deadline; do not inspect plan or witness',limits='Groups must contain ALL direct users of non-target O>0 producer. Outside consumers invalidate eligibility. Counting candidates is no proof of restoring a plan; unchanged16M and strict original DAG/profile validation needed',shared_analysis_wall_seconds=time.perf_counter()-start)
    Path('reports/large-group-classification-batch49.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
