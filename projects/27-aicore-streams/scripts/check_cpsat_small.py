"""Independent subset optimum versus external serial interval CP-SAT."""
import hashlib
import json
import random
import time
from pathlib import Path
from serial_cpsat_oracle import model,solve

def exact_peak(nodes):
    n=len(nodes);idx={x['id']:i for i,x in enumerate(nodes)}
    pred=[sum(1<<idx[p] for p in x['inputs']) for x in nodes]
    succ=[0]*n
    for i,x in enumerate(nodes):
        for p in x['inputs']:succ[idx[p]]|=1<<i
    full=(1<<n)-1;dp=[10**100]*(full+1);dp[0]=0
    for mask in range(full+1):
        if dp[mask]==10**100:continue
        live=sum(x['output_memory'] for i,x in enumerate(nodes) if mask>>i&1 and (not succ[i] or succ[i]&~mask))
        for i,x in enumerate(nodes):
            if mask>>i&1 or pred[i]&~mask:continue
            nxt=mask|1<<i;dp[nxt]=min(dp[nxt],max(dp[mask],live+x['workspace_memory']+x['output_memory']))
    return dp[full]

def main():
    import ortools
    rows=[];start=time.perf_counter()
    for seed in range(32):
        rng=random.Random(20331011+seed);n=4+seed%5;nodes=[]
        for i in range(n):
            nodes.append(dict(id=50001+23*i,core_type='AIC' if rng.randrange(2) else 'AIV',core_num=1,
                exec_time=1+rng.randrange(1000000000),workspace_memory=rng.randrange(13),output_memory=rng.randrange(17) if seed%5 else 0,
                inputs=[50001+23*p for p in range(i) if rng.randrange(100)<10+seed%75]))
        rng.shuffle(nodes);best=exact_peak(nodes)
        for mem in [max(0,best-1),best,best+5]:
            case=dict(name=f'small_seed{seed}_mem{mem}',nodes=nodes,hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=mem,event_record_time=1000000,event_wait_time=1000000),deadline_us=sum(x['exec_time'] for x in nodes))
            built,_=model(case);assert not built.validate()
            got=solve(case,2,1);expected=mem>=best
            assert (got['status'] in ['OPTIMAL','FEASIBLE'])==expected and got['status']!='UNKNOWN',got
            if expected:assert got['meets_deadline']
            rows.append(dict(seed=seed,n=n,memory_limit=mem,independent_minimum_peak=best,status=got['status'],wall=got['solve_wall_seconds']))
    result=dict(passed=True,checks=len(rows),graphs=32,ortools_version=ortools.__version__,elapsed_wall_seconds=time.perf_counter()-start,
        oracle_source_sha256=hashlib.sha256(Path('scripts/serial_cpsat_oracle.py').read_bytes()).hexdigest(),rows=rows)
    Path('reports/serial-cpsat-small-batch33.json').write_text(json.dumps(result,indent=2))
    print(f"{len(rows)} external CP-SAT/subset optimum checks passed; {result['elapsed_wall_seconds']:.3f}s")

if __name__=='__main__':main()
