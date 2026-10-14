"""Irregular non-contiguous sharing with variable stage sizes; solver-free witnesses.

Stages only describe the hidden constructive serial order, not graph constraints.
Each producer has its own consumers and random later consumers; no ID encodes
stage/order, and no graph is filtered according to solver outcomes.
"""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def irregular_case(seed, count, family, retained):
    rng = random.Random(seed)
    ids = iter(rng.sample(range(10_000, 2_000_000_000), count*10+4))
    roots = [next(ids) for _ in range(rng.randint(1, 4))]
    stages = []
    for i in range(count):
        stages.append(([next(ids) for _ in range(rng.randint(1, 3))], [next(ids) for _ in range(rng.randint(1, 2))], [next(ids) for _ in range(rng.randint(1, 3))]))
    extra = {c:[] for _,_,cs in stages for c in cs}
    for i, (producers, _, _) in enumerate(stages):
        horizon = min(count-1-i, 8 if family=="local" else 32 if family=="dense" else count)
        if not horizon:
            continue
        choices = range(i+1, i+1+horizon)
        for producer in producers:
            maximum = min(horizon, 8 if family=="dense" else 3)
            for j in rng.sample(choices, rng.randint(0, maximum)):
                extra[rng.choice(stages[j][2])].append(producer)
    nodes = [node(r,"AIC",1,1,0,0) for r in roots]
    for i, (producers, companions, consumers) in enumerate(stages):
        parents = rng.sample(roots,rng.randint(1,len(roots)))
        # Random backward links connect stage outputs without enforcing a chain.
        if retained and i and rng.random()<0.4:
            parents.append(rng.choice(stages[rng.randrange(i)][2]))
        for p in producers:
            nodes.append(node(p,rng.choice(["AIC","AIC","AIV"]),rng.randint(1,8),rng.randint(1000,100000),rng.randint(0,5),rng.randint(30,180),parents))
        for b in companions:
            nodes.append(node(b,rng.choice(["AIC","AIV"]),rng.randint(1,8),rng.randint(1,30),rng.randint(0,5),rng.randint(40,160),parents))
        for c in consumers:
            inputs = producers+companions+extra[c]
            rng.shuffle(inputs)
            nodes.append(node(c,rng.choice(["AIC","AIV"]),rng.randint(1,8),rng.randint(1,100),rng.randint(150,500),rng.randint(0,5) if retained else 0,inputs))
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    x = case(f"irregular_consumers_{family}_k{count}_ret{retained}_seed{seed}",hardware(streams=8,memory=peak,record=3,wait=3),nodes,duration,witness)
    x["generation"] = dict(seed=seed,family="irregular_noncontiguous_consumers",connection=family,stages=count,retained_outputs=retained,witness_T=duration,witness_peak=peak,feasibility="independent serial stage order; variable stages, random non-contiguous consumers")
    return x


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=20261017)
    p.add_argument("--output",type=Path,default=Path("data/irregular-consumers.json"))
    p.add_argument("--sizes",default="8,24,96,384",help="comma-separated stage counts, preserves original default reproducibility")
    args = p.parse_args()
    sizes=[int(x) for x in args.sizes.split(",")]
    cases = [irregular_case(args.seed+k*100+f*10+r,k,family,r) for k in sizes for f,family in enumerate(["local","dense","global"]) for r in [0,1]]
    args.output.write_text(json.dumps(dict(format="aicore-local-v1",generator_seed=args.seed,cases=cases),separators=(",",":")))
    print(f"irregular consumer records={len(cases)} seed={args.seed}")


if __name__ == "__main__":
    main()
