"""Dense fanin/long-distance DAGs with independent serial feasibility witnesses."""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case,hardware,node,serial_witness


def main():
    p=argparse.ArgumentParser();p.add_argument("--seed",type=int,default=20261023);p.add_argument("--output",type=Path,default=Path("data/dense-assignment.json"));args=p.parse_args()
    cases=[]
    for n,width,fanin,streams in [(256,16,8,16),(1024,32,24,64),(4096,64,48,256)]:
        for long_distance in [False,True]:
            rng=random.Random(args.seed+n+int(long_distance));ids=rng.sample(range(1,2000000000),n);nodes=[]
            for i in range(n):
                layer=i//width;stop=layer*width;start=0 if long_distance else max(0,stop-width)
                parents=rng.sample(range(start,stop),min(fanin,stop-start)) if stop else []
                nodes.append(node(ids[i],"AIC" if rng.randrange(2) else "AIV",rng.randint(1,8),rng.randint(1,1000),rng.randint(0,100),rng.randint(0,10),[ids[j] for j in parents]))
            witness,T,P=serial_witness(nodes);memory=sum(x["output_memory"] for x in nodes)+streams*max(x["workspace_memory"] for x in nodes)
            x=case(f"dense_{'global' if long_distance else 'layer'}_n{n}_seed{args.seed}",hardware(128,128,streams,max(memory,P),2,3),nodes,T,witness)
            x["generation"]={"seed":args.seed,"family":"dense non-chain multi-layer / long-distance fanin","witness_T":T,"witness_peak":P,"edges":sum(len(v["inputs"]) for v in nodes),"feasibility":"independent serial witness; wide conservative memory bound"}
            rng.shuffle(nodes);cases.append(x)
    args.output.write_text(json.dumps({"format":"aicore-local-v1","generator_seed":args.seed,"cases":cases},separators=(",",":")))
    print(f"6 dense feasible cases generated,seed{args.seed}")


if __name__=="__main__":main()
