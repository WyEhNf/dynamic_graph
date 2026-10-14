"""Large cross-stream Wait with full-core joins; independent serial witnesses."""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def wait_case(seed,branches,width,event):
    rng=random.Random(seed)
    ids=iter(rng.sample(range(10_000,2_000_000_000),branches*(width+1)))
    nodes=[]
    for _ in range(branches):
        parents=[]
        for _ in range(width):
            i=next(ids);parents.append(i)
            nodes.append(node(i,"AIC",rng.choice([16,32]),rng.randint(1000,10000),2,1))
        rng.shuffle(parents)
        nodes.append(node(next(ids),"AIC",128,rng.randint(500,2000),32,1,parents))
    witness,total,peak=serial_witness(nodes)
    memory=sum(v["output_memory"] for v in nodes)+8*max(v["workspace_memory"] for v in nodes)
    rng.shuffle(nodes)
    x=case(f"wait_overlap_b{branches}_w{width}_event{event}_seed{seed}",hardware(128,128,8,memory,event//2,event),nodes,total,witness)
    x["generation"]=dict(seed=seed,family="full_core_join_wait_overlap",branches=branches,width=width,event=event,witness_T=total,witness_peak=peak,feasibility="independent serial witness; generous memory isolates Wait/core overlap")
    return x


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=20261021)
    p.add_argument("--output",type=Path,default=Path("data/wait-overlap.json"))
    args=p.parse_args()
    cases=[wait_case(args.seed+b*1000+w*10+e,b,w,e) for b in [2,4,8] for w in [8,32,128] for e in [100,10000]]
    args.output.write_text(json.dumps(dict(format="aicore-local-v1",generator_seed=args.seed,cases=cases),separators=(",",":")))
    print(f"wait overlap records={len(cases)} seed={args.seed}")


if __name__=="__main__":
    main()
