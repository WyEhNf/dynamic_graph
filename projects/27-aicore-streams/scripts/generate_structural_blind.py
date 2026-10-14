"""One-time post-freeze structural validation; never filter by solver outcome."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def make(seed, count, family, retained, variant):
    rng = random.Random(seed)
    ids = iter(rng.sample(range(10_000, 2_000_000_000), count*16+4))
    roots = [next(ids) for _ in range(rng.randint(1, 4))]
    stages = []
    for _ in range(count):
        stages.append(([next(ids) for _ in range(rng.randint(1, 3))],
                       [next(ids) for _ in range(rng.randint(1, 2))],
                       [next(ids) for _ in range(rng.randint(5, 8) if variant == 'high-fanout' else rng.randint(1, 3))]))
    extra = {c: [] for _, _, cs in stages for c in cs}
    for i, (producers, _, _) in enumerate(stages):
        horizon = min(count-1-i, 8 if family == 'local' else 32)
        for producer in producers:
            if horizon:
                for j in rng.sample(range(i+1, i+1+horizon), rng.randint(0, min(horizon, 8 if family == 'dense' else 3))):
                    extra[rng.choice(stages[j][2])].append(producer)
    root_memory = seed % 2 * 5
    nodes = [node(r, 'AIC', 1, 1, 0, root_memory) for r in roots]
    for i, (ps, bs, cs) in enumerate(stages):
        parents = rng.sample(roots, rng.randint(1, len(roots)))
        if retained and i and rng.random() < .4:
            parents.append(rng.choice(stages[rng.randrange(i)][2]))
        for p in ps:
            duration = rng.randint(1, 100) if variant == 'equal-duration' else rng.randint(1000, 100000)
            nodes.append(node(p, rng.choice(['AIC', 'AIC', 'AIV']), rng.randint(1, 8), duration, rng.randint(0, 5), rng.randint(30, 180), parents))
        for b in bs:
            nodes.append(node(b, rng.choice(['AIC', 'AIV']), rng.randint(1, 8), rng.randint(1, 100 if variant == 'equal-duration' else 30), rng.randint(0, 5), rng.randint(40, 160), parents))
        for c in cs:
            inputs = ps + bs + extra[c]; rng.shuffle(inputs)
            nodes.append(node(c, rng.choice(['AIC', 'AIV']), rng.randint(1, 8), rng.randint(1, 100), rng.randint(150, 500), rng.randint(0, 5) if retained else 0, inputs))
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    x = case(f'blind_{variant}_{family}_k{count}_ret{retained}_seed{seed}', hardware(streams=8, memory=peak, record=3, wait=3), nodes, duration, witness)
    x['generation'] = dict(seed=seed, variant=variant, stages=count, connection=family, retained_outputs=retained, root_output_memory=root_memory,
        witness_T=duration, witness_peak=peak, feasibility='solver-independent hidden serial construction; no outcomes filtered')
    return x


def main():
    p = argparse.ArgumentParser(); p.add_argument('--seed', type=int, default=20281026); p.add_argument('--output', type=Path, default=Path('data/structural-blind-batch26.json')); a = p.parse_args()
    cases = [make(a.seed+k*100+v*10+f*2+r, k, family, r, variant)
        for k in [12,64,128] for v,variant in enumerate(['irregular','equal-duration','high-fanout'])
        for f,family in enumerate(['local','dense']) for r in [0,1]]
    payload = dict(format='aicore-local-v1', generator_seed=a.seed,
        validation_scope='generated after batch26 source/executable freeze, one-time unseen test; no algorithm tuning from this result', cases=cases)
    a.output.write_text(json.dumps(payload, separators=(',',':')), encoding='utf-8')
    provenance = dict(input_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(), generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        baseline_source_sha256=hashlib.sha256(Path('research/batch23/solution.cpp').read_bytes()).hexdigest(),
        after_source_sha256=hashlib.sha256(Path('research/batch26/solution.cpp').read_bytes()).hexdigest(), records=len(cases), nodes_range=[min(len(x['nodes']) for x in cases),max(len(x['nodes']) for x in cases)])
    Path('reports/structural-blind-batch26-provenance.json').write_text(json.dumps(provenance, indent=2))
    print(provenance)


if __name__ == '__main__': main()
