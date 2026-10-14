"""Independent bigint discrete-event oracle; local fixed-plan semantic controls."""
import json,random
from pathlib import Path
M=(1<<63)-1

def simulate(h,nodes,plan):
    ix={v['id']:i for i,v in enumerate(nodes)};succ=[0]*len(nodes)
    for v in nodes:
        for p in v['inputs']:succ[ix[p]]+=1
    flows=plan['streams'];cur=[[0,0,None] for _ in flows];done=set();events=set();mem=peak=now=T=0;used=[0,0]
    for guard in range(10000):
        changed=True
        while changed:
            changed=False
            for s,(k,phase,due) in enumerate(cur):
                if k>=len(flows[s]['tasks']) or due!=now:continue
                task=flows[s]['tasks'][k];v=nodes[ix[task['op_id']]]
                if phase==1:cur[s][1:]=[2,None]
                elif phase==3:
                    mem-=v['workspace_memory'];used[v['core_type']=='AIV']-=v['core_num'];done.add(v['id']);T=now
                    for p in v['inputs']:
                        succ[ix[p]]-=1
                        if not succ[ix[p]]:mem-=nodes[ix[p]]['output_memory']
                    if task['record_after']>=0:
                        if h['event_record_time']:cur[s][1:]=[4,now+h['event_record_time']]
                        else:events.add(task['record_after']);cur[s]=[k+1,0,None]
                    else:cur[s]=[k+1,0,None]
                else:events.add(task['record_after']);cur[s]=[k+1,0,None]
                changed=True
            if len(done)==len(nodes):return T<=M,T,peak
            for s,(k,phase,due) in enumerate(cur):
                if k>=len(flows[s]['tasks']):continue
                task=flows[s]['tasks'][k];v=nodes[ix[task['op_id']]]
                if cur[s][1]==0 and all(e in events for e in task['wait_before']):
                    cur[s][1:]=[1,now+len(task['wait_before'])*h['event_wait_time']];changed=True
                    if cur[s][2]==now:cur[s][1:]=[2,None]
                if cur[s][1]==2:
                    typ=int(v['core_type']=='AIV');cap=h['aiv_core_num' if typ else 'aic_core_num']
                    if used[typ]+v['core_num']>cap or mem+v['workspace_memory']+v['output_memory']>h['memory_limit']:continue
                    assert all(p in done for p in v['inputs'])
                    used[typ]+=v['core_num'];mem+=v['workspace_memory']+v['output_memory'];peak=max(peak,mem);cur[s][1:]=[3,now+v['exec_time']];changed=True
        timers=[x[2] for x in cur if x[2] is not None and x[2]>now]
        if not timers:return False,T,peak
        now=min(timers)
    raise AssertionError('model failed to terminate')

def main():
    rng=random.Random(202610114200);cases=[]
    values=[0,1,M,M-1,M//2,M//2+1,6*10**18]
    for case in range(320):
        n=rng.randrange(2,8);ids=rng.sample(range(10,1000),n);nodes=[]
        for i in range(n):nodes.append(dict(id=ids[i],core_type=rng.choice(['AIC','AIV']),core_num=rng.randrange(1,5),exec_time=rng.randrange(1,15),workspace_memory=rng.choice(values),output_memory=rng.choice(values),inputs=[ids[j] for j in range(i) if rng.random()<0.3]))
        count=rng.randrange(2,5);owners=[rng.randrange(count) for _ in nodes];flows=[dict(tasks=[]) for _ in range(count)]
        recorders=set();before=[set() for _ in nodes]
        for i,v in enumerate(nodes):
            for p in v['inputs']:
                j=ids.index(p)
                if owners[j]!=owners[i]:recorders.add(j);before[i].add(j)
            if i and rng.random()<0.25:
                j=rng.randrange(i)
                if owners[j]!=owners[i]:recorders.add(j);before[i].add(j)
        labels={i:1000+13*i for i in recorders}
        for i,v in enumerate(nodes):flows[owners[i]]['tasks'].append(dict(op_id=v['id'],wait_before=[labels[j] for j in sorted(before[i])],record_after=labels.get(i,-1)))
        plan=dict(streams=flows);h=dict(aic_core_num=8,aiv_core_num=8,stream_num=count,memory_limit=M,event_record_time=rng.choice([0,1,M,M-1,M//2]),event_wait_time=rng.choice([0,1,M,M//2,M//2+1]))
        valid,T,peak=simulate(h,nodes,plan);rng.shuffle(nodes)
        cases.append(dict(name=f'bigint_parallel_seed202610114200_{case}',hardware=h,nodes=nodes,deadline_us=M,fixed_plan=plan,gold_valid=valid,gold_T=str(T),gold_peak=str(peak)))
    p=Path('data/numeric-parallel-batch42.json');p.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases)),encoding='utf-8');print(len(cases),sum(c['gold_valid'] for c in cases),'independent bigint Event controls/valid')
if __name__=='__main__':main()
