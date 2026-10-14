"""Planted serial witnesses with overlapping DIRECT consumer windows.

Shared zero-output relays connect the DAG; a producer's real output lasts for
several nearby consumers. Shuffled inputs and IDs prevent using storage order.
No solver calls or outcome filtering occurs in this generator.
"""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def overlap_case(seed, count, fanout, relays, weighted=False):
    rng = random.Random(seed)
    ids = rng.sample(range(10000, 2_000_000_000), 3*count+relays)
    nodes = [node(ids[r], "AIC", 1, 1, 0, 0) for r in range(relays)]
    a_ids = ids[relays::3]
    for i in range(count):
        a, b, c = ids[relays+3*i:relays+3*i+3]
        roots = rng.sample(ids[:relays], rng.randint(1, relays))
        parents = [b] + a_ids[max(0, i-fanout):i+1]
        rng.shuffle(parents)
        outputs = (rng.randint(60, 140), rng.randint(60, 140), rng.randint(0, 3)) if weighted else (100, 100, 1)
        work = rng.randint(150, 300) if weighted else 220
        nodes += [node(a, "AIC", 1, rng.randint(10000, 100000), 1, outputs[0], roots), node(b, "AIV", 1, rng.randint(1, 30) if weighted else 1, 1, outputs[1], roots), node(c, "AIC", 1, rng.randint(1, 50) if weighted else 1, work, outputs[2], parents)]
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    x = case(f"overlap{'_weighted' if weighted else ''}_k{count}_f{fanout}_r{relays}_seed{seed}", hardware(streams=8, memory=peak), nodes, duration, witness)
    x["generation"] = dict(seed=seed, family="overlapping_direct_consumers", witness_T=duration, witness_peak=peak, feasibility="known serial progression completing one consumer window at a time")
    if weighted:
        x["generation"]["weighted"] = True
    return x


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=20261014)
    p.add_argument("--output", type=Path, default=Path("data/overlap.json"))
    p.add_argument("--weighted", action="store_true")
    args = p.parse_args()
    cases = [overlap_case(args.seed + k*100 + f*10+r, k, f, r, args.weighted) for k in [8, 24, 96, 384, 1536] for f in [1, 2, 4] for r in [1, 4]]
    args.output.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=cases), separators=(",", ":")))
    print(f"overlap records={len(cases)} seed={args.seed}")


if __name__ == "__main__":
    main()
