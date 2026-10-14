"""Core-packing workloads with solver-independent conservative serial witnesses."""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def packing_case(seed,n,capacity,correlation):
    rng=random.Random(seed)
    ids=rng.sample(range(10_000,2_000_000_000),n)
    nodes=[]
    for i in range(n):
        cores=rng.choice([1,capacity//4,capacity//2,capacity])
        base=rng.choice([1,3,7,25,100,1000,10000])
        duration=base if correlation=="independent" else base*capacity//cores if correlation=="long_small" else base*cores
        nodes.append(node(ids[i],rng.choice(["AIC","AIV"]),cores,max(1,duration),rng.randint(0,16),rng.choice([0,1,5])))
    witness,total,peak=serial_witness(nodes)
    # At most eight simultaneous computes: this bound removes memory as a
    # bottleneck without assuming a particular returned stream schedule.
    limit=sum(v["output_memory"] for v in nodes)+8*max(v["workspace_memory"] for v in nodes)
    rng.shuffle(nodes)
    x=case(f"corepacking_{correlation}_n{n}_cap{capacity}_seed{seed}",hardware(capacity,capacity,8,limit,0,0),nodes,total,witness)
    x["generation"]=dict(seed=seed,family="heterogeneous_corepacking",correlation=correlation,witness_T=total,witness_peak=peak,feasibility="independent serial witness; memory bound covers any eight concurrent computes")
    return x


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=20261020)
    p.add_argument("--output",type=Path,default=Path("data/corepacking.json"))
    args=p.parse_args()
    cases=[packing_case(args.seed+n*100+cap*10+j,n,cap,c) for n in [64,256,1024] for cap in [8,32] for j,c in enumerate(["independent","long_small","long_large"])]
    args.output.write_text(json.dumps(dict(format="aicore-local-v1",generator_seed=args.seed,cases=cases),separators=(",",":")))
    print(f"corepacking records={len(cases)} seed={args.seed}")


if __name__=="__main__":
    main()
