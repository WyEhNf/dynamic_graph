"""Analytically optimal controls, separate from heuristic-generated witnesses."""
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, plan, task, serial_witness


def main():
    cases=[]
    for seed in [20261022,20271022]:
        rng=random.Random(seed)
        for n in [1,2,32,512,10000]:
            ids=rng.sample(range(1,2000000000),n)
            nodes=[node(ids[i],"AIC" if rng.randrange(2) else "AIV",rng.randint(1,8),rng.randint(1,1000000000),rng.randint(0,1000),rng.randint(0,1000),ids[i-1:i] if i else []) for i in range(n)]
            witness,T,P=serial_witness(nodes)
            x=case(f"analytic_chain_n{n}_seed{seed}",hardware(8,8,8,P,1000000,1000000),nodes,T,witness)
            # Every task precedes the next. No legal plan can overlap any two
            # Computes; all serial orders are identical and no Event is needed.
            x["generation"]={"analytic_T":T,"analytic_peak":P,"proof":"single total precedence chain", "seed":seed}
            rng.shuffle(x["nodes"]);cases.append(x)
    for kinds,T,P in [(["AIC","AIC"],5,3),(["AIC","AIV"],3,4)]:
        nodes=[node(999,kinds[0],8,2,1,1),node(27,kinds[1],8,3,1,1)]
        witness=plan([task(999),task(27)]) if T==5 else plan([task(999)],[task(27)])
        x=case("analytic_pair_"+"_".join(kinds),hardware(8,8,2,P,0,0),nodes,T,witness)
        x["generation"]={"analytic_T":T,"analytic_peak":P,"proof":"two full-pool tasks; serial minimum peak3 or forced overlap peak4"};cases.append(x)
    Path("data/certificate-controls.json").write_text(json.dumps({"format":"aicore-local-v1","cases":cases}))
    print("12 independent analytic controls generated, including two 10000-node chains")


if __name__=="__main__":main()
