"""Independent restricted permutation enumeration and original-edge liveness.

Small graph subset DP additionally establishes unrestricted serial peak.
No test plan is consumed by submitted code. Large witness orders are produced
by random branch traversal, not by the candidate's recursive peak recurrence.
"""
import hashlib,json,random,subprocess,time
from pathlib import Path

def make(k,seed):
    rng=random.Random(seed);nodes=[];out={};forks=[]
    def node(parents,leaf=False):
        i=len(nodes);nodes.append(dict(id=100001+37*i,core_type=rng.choice(['AIC','AIV']),core_num=rng.randrange(1,9),
            exec_time=rng.randrange(1,10000),workspace_memory=rng.randrange(40,800) if leaf else rng.randrange(0,45),
            output_memory=rng.randrange(0,25) if leaf else rng.randrange(20,350),inputs=[nodes[p]['id'] for p in parents]));out[i]=[]
        for p in parents:out[p].append(i)
        return i
    def tree(count,parent=None):
        if count==0:
            a=node([] if parent is None else [parent],True);return (a,)
        a=node([] if parent is None else [parent]);left=rng.randrange(count)
        x=tree(left,a);y=tree(count-1-left,a)
        j=node([a,x[-1],y[-1]],True);forks.append((a,x,y,j));return (a,x,y,j)
    root=tree(k)
    def traversal(b):
        if len(b)==1:return [b[0]]
        a,x,y,j=b
        if rng.randrange(2):x,y=y,x
        return [a]+traversal(x)+traversal(y)+[j]
    def all_orders(b):
        if len(b)==1:return [[b[0]]]
        a,x,y,j=b;xx=all_orders(x);yy=all_orders(y);return [[a]+f+s+[j] for u in xx for v in yy for f,s in [(u,v),(v,u)]]
    parents=[[next(i for i,n in enumerate(nodes) if n['id']==p) for p in v['inputs']] for v in nodes]
    def peak(order):
        done=set();live=0;highest=0;users=[len(out[i]) for i in range(len(nodes))]
        for i in order:
            assert i not in done and set(parents[i])<=done
            highest=max(highest,live+nodes[i]['workspace_memory']+nodes[i]['output_memory'])
            live+=nodes[i]['output_memory'];done.add(i)
            for p in parents[i]:
                users[p]-=1
                if not users[p]:live-=nodes[p]['output_memory']
        assert len(done)==len(nodes)
        return highest
    best=min((peak(x),x) for x in (all_orders(root) if k<=3 else [traversal(root) for _ in range(96)]))
    serial_best=None
    if k<=3:
        n=len(nodes);pp=[sum(1<<p for p in parents[i]) for i in range(n)];cc=[sum(1<<c for c in out[i]) for i in range(n)]
        dp={0:0}
        for mask in range(1<<n):
            if mask not in dp:continue
            live=sum(nodes[i]['output_memory'] for i in range(n) if mask>>i&1 and (not cc[i] or cc[i]&~mask))
            for i in range(n):
                if mask>>i&1 or pp[i]&~mask:continue
                m=mask|1<<i;p=max(dp[mask],live+nodes[i]['workspace_memory']+nodes[i]['output_memory']);dp[m]=min(dp.get(m,10**20),p)
        serial_best=dp[(1<<n)-1]
    witness={'streams':[{'tasks':[dict(op_id=nodes[i]['id'],wait_before=[],record_after=-1) for i in best[1]]}]}
    rng.shuffle(nodes)
    case=dict(name=f'new_nested_forkjoin_k{k}_seed{seed}',hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=8,memory_limit=best[0],event_record_time=rng.choice([0,3,1000000]),event_wait_time=rng.choice([0,3,1000000])),nodes=nodes,
        deadline_us=sum(n['exec_time'] for n in nodes),witness_plan=witness,expected_feasible=True)
    return case,dict(name=case['name'],restricted_peak=best[0],serial_optimum=serial_best,k=k)

def main():
    cases=[];oracle=[]
    for k in [1,2,3,15,31,63,127,255,511]:
        for repeat in range(4):
            c,r=make(k,2026101200+1000*k+repeat);cases.append(c);oracle.append(r)
    suite=Path('data/nested-forkjoin-new-batch38.json');suite.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases)),encoding='utf-8')
    Path('reports/nested-forkjoin-new-batch38-oracle.json').write_text(json.dumps(dict(input_sha256=hashlib.sha256(suite.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),records=oracle,
        restricted_small='Exhaustive independent permutations of contiguous branch orders',small_oracle='Full subset DP over original-edge output liveness; may interleave branches',large_witness='96 independently randomized DFS traversals; choose minimum independently simulated peak, no candidate recurrence used')),encoding='utf-8')
    print('Created',len(cases),'new structure/seed cases, n4..1534, exact unrestricted small oracle12; large witnesses independent randomized DFS')

if __name__=='__main__':main()
