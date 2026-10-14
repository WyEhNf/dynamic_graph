"""Independent Python arbitrary precision serial lifetime/profile gold."""
import itertools,json,random,hashlib
from pathlib import Path
MAX=2**63-1
def profile(nodes,perm,prefixes,producers,tails,cap):
    byid={v['id']:v for v in nodes};users={v['id']:0 for v in nodes}
    for v in nodes:
        for p in v['inputs']:users[p]+=1
    order=[];done=set();live=peak=area=excess=0;critical=-1
    def execute(i,slot):
        nonlocal live,peak,area,excess,critical
        v=byid[i];assert all(p in done for p in v['inputs'])
        alloc=live+v['workspace_memory']+v['output_memory']
        if alloc>peak:peak=alloc;critical=slot
        area+=alloc;excess+=max(0,alloc-cap);live+=v['output_memory']
        for p in v['inputs']:
            users[p]-=1
            if not users[p]:live-=byid[p]['output_memory']
        assert live>=0
        done.add(i);order.append(i)
    for prefix in prefixes:execute(prefix,-1)
    for slot,c in enumerate(perm):
        fresh=[p for p in byid[c]['inputs'] if p not in done]
        constant=True
        for prefix in prefixes:
            fresh_users=sum(prefix in byid[p]['inputs'] for p in fresh)
            if byid[prefix]['output_memory'] and 0<fresh_users<len(fresh) and users[prefix]<=fresh_users:constant=False
        if constant:fresh.sort(key=lambda p:-byid[p]['workspace_memory'])
        for p in fresh:execute(p,slot)
        execute(c,slot)
    for p in producers:
        if p not in done:execute(p,-1)
    for t in tails:execute(t,-1)
    assert len(order)==len(nodes)
    return dict(order=order,peak=str(peak),area=str(area),excess=str(excess),critical=critical)
def node(i,ps,rng,extreme):
    choices=[0,1,MAX,MAX-1,MAX//2,6000000000000000000] if extreme else range(0,100)
    return dict(id=i,core_type=rng.choice(['AIC','AIV']),core_num=1,exec_time=rng.randrange(1,100),workspace_memory=rng.choice(choices),output_memory=rng.choice(choices),inputs=list(ps))
rows=[];rng=random.Random(20344411)
for seed in range(160):
    p=rng.randrange(2,8);c=rng.randrange(2,7);ids=rng.sample(range(100,2000000000),p+c+3);prefix=ids[0] if seed%2 else None
    prefixes=[] if prefix is None else [prefix]
    if prefix is not None and seed%5==0:prefixes+=rng.sample(range(100,2000000000),2)
    producers=ids[1:p+1];consumers=ids[p+1:p+c+1];tail=[ids[-1]] if seed%3==0 else []
    nodes=[]
    nodes += [node(i,[],rng,seed%4==0) for i in prefixes]
    nodes += [node(i,[] if not prefixes else rng.sample(prefixes,rng.randrange(1,len(prefixes)+1)),rng,seed%4==0) for i in producers]
    nodes += [node(i,rng.sample(producers,rng.randrange(1,p+1)),rng,seed%4==0) for i in consumers]
    nodes += [node(i,consumers,rng,seed%4==0) for i in tail]
    # Recognition requires no consumer-parent mix: unused producers allowed.
    rng.shuffle(nodes);cap=MAX if seed%4==0 else rng.randrange(50,500)
    hw=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=cap,event_record_time=3,event_wait_time=5)
    # Match node-record topological producer order for deferred unused roots.
    out={v['id']:[] for v in nodes};degree={v['id']:len(v['inputs']) for v in nodes}
    for v in nodes:
        for parent in v['inputs']:out[parent].append(v['id'])
    topo=[v['id'] for v in nodes if not degree[v['id']]]
    for parent in topo:
        for child in out[parent]:
            degree[child]-=1
            if not degree[child]:topo.append(child)
    topop=[i for i in topo if i in producers];prefixes=[i for i in topo if i in prefixes]
    probes=list(itertools.permutations(consumers))
    if len(probes)>24:probes=rng.sample(probes,24)
    for perm in probes:
        rows.append(dict(name=f'shallow_gold_s{seed}_p{len(rows)}',hardware=hw,nodes=nodes,permutation=list(perm),gold=profile(nodes,perm,prefixes,topop,tail,cap)))
controls=0
for wa,wb,oa,ob in itertools.product(range(6),repeat=4):
    if wa<wb:continue
    assert max(oa+wa,oa+ob+wb)<=max(ob+wb,ob+oa+wa)
    controls+=1
# Negative control: a prefix releases after only producer b; W descending can
# increase peak when this external live amount changes between the pair.
# initial live100, a:W10/O1, b:W0/O1, prefix only consumed by b.
assert max(100+10+1,100+1+1)>max(100+1,1+10+1)
out=Path('data/shallow-profile-gold-batch44.json');out.write_text(json.dumps(dict(format='aicore-local-profile-gold-v1',cases=rows),indent=2),encoding='utf-8')
Path('reports/shallow-gold-generation-batch44.json').write_text(json.dumps(dict(profile_controls=len(rows),adjacent_exchange_controls=controls,independent_python='unbounded ints BEGIN allocation/last DIRECT consumer END, sinks retained',sha256=hashlib.sha256(out.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print(len(rows),controls)
