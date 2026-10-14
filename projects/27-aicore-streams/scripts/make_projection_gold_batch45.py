"""Independent full-ancestor Python-bigint reference, not frontier code reuse.

Compare interface permutation normalization and exact original graph live set.
This test is local, neither optimum certificate nor official data.
"""
import collections,hashlib,json,random
from pathlib import Path
MAX=2**63-1
def reference(nodes,capacity,desired):
    index={v['id']:i for i,v in enumerate(nodes)};parents=[[index[x] for x in v['inputs']] for v in nodes]
    children=[[] for _ in nodes]
    for c,ps in enumerate(parents):
        for p in ps:children[p].append(c)
    degree=list(map(len,parents));topo=[i for i,d in enumerate(degree) if not d]
    for i in topo:
        for c in children[i]:
            degree[c]-=1
            if not degree[c]:topo.append(c)
    positive=sorted(v['workspace_memory'] for v in nodes if v['workspace_memory'])
    threshold=min(MAX,4*positive[(len(positive)-1)//2])
    targets=[i for i in topo if len(parents[i])>=2 and nodes[i]['workspace_memory']>=threshold and nodes[i]['workspace_memory']>max(nodes[p]['workspace_memory'] for p in parents[i])]
    if not 2<=len(targets)<=512:return None
    ancestors=[set() for _ in nodes]
    for i in topo:
        for p in parents[i]:ancestors[i]|=ancestors[p]|{p}
    desired=[index[x] for x in desired] if desired else list(reversed(targets))
    rank={i:k for k,i in enumerate(desired)};remaining=set(targets);completed=set();permutation=[];order=[];slots=[]
    while remaining:
        ready=[i for i in remaining if not(ancestors[i]&remaining)]
        c=min(ready,key=lambda i:rank[i]);remaining.remove(c);permutation.append(c)
        for i in topo:
            if i in ancestors[c]|{c} and i not in completed:order.append(i);slots.append(len(permutation)-1);completed.add(i)
    for i in topo:
        if i not in completed:order.append(i);slots.append(-1);completed.add(i)
    # Recompute the live *set* at every BEGIN from a prefix and future users,
    # with sink retention. No mutable user counters or C++ wide arithmetic.
    done=set();peak=area=excess=0;critical=-1
    for i,slot in zip(order,slots):
        live=sum(nodes[p]['output_memory'] for p in done if not children[p] or set(children[p])-done)
        allocated=live+nodes[i]['workspace_memory']+nodes[i]['output_memory']
        if allocated>peak:peak=allocated;critical=slot
        area+=allocated;excess+=max(0,allocated-capacity);done.add(i)
    return dict(targets=[nodes[i]['id'] for i in targets],desired=[nodes[i]['id'] for i in desired],order=[nodes[i]['id'] for i in order],permutation=[nodes[i]['id'] for i in permutation],peak=str(peak),area=str(area),excess=str(excess),critical=critical)
def main():
    rng=random.Random(203445001);cases=[]
    special=[]
    # Explicit retained chain, shared parents, nonzero prefix and two sinks.
    # Target IDs and storage are independently selected from the input.
    for zeros in [False,True]:
        base=[(31,0,7,[]),(13,0,11,[]),(101,2,25,[31,13]),(71,3,30,[31]),(201,100,4,[101,71]),(103,1,19,[201,13]),(107,4,23,[201,31]),(203,140,6,[103,107,71]),(109,2,17,[203]),(205,160,5,[109,101]),(401,0,9,[201,203]),(409,0,8,[205,203])]
        nodes=[dict(id=i,core_type='AIC' if q%2 else 'AIV',core_num=1,exec_time=q+1,workspace_memory=w,output_memory=0 if zeros else o,inputs=ps) for q,(i,w,o,ps) in enumerate(base)]
        special.append(nodes)
    # Individual allocation and cumulative history at MAX, including profiles
    # whose instantaneous total exceeds MAX without arithmetic wrapping.
    base=[(31,0,MAX//9,[]),(13,0,MAX//8,[]),(101,1,MAX//5,[31,13]),(71,2,MAX//6,[31]),(201,MAX//4,MAX//20,[101,71]),(103,1,MAX//7,[201,13]),(107,3,MAX//6,[201]),(203,MAX//3,MAX//21,[103,107,101]),(401,0,1,[201,203]),(409,0,MAX//5,[203])]
    special.append([dict(id=i,core_type='AIC',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=ps) for i,w,o,ps in base])
    for q,nodes in enumerate(special):
        rng.shuffle(nodes);initial=reference(nodes,MAX,[]);assert initial
        for capacity in [0,MAX,100,500]:
            desired=initial['targets'][:];rng.shuffle(desired);expected=reference(nodes,capacity,desired)
            cases.append(dict(name=f'projection_explicit_{q}_{capacity}',hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=capacity,event_record_time=0,event_wait_time=0),nodes=nodes,deadline_us=10000,desired=desired,gold=expected))
    for seed in range(180):
        n=rng.randint(12,50);ids=rng.sample(range(1000,2_000_000_000),n);nodes=[]
        for i in range(n):
            inputs=rng.sample(ids[:i],rng.randint(0,min(i,5)))
            work=rng.randint(80,500) if i%3==2 else rng.randint(0,5)
            nodes.append(dict(id=ids[i],core_type=rng.choice(['AIC','AIV']),core_num=rng.randint(1,8),exec_time=rng.randint(1,20),workspace_memory=work,output_memory=rng.randint(0,100),inputs=inputs))
        rng.shuffle(nodes)
        gold=reference(nodes,500,[])
        if not gold:continue
        scale=MAX//1000 if seed%9==0 else 1
        for v in nodes:v['workspace_memory']*=scale;v['output_memory']*=scale
        # Large history totals and overcapacity profiles are deliberate.
        for trial in range(3):
            desired=gold['targets'][:];rng.shuffle(desired)
            capacity=rng.choice([0,MAX,500*scale])
            expected=reference(nodes,capacity,desired)
            assert expected
            hw=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=capacity,event_record_time=0,event_wait_time=0)
            cases.append(dict(name=f'projection_random_{seed}_{trial}',hardware=hw,nodes=nodes,deadline_us=10000,desired=desired,gold=expected))
    p=Path('data/projection-gold-batch45.json');p.write_text(json.dumps(dict(format='aicore-local-projection-gold-v1',cases=cases)),encoding='utf-8')
    Path('reports/projection-gold-generation-batch45.json').write_text(json.dumps(dict(count=len(cases),seed=203445001,input_sha=hashlib.sha256(p.read_bytes()).hexdigest(),reference='Full original ancestor sets and prefix/future live-set bigint sum, independent from target-stop closures and mutable C++ users',explicit_controls=12,over_int64=sum(int(x['gold']['peak'])>MAX for x in cases)),indent=2))
    print(len(cases),'independent closure/permutation/bigint controls')
if __name__=='__main__':main()
