"""Stdlib exhaustive check of slot intervals against exact timed lifetimes."""
import hashlib
import itertools
import json
import random
from pathlib import Path

def main():
    checks=0;graphs=0
    for seed in range(40):
        r=random.Random(20321011+seed);n=4+seed%4
        parents=[{p for p in range(i) if r.randrange(100)<15+seed%60} for i in range(n)]
        output=[r.randrange(7) if seed%5 else 0 for _ in range(n)]
        work=[r.randrange(9) for _ in range(n)];duration=[1+r.randrange(1000000000) for _ in range(n)]
        children=[{c for c in range(n) if i in parents[c]} for i in range(n)]
        for order in itertools.permutations(range(n)):
            pos={i:k for k,i in enumerate(order)}
            if any(pos[p]>=pos[c] for c in range(n) for p in parents[c]):continue
            # Independent interval-based real microsecond liveness.
            start={};end={};clock=0
            for i in order:start[i]=clock;clock+=duration[i];end[i]=clock
            finish={i:max((end[c] for c in children[i]),default=clock) for i in range(n)}
            timed=max(sum(work[i] for i in range(n) if start[i]<=t<end[i])+
                      sum(output[i] for i in range(n) if start[i]<=t<finish[i]) for t in start.values())
            # Slot model uses direct-consumer END, sink lasts until all n slots.
            stop={i:max((pos[c]+1 for c in children[i]),default=n) for i in range(n)}
            slotted=max(sum(work[i] for i in range(n) if pos[i]==k)+
                        sum(output[i] for i in range(n) if pos[i]<=k<stop[i]) for k in range(n))
            assert timed==slotted,(seed,order,timed,slotted)
            checks+=1
        graphs+=1
    result=dict(graphs=graphs,topological_orders=checks,passed=True,
        scope='Exhaustive all topological orders of 40 arbitrary DAGs, n4..7; timed intervals versus serial-position intervals; not large CP-SAT solving',
        seed_base=20321011,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    Path('reports/serial-slot-math-batch33.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
