"""Reproducible research workload; witnesses never consult the C++ solver.

Small one-stream cases have an exact subset-DP minimum-peak oracle. Parallel
cases have a constructive event witness with analytically computed timings:
one computation per stream and capacity >= streams * largest core request.
Both proofs use original direct-consumer output lifetimes, not guard edges.
"""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, plan, task, synthetic, official_samples, serial_witness


def serial_oracle(nodes):
    n = len(nodes)
    index = {x["id"]: i for i, x in enumerate(nodes)}
    pred = [sum(1 << index[p] for p in x["inputs"]) for x in nodes]
    succ = [0] * n
    for i, x in enumerate(nodes):
        for p in x["inputs"]:
            succ[index[p]] |= 1 << i
    size = 1 << n
    dp = [10**30] * size
    previous = [-1] * size
    dp[0] = 0
    for mask in range(size):
        if dp[mask] == 10**30:
            continue
        live = sum(x["output_memory"] for i, x in enumerate(nodes)
                   if mask >> i & 1 and (not succ[i] or succ[i] & ~mask))
        for i, x in enumerate(nodes):
            if mask >> i & 1 or pred[i] & ~mask:
                continue
            nxt = mask | 1 << i
            peak = max(dp[mask], live + x["workspace_memory"] + x["output_memory"])
            if peak < dp[nxt]:
                dp[nxt], previous[nxt] = peak, i
    mask, order = size - 1, []
    while mask:
        i = previous[mask]
        order.append(i)
        mask ^= 1 << i
    order.reverse()
    return plan([task(nodes[i]["id"]) for i in order]), sum(x["exec_time"] for x in nodes), dp[-1]


def oracle_case(seed, n, density):
    rng = random.Random(seed)
    ids = rng.sample(range(1_000_000, 2_000_000_000), n)
    nodes = []
    for i in range(n):
        parents = [ids[j] for j in range(i) if rng.random() < density]
        nodes.append(node(ids[i], rng.choice(["AIC", "AIV"]), rng.randint(1, 8),
                          rng.randint(1, 1000), rng.randint(0, 180),
                          rng.choice([0, 3, 20, 80, 150]), parents))
    witness, duration, peak = serial_oracle(nodes)
    rng.shuffle(nodes)
    x = case(f"oracle_n{n}_d{density}_seed{seed}", hardware(streams=1, memory=peak), nodes, duration, witness)
    x["generation"] = dict(seed=seed, family="serial_oracle", feasibility="exact subset DP", oracle_peak=peak, witness_T=duration, witness_peak=peak)
    return x


def analytic_witness(nodes, assignment, streams, record, wait, extra):
    index = {x["id"]: i for i, x in enumerate(nodes)}
    before = [{index[p] for p in x["inputs"]} for x in nodes]
    for consumer, producer in extra:
        before[consumer].add(producer)
    records = {p for i, parents in enumerate(before) for p in parents if assignment[p] != assignment[i]}
    # Sparse event IDs exercise compact mapping; there are no reused recorders.
    event = {p: 17 + p * 37 for p in sorted(records)}
    output = [[] for _ in range(streams)]
    flow_end = [0] * streams
    start, end, event_ready = [], [], []
    successors = [[] for _ in nodes]
    for i, x in enumerate(nodes):
        for p in x["inputs"]:
            successors[index[p]].append(i)
        s = assignment[i]
        waits = [p for p in before[i] if assignment[p] != s]
        t = max([flow_end[s]] + [event_ready[p] for p in waits]) + len(waits) * wait
        start.append(t)
        end.append(t + x["exec_time"])
        event_ready.append(end[-1] + (record if i in records else 0))
        flow_end[s] = event_ready[-1]
        output[s].append(task(x["id"], [event[p] for p in reversed(sorted(waits))], event.get(i, -1)))
    duration = max(end, default=0)
    deltas = {}
    def change(t, amount):
        neg, pos = deltas.get(t, (0, 0))
        deltas[t] = (neg + min(0, amount), pos + max(0, amount))
    for i, x in enumerate(nodes):
        change(start[i], x["workspace_memory"] + x["output_memory"])
        change(end[i], -x["workspace_memory"])
        release = max((end[j] for j in successors[i]), default=duration)
        change(release, -x["output_memory"])
    live = peak = 0
    for t in sorted(deltas):
        neg, pos = deltas[t]
        live += neg
        live += pos
        peak = max(peak, live)
    assert live == 0
    return plan(*output), duration, peak


