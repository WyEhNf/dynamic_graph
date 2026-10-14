"""Root independent bigint original-DAG physical and charged detector reference."""
import hashlib,json,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def model(nodes,prefix,cap):
    index={v['id']:i for i,v in enumerate(nodes)};n=len(nodes);ins=[[index[p] for p in v['inputs']] for v in nodes];out=[[] for _ in nodes]
    for i,parents in enumerate(ins):
        for p in parents:out[p].append(i)
    degree=[len(x) for x in ins];topo=[i for i in range(n) if not degree[i]]
    for i in topo:
        for c in out[i]:
            degree[c]-=1
            if not degree[c]:topo.append(c)
    assert len(topo)==n;pre=[index[p] for p in prefix];done=set(pre);remaining=[len(set(x)-done) for x in out]
    eligible=set(sorted((p for p in done if remaining[p] and nodes[p]['output_memory']),key=lambda p:(-nodes[p]['output_memory'],nodes[p]['id']))[:24])
    events=[];pay=lambda op,value:events.append((op,value));pay('pair_entry_fields',4);pay('eligible_init',n)
    for p in sorted(eligible,key=lambda p:(-nodes[p]['output_memory'],nodes[p]['id'])):pay('eligible_assign',1)
    best=None
    for j in topo:
        pay('target_visit',1)
        if j in done:continue
        pay('reach_and_pin_init',3*n)
        reach=[]
        for label,edges in [('ancestor',ins),('descendant',out)]:
            found={j};stack=[j];pay(label+'_seed',4)
            while stack:
                i=stack.pop();pay(label+'_pop',1)
                for p in edges[i]:
                    pay(label+'_edge',1)
                    if p not in found:pay(label+'_discover',2);found.add(p);stack.append(p)
            reach.append(found)
        anc,desc=reach;pay('forced_WO',3);bound=nodes[j]['workspace_memory']+nodes[j]['output_memory'];pinned=set()
        for p in range(n):
            pay('producer_visit',1)
            if p==j or not nodes[p]['output_memory']:continue
            retain=not out[p]
            for c in out[p]:
                pay('original_direct_edge',1)
                if c in desc:retain=True;break
            if retain:
                pay('pin_assign',1);pinned.add(p)
                if p in anc:pay('ancestor_force_add',2);bound+=nodes[p]['output_memory']
        pay('base_compare',1)
        if bound>cap:continue
        crossed=False
        for k,p in enumerate(pre):
            pay('prefix_visit',1)
            if p in pinned and p not in anc:
                pay('independent_force_add',2);bound+=nodes[p]['output_memory'];pay('strict_cross_compare',1)
                if not crossed and bound>cap:
                    pay('cross_and_eligibility',6);crossed=True
                    if p in eligible and p not in anc and p not in desc:
                        pay('pair_score_compare',3);score=(k,nodes[j]['id'],nodes[p]['id'])
                        if best is None or score<best:pay('best_pair_fields',5);best=score
    pay('complete_scan_flag',1)
    return events,best,(index,ins,out)
def physics(nodes,order,cap,whole):
    index={v['id']:i for i,v in enumerate(nodes)};out=[set() for _ in nodes]
    for c,v in enumerate(nodes):
        for p in v['inputs']:out[index[p]].add(c)
    seen=set();peak=elapsed=0;records=[]
    for identity in order:
        i=index[identity];assert i not in seen and {index[p] for p in nodes[i]['inputs']}<=seen
        held={p for p in seen if not out[p] or out[p]-seen};live=sum(nodes[p]['output_memory'] for p in held)
        memory=live+nodes[i]['workspace_memory']+nodes[i]['output_memory']
        records.append(dict(phase='BEGIN',id=identity,time=elapsed,held=sorted(nodes[p]['id'] for p in held),live=live,memory=memory,fits=memory<=cap))
        if memory>cap:return dict(valid=False,complete=False,T=None,peak=None,rows=records)
        peak=max(peak,memory);seen.add(i);elapsed+=nodes[i]['exec_time'];held={p for p in seen if not out[p] or out[p]-seen}
        records.append(dict(phase='END',id=identity,time=elapsed,held=sorted(nodes[p]['id'] for p in held),live=sum(nodes[p]['output_memory'] for p in held)))
    if whole:assert len(seen)==len(nodes)
    return dict(valid=True,complete=True,T=elapsed,peak=peak,rows=records)
