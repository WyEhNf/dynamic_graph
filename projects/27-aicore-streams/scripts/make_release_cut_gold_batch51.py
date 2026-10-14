"""Independent ancestor SET and prefix/future-user bigint physics, full plans."""
import hashlib,json,random
from pathlib import Path
from make_first_pivot_gold_batch50 import replay
MAX=2**63-1

def reference(nodes,prefix,producer,capacity):
    by={v['id']:v for v in nodes};done=set(prefix);children={i:set() for i in by}
    degree={i:len(v['inputs']) for i,v in by.items()};topo=[i for i in by if not degree[i]]
    for v in nodes:
        for p in v['inputs']:children[p].add(v['id'])
    for i in topo:
        # Match row-order Kahn to specify closure output, not execution order.
        for v in nodes:
            if i in v['inputs']:
                degree[v['id']]-=1
                if degree[v['id']]==0:topo.append(v['id'])
    def live(ds):return sum(by[p]['output_memory'] for p in ds if not children[p] or children[p]-ds)
    initial=live(done);result=dict(valid=False,pending=[],order=[],peak=str(initial),final_live=str(initial),initial_live=str(initial))
    if producer not in done or by[producer]['output_memory']==0 or not children[producer] or not children[producer]-done:return result,topo
    closure=set();stack=list(children[producer]-done)
    while stack:
        i=stack.pop()
        if i in done or i in closure:continue
        closure.add(i);stack+=by[i]['inputs']
    if len(closure)>128:return result,topo
    result['pending']=[i for i in topo if i in closure]
    while closure-done:
        ready=[]
        for i in closure-done:
            v=by[i]
            if not set(v['inputs'])<=done:continue
            allocation=live(done)+v['workspace_memory']+v['output_memory']
            if allocation>capacity:continue
            freed=sum(by[p]['output_memory'] for p in v['inputs'] if children[p]-done=={i})
            ready.append(((v['output_memory']-freed,v['workspace_memory']+v['output_memory'],i),i,allocation))
        if not ready:return result,topo
        _,i,allocation=min(ready);result['peak']=str(max(int(result['peak']),allocation));done.add(i);result['order'].append(i)
    assert not children[producer]-done
    result['valid']=True;result['final_live']=str(live(done));return result,topo

def nodes(records):return [dict(id=i,core_type='AIC' if q%2 else 'AIV',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=ps) for q,(i,w,o,ps) in enumerate(records)]

def main():
    rng=random.Random(203451001);cases=[];fixed=[];physics=[]
    examples=[('external-user-wide',[(11,1,60,[]),(13,20,60,[]),(101,1,0,[11]),(103,20,0,[11,13])],[11],11,140),
      ('wrong-partial-cut-narrow',[(11,1,60,[]),(13,20,60,[]),(101,1,0,[11]),(103,20,0,[11,13])],[11],11,100),
      ('mutually-dependent-users',[(11,1,40,[]),(13,2,10,[]),(101,3,20,[11]),(103,4,1,[11,101,13]),(107,2,2,[103])],[11],11,80),
      ('overlap-and-outside-output',[(11,1,40,[]),(13,1,30,[]),(101,3,20,[11,13]),(103,4,1,[11,13]),(107,2,2,[101,103])],[11,13],11,100),
      ('sink-never-release',[(11,1,40,[]),(13,1,30,[]),(101,3,2,[13])],[11],11,100),
      ('incomplete-producer',[(11,1,40,[]),(101,3,20,[11]),(103,4,1,[11,101])],[],11,100),
      ('already-fully-consumed',[(11,1,40,[]),(101,3,20,[11]),(103,4,1,[101])],[11,101],11,100),
      ('exact-MAX',[(11,0,MAX-100,[]),(101,100,0,[11]),(103,99,0,[11])],[11],11,MAX),
      ('above-MAX-cannot-fit',[(11,0,6*10**18,[]),(101,6*10**18,0,[11]),(103,1,0,[11])],[11],11,MAX),
      ('zero-output-no-credit',[(11,1,0,[]),(101,3,20,[11]),(103,4,1,[11,101])],[11],11,100)]
    for count in (128,129):examples.append((f'pending-boundary-{count}',[(11,0,1,[])]+[(1001+i,1,0,[11]) for i in range(count)],[11],11,4))
    for name,recs,prefix,p,cap in examples:cases.append(dict(name=name,nodes=nodes(recs),prefix=prefix,producer=p,capacity=cap))
    for trial in range(90):
        n=rng.randrange(8,25);ids=rng.sample(range(1000,2_000_000_000),n);vs=[]
        for i in range(n):vs.append((ids[i],rng.randrange(0,20),rng.randrange(0,30),rng.sample(ids[:i],rng.randrange(min(4,i)+1))))
        prefix=ids[:rng.randrange(1,n)];ns=nodes(vs);p=rng.choice(prefix);rng.shuffle(ns)
        cases.append(dict(name=f'cut_random_{trial}',nodes=ns,prefix=prefix,producer=p,capacity=sum(v['output_memory']+v['workspace_memory'] for v in ns)))
    for c in cases:
        hw=dict(aic_core_num=128,aiv_core_num=128,stream_num=2,memory_limit=c.pop('capacity'),event_record_time=0,event_wait_time=0)
        c['hardware']=hw;c['deadline_us']=len(c['nodes']);c['gold'],topo=reference(c['nodes'],c['prefix'],c['producer'],hw['memory_limit'])
        taken=c['prefix']+c['gold']['order'];order=taken+[i for i in topo if i not in set(taken)]
        full=replay(c['nodes'],order);plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])])
        fixed.append(dict(name=c['name'],hardware=hw,nodes=c['nodes'],deadline_us=c['deadline_us'],fixed_plan=plan,gold_valid=full['peak']<=hw['memory_limit'],gold_T=str(full['T']),gold_peak=str(full['peak'])))
        physics.append(dict(name=c['name'],plan=plan,original_input=dict(hardware=hw,nodes=c['nodes'],deadline_us=c['deadline_us']),full_schedule=full))
    files={'data/release-cut-gold-batch51.json':dict(format='aicore-local-release-cut-gold-v1',cases=cases),'data/release-cut-fixed-gold-batch51.json':dict(format='aicore-local-fixed-plan-bigint-v1',cases=fixed),'research/batch51/release-cut-full-plans.json':dict(cases=physics)}
    for f,x in files.items():Path(f).write_text(json.dumps(x),encoding='utf-8')
    summary=dict(seed=203451001,cases=len(cases),valid_cuts=sum(c['gold']['valid'] for c in cases),complete_plan_cases=len(fixed),physically_feasible_complete_plans=sum(c['gold_valid'] for c in fixed),reference='Independent ancestor SET closure, direct-user prefix/future set liveness; every original node once in complete fixed plan; sinks retained; wrong partialcut narrow is physically invalid, complete original ancestor cut at140 is valid',sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files})
    Path('reports/release-cut-generation-batch51.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
