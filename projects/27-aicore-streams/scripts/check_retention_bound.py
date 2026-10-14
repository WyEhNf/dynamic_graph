"""All-prefix check of the future-retained-output necessary bound, stdlib."""
import hashlib
import itertools
import json
import random
from pathlib import Path

def main():
    checks=orders=0
    for seed in range(40):
        r=random.Random(20321011+seed);n=4+seed%4
        parents=[{p for p in range(i) if r.randrange(100)<15+seed%60} for i in range(n)]
        output=[r.randrange(7) if seed%5 else 0 for _ in range(n)]
        work=[r.randrange(9) for _ in range(n)]
        children=[{c for c in range(n) if i in parents[c]} for i in range(n)]
        ancestors=[]
        for i in range(n):
            a={i}
            for p in parents[i]:a|=ancestors[p]
            ancestors.append(a)
        for order in itertools.permutations(range(n)):
            pos={i:k for k,i in enumerate(order)}
            if any(pos[p]>=pos[c] for c in range(n) for p in parents[c]):continue
            orders+=1
            for prefix in range(n):
                done=set(order[:prefix])
                for i in order[prefix:]:
                    pinned={p for p in done if any(i in ancestors[c] for c in children[p])}
                    sinks={p for p in done if not children[p]}
                    missing=parents[i]-done
                    assert not (pinned&sinks or pinned&missing or sinks&missing)
                    lower=work[i]+output[i]+sum(output[p] for p in pinned|sinks|missing)
                    # Actual future allocation along this unmodified full order.
                    alive={p for p in order[:pos[i]] if not children[p] or any(pos[c]>=pos[i] for c in children[p])}
                    actual=work[i]+output[i]+sum(output[p] for p in alive)
                    assert lower<=actual,(seed,order,prefix,i,lower,actual)
                    assert pinned<=alive and missing<=alive
                    checks+=1
    result=dict(passed=True,graphs=40,topological_orders=orders,future_prefix_node_checks=checks,
        seed_base=20321011,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Necessary bound <= actual future Compute allocation for every prefix and future node of every topological order; zero output/multiple sinks/shared and transitive users included')
    Path('reports/retention-bound-math-batch33.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
