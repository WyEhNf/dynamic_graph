"""Fresh topologies; witness generation never feeds the candidate algorithm."""
import ast,hashlib,json,random
from pathlib import Path
tree=ast.parse(Path('scripts/make_shallow_gold_batch44.py').read_text(encoding='utf-8'))
space={};exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='profile'],type_ignores=[]),'independent_profile','exec'),space)
profile=space['profile'];cases=[]
for seed in range(72):
    rng=random.Random(20344700+seed);p=[16,40,100,240][seed%4];c=[8,24,64,160][seed%4];prefix_count=seed%4
    ids=rng.sample(range(100,2000000000),p+c+prefix_count+2);prefixes=ids[:prefix_count];producers=ids[prefix_count:prefix_count+p];consumers=ids[prefix_count+p:prefix_count+p+c];tails=ids[-2:] if seed%6==0 else []
    witness_consumers=list(consumers);rng.shuffle(witness_consumers)
    nodes=[]
    def add(i,parents,w,o):
        nodes.append(dict(id=i,core_type=rng.choice(['AIC','AIV']),core_num=rng.randrange(1,9),exec_time=rng.randrange(1,20000),workspace_memory=w,output_memory=o,inputs=list(parents)))
    for i in prefixes:add(i,[],rng.randrange(0,20),rng.randrange(0,100))
    reverse={i:[] for i in consumers}
    for i in producers:
        start=rng.randrange(c);width=rng.randrange(1,min(c,8)+1)
        use={witness_consumers[(start+d)%c] for d in rng.sample(range(width),rng.randrange(1,width+1))}
        if seed%3==0:use.add(rng.choice(consumers))
        for j in use:reverse[j].append(i)
        add(i,rng.sample(prefixes,rng.randrange(1,prefix_count+1)) if prefixes else [],0 if seed%2 else rng.randrange(0,250),rng.randrange(10,180))
    # Ensure every consumer has an input; add real edges rather than assuming
    # any fake lifetime credit. Producer degree changes are visible to gold.
    for i in consumers:
        if not reverse[i]:reverse[i].append(rng.choice(producers))
        rng.shuffle(reverse[i]);add(i,reverse[i],rng.randrange(50,450),rng.randrange(0,80) if seed%5==0 else 0)
    for i in tails:add(i,consumers,rng.randrange(0,80),rng.randrange(0,50))
    rng.shuffle(nodes);out={v['id']:[] for v in nodes};degree={v['id']:len(v['inputs']) for v in nodes}
    for v in nodes:
        for parent in v['inputs']:out[parent].append(v['id'])
    topo=[v['id'] for v in nodes if not degree[v['id']]]
    for i in topo:
        for child in out[i]:
            degree[child]-=1
            if degree[child]==0:topo.append(child)
    prefixes=[i for i in topo if i in prefixes];producers=[i for i in topo if i in producers];tails=[i for i in topo if i in tails]
    gold=profile(nodes,witness_consumers,prefixes,producers,tails,2**63-1);peak=int(gold['peak']);total=sum(v['exec_time'] for v in nodes)
    capacity=peak+(0 if seed%3==0 else peak//20)
    hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=8,memory_limit=capacity,event_record_time=[0,3,1000000][seed%3],event_wait_time=[0,5,1000000][seed%3])
    plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in gold['order']])])
    cases.append(dict(name=f'shallow_holdout_seed{20344700+seed}',hardware=hardware,nodes=nodes,deadline_us=total,expected_feasible=True,witness_plan=plan,generation=dict(seed=20344700+seed,witness_T=total,witness_peak=peak,inputs='original edges; intervals plus optional nonlocal users; multiple retained prefixes/sinks; shuffled sparse IDs')))
path=Path('data/shallow-heldout-batch44.json');path.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases),indent=2),encoding='utf-8');print(len(cases),hashlib.sha256(path.read_bytes()).hexdigest())