def main():
    f=read(D/'reference-completion-freeze-revision1.json');assert sha(D/'reference-completion-freeze-revision1.json')=='08e72f01a55acf9ec3838310c891d32686f429d7f6ed799ea25d48be4fab3daa'
    for r in f['files']:
        path=Path(r['path']);path=path if path.is_absolute() else P/path;assert sha(path)==r['sha256'] and path.stat().st_size==r['bytes']
    assert f['actual_exit_code']==0 and f['actual_generator_calls']==1 and f['prior_generator_calls']==0
    gold=read(D/'gold160.json');driver=read(D/'gold-driver-input.json');families=Counter();qualified=exhausted=valid=0
    for c,request in zip(gold['cases'],driver['cases'],strict=True):
        assert request=={k:c[k] for k in ('name','nodes','hardware','deadline_us','prefix','limit','supplied_whole_order')}
        events,best,graph=model(c['nodes'],c['prefix'],c['hardware']['memory_limit']);spent=0;paid=[];halt=False
        for op,fee in events:
            okay=fee<=c['limit']-spent;new=spent+fee if okay else c['limit'];paid.append(dict(operation=op,amount=fee,work_before=spent,work_after=new,paid=okay));spent=new
            if not okay:halt=True;break
        expected=dict(producer=None if halt or best is None else best[2],target=None if halt or best is None else best[1],complete=not halt,exhausted=halt,work=spent)
        assert c['expected']==expected,c['name'];assert c['charge_histogram']==dict(Counter(e['operation'] for e in paid))
        if c['family']=='F':assert c['charge_events']==paid
        assert c['prefix_physics']==physics(c['nodes'],c['prefix'],c['hardware']['memory_limit'],False)
        whole=physics(c['nodes'],c['supplied_whole_order'],c['hardware']['memory_limit'],True);assert c['whole_physics']==whole,c['name']
        families[c['family']]+=1;qualified+=expected['producer'] is not None;exhausted+=halt;valid+=whole['valid']
        if expected['producer'] is not None:
            index,ins,out=graph;done={index[p] for p in c['prefix']};todo=list(out[index[expected['producer']]]);closure=set()
            while todo:
                i=todo.pop()
                if i not in done and i not in closure:closure.add(i);todo.extend(ins[i])
            assert len(closure)==c['qualifier']['original_remaining_direct_closure_size']
    assert dict(families)==dict(A=48,B=32,C=32,D=32,F=16) and (qualified,exhausted,valid)==(96,12,144)
    literal=read(D/'literal-charge-gold.json')['templates'];assert [(r['first_pair_fields'],r['complete_scan']) for r in literal]==[(75,127),(143,205)]
    assert sha(P/'solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
    result=dict(passed=True,reviewed_unix=time.time(),gold_sha256=sha(D/'gold160.json'),reference_freeze_sha256=sha(D/'reference-completion-freeze-revision1.json'),controls=160,qualified_pairs=96,exhausted=12,fixed_whole_legal=144,fixed_whole_expected_invalid=16,root_original_physics_replays=320,
        scope='All160 original-DAG independent index-based FIFO/LIFO charged scans rebuilt, raw budget saturation/cleared partial pair and bigint original direct lifetime BEGIN/END verified. Driver carries no expected pair into candidate. Old hand and environmental preflight errors retained. No candidate execution or recovery claim.',
        authorization='Prepare file-backed GCC/Clang-UBSan isolated160-control build/test run plan, exactsource/driver/ABI/ownedG compiler/output/temp paths and freshresources freeze. No compile/solver before plan review; default/oldTeX unchanged. Validate literalerrors/partial scan, whole real plans, shared2M/16M budget before original12 expansion.')
    (ROOT/'outputs/stage2-root-causal-reference-gold-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