def parallel_case(seed, n, family, event_cost, tight):
    rng = random.Random(seed)
    streams = min(16, max(2, n // 8))
    ids = rng.sample(range(1_000_000, 2_000_000_000), n)
    nodes, assignments, extra = [], [], []
    width = rng.randint(3, 13)
    for i in range(n):
        if family == "erdos":
            parents = rng.sample(range(i), min(i, rng.randint(0, 5)))
        elif family == "irregular":
            lower = max(0, i - rng.randint(1, width * 3))
            parents = rng.sample(range(lower, i), min(i - lower, rng.randint(0, 5)))
        elif family == "fork_join":
            block = i // width * width
            parents = ([block - 1] if block else []) if i % width != width - 1 else list(range(block, i))
        elif family == "disconnected":
            lane = i % streams
            parents = [i - streams] if i >= streams else []
            if i > streams and rng.random() < .12:
                parents += [rng.randrange(i)]
        elif family == "butterfly":
            lane_width = 16
            layer, lane = divmod(i, lane_width)
            hop = 1 << (layer % 4)
            parents = [(layer - 1) * lane_width + lane,
                       (layer - 1) * lane_width + (lane ^ hop)] if layer else []
        elif family == "comb":
            parents = [i - 2] if i >= 2 and i % 2 == 0 else ([i - 1] if i % 2 else [])
        elif family == "wide_merge":
            block = i // 32 * 32
            parents = list(range(block, i)) if i % 32 == 31 else ([block - 1] if block else [])
        else:  # Legacy label "scale_free": weighted-parent DAG; no power-law claim.
            population = [j for j in range(i) for _ in range(1 + min(8, len(nodes[j]["inputs"])))]
            parents = sorted(set(rng.choices(population, k=rng.randint(1, 5)))) if population else []
        duration = rng.choice([1, 2, 5, 10, 100, 1000, 100000]) if family == "irregular" else rng.randint(1, 500)
        output = rng.choice([0, 1, 4, 30, 100])
        work = rng.choice([0, 2, 10, 50, 180])
        nodes.append(node(ids[i], rng.choice(["AIC", "AIV"]), rng.randint(1, 8), duration, work, output, [ids[p] for p in sorted(set(parents))]))
        assignments.append(rng.randrange(streams))
        if i and rng.random() < .08:
            extra.append((i, rng.randrange(i)))
    witness, duration, peak = analytic_witness(nodes, assignments, streams, event_cost, event_cost, extra)
    hw = hardware(128, 128, streams, peak, event_cost, event_cost)
    deadline = duration if tight else duration * 2
    rng.shuffle(nodes)
    x = case(f"parallel_{family}_n{n}_event{event_cost}_{'tight' if tight else 'slack'}_seed{seed}", hw, nodes, deadline, witness)
    x["generation"] = dict(seed=seed, family=family, feasibility="analytic event witness; capacities bound simultaneous cores", witness_T=duration, witness_peak=peak, extra_guards=len(extra))
    return x


def component_case(seed, n):
    """Many two-input merges: witness completes each component before opening another.

    This targets inter-component output accumulation rather than a global ID
    order. The generator randomizes IDs and rows without querying the solver.
    """
    assert n % 3 == 0
    rng = random.Random(seed)
    ids = rng.sample(range(1_000_000, 2_000_000_000), n)
    nodes = []
    for k in range(0, n, 3):
        nodes.extend([node(ids[k], "AIC", 1, 1, 1, 100),
                      node(ids[k+1], "AIV", 1, 1, 1, 100),
                      node(ids[k+2], "AIC", 1, 1, 220, 1, ids[k:k+2])])
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    x = case(f"components_n{n}_seed{seed}", hardware(streams=8, memory=peak), nodes, duration, witness)
    x["generation"] = dict(seed=seed, family="disjoint_memory_merges", feasibility="serial component witness", witness_T=duration, witness_peak=peak)
    return x


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/research.json"))
    parser.add_argument("--seed", type=int, default=20261011)
    args = parser.parse_args()
    cases = official_samples()
    for n in [8, 12, 16]:
        for k in range(12):
            cases.append(oracle_case(args.seed + n * 100 + k, n, [.08, .2, .45][k % 3]))
    for n in [32, 128, 512, 2048]:
        for k, family in enumerate(["erdos", "irregular", "fork_join", "disconnected", "scale_free"]):
            for j, ev in enumerate([0, 3, 1000000]):
                cases.append(parallel_case(args.seed + n * 100 + k * 10 + j, n, family, ev, j == 0))
    for n in [1024, 4096, 10000]:
        for shape in ["random", "layered", "sinks", "chain"]:
            cases.append(synthetic(args.seed + n, n, shape, "normal"))
    for n in [64, 256, 1024]:
        for k, family in enumerate(["butterfly", "comb", "wide_merge"]):
            for j, ev in enumerate([0, 3, 1000000]):
                cases.append(parallel_case(args.seed + n * 1000 + k * 10 + j, n, family, ev, False))
    for n in [96, 768, 3072, 9216]:
        cases.append(component_case(args.seed+n, n))
    cases.append(oracle_case(args.seed+18*100, 18, .2))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=cases), separators=(",", ":")), encoding="utf-8")
    print(f"generated {len(cases)} research cases -> {args.output}")


if __name__ == "__main__":
    main()
