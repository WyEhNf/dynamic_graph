"""New topologies and scarce-core witnesses, independent of the C++ solver.

Exact parallel optima are subsequently attached by aicore_oracle, not here.
Python resource simulation derives witnesses; both C++ models check them.
"""
import argparse
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness
from generate_research_cases import analytic_witness


def resource_witness(hw, nodes, witness):
    """Event-driven third implementation, using original direct users only."""
    index = {v["id"]: i for i, v in enumerate(nodes)}
    flows = [s["tasks"] for s in witness["streams"] if s["tasks"]]
    cursors = [[0, "waiting", None] for _ in flows]
    users = [0] * len(nodes)
    for v in nodes:
        for p in v["inputs"]:
            users[index[p]] += 1
    ready, done = set(), set()
    cores = {"AIC": 0, "AIV": 0}
    clock = memory = peak = 0
    while len(done) < len(nodes):
        change = True
        while change and len(done) < len(nodes):
            change = False
            for stream, cursor in zip(flows, cursors):
                k, stage, due = cursor
                if k == len(stream) or due != clock:
                    continue
                t = stream[k]
                i = index[t["op_id"]]
                v = nodes[i]
                if stage == "wait_timer":
                    cursor[:] = [k, "compute_ready", None]
                elif stage == "compute_timer":
                    done.add(i)
                    cores[v["core_type"]] -= v["core_num"]
                    memory -= v["workspace_memory"]
                    for p in v["inputs"]:
                        j = index[p]
                        users[j] -= 1
                        if users[j] == 0:
                            memory -= nodes[j]["output_memory"]
                    if t["record_after"] >= 0 and hw["event_record_time"]:
                        cursor[:] = [k, "record_timer", clock + hw["event_record_time"]]
                    else:
                        if t["record_after"] >= 0:
                            ready.add(t["record_after"])
                        cursor[:] = [k + 1, "waiting", None]
                elif stage == "record_timer":
                    ready.add(t["record_after"])
                    cursor[:] = [k + 1, "waiting", None]
                change = True
            if len(done) == len(nodes):
                break
            for stream, cursor in zip(flows, cursors):
                k, stage, due = cursor
                if k == len(stream):
                    continue
                t = stream[k]
                v = nodes[index[t["op_id"]]]
                if stage == "waiting" and all(e in ready for e in t["wait_before"]):
                    duration = len(t["wait_before"]) * hw["event_wait_time"]
                    cursor[:] = [k, "wait_timer" if duration else "compute_ready", clock + duration if duration else None]
                    change = True
                if cursor[1] == "compute_ready":
                    kind = v["core_type"]
                    allocation = v["workspace_memory"] + v["output_memory"]
                    if cores[kind] + v["core_num"] <= hw["aic_core_num" if kind == "AIC" else "aiv_core_num"] and memory + allocation <= hw["memory_limit"]:
                        assert all(index[p] in done for p in v["inputs"])
                        cores[kind] += v["core_num"]
                        memory += allocation
                        peak = max(peak, memory)
                        cursor[:] = [k, "compute_timer", clock + v["exec_time"]]
                        change = True
        if len(done) < len(nodes):
            future = [due for k, stage, due in cursors if due is not None and due > clock]
            assert future, "Constructive witness deadlocked"
            clock = min(future)
    return clock, peak


def relay_case(seed, components, relays):
    rng = random.Random(seed)
    ids = rng.sample(range(10_000, 2_000_000_000), 3 * components + relays)
    nodes = [node(ids[r], "AIC", 1, 1, 0, 0) for r in range(relays)]
    for k in range(components):
        a, b, c = ids[relays+3*k:relays+3*k+3]
        roots = rng.sample(ids[:relays], rng.randint(1, relays))
        nodes += [node(a, "AIC", 1, rng.randint(10_000, 100_000), 1, 100, roots),
                  node(b, "AIV", 1, 1, 1, 100, roots),
                  node(c, "AIC", 1, 1, 220, 1, [a, b])]
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    x = case(f"connected_relay_k{components}_r{relays}_seed{seed}", hardware(streams=8, memory=peak), nodes, duration, witness)
    x["generation"] = dict(family="connected_memory_relay", seed=seed, witness_T=duration, witness_peak=peak, feasibility="serial component completion behind shared zero-output relay roots")
    return x


def random_case(seed, n, density, record, scarce):
    rng = random.Random(seed)
    ids = rng.sample(range(10_000, 2_000_000_000), n)
    nodes = []
    for i in range(n):
        parents = [ids[j] for j in range(i) if rng.random() < density]
        if scarce and len(parents) > 8:
            parents = rng.sample(parents, 8)
        nodes.append(node(ids[i], rng.choice(["AIC", "AIV"]), rng.randint(1, 8), rng.choice([1, 2, 10, 1000, 100000]), rng.randint(0, 80), rng.choice([0, 1, 4, 20]), parents))
    hw = hardware(streams=8, memory=10**9, record=record, wait=record)
    if scarce:
        assignment = [rng.randrange(8) for _ in nodes]
        witness, _, _ = analytic_witness(nodes, assignment, 8, record, record, [])
        duration, peak = resource_witness(hw, nodes, witness)
        proof = "independent Python scarce-core event simulation checked by two C++ models"
        family = "scarce_core_long_distance"
    else:
        witness, duration, peak = serial_witness(nodes)
        proof = "known topological serial order with exact direct-user lifetime"
        family = "dense_long_distance"
    hw["memory_limit"] = peak
    rng.shuffle(nodes)
    x = case(f"{family}_n{n}_d{density}_e{record}_seed{seed}", hw, nodes, duration, witness)
    x["generation"] = dict(family=family, seed=seed, density=str(density), witness_T=duration, witness_peak=peak, feasibility=proof)
    return x


def oracle_case(seed, n):
    rng = random.Random(seed)
    ids = rng.sample(range(10_000, 2_000_000_000), n)
    nodes = [node(ids[i], rng.choice(["AIC", "AIV"]), rng.randint(1, 2), rng.randint(1, 30), rng.randint(0, 12), rng.randint(0, 8), [ids[j] for j in range(i) if rng.random() < .3]) for i in range(n)]
    witness, duration, peak = serial_witness(nodes)
    rng.shuffle(nodes)
    return case(f"parallel_oracle_n{n}_seed{seed}", hardware(aic=2, aiv=2, streams=2, memory=peak, record=seed % 4, wait=(seed // 4) % 4), nodes, duration, witness)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=20261012)
    p.add_argument("--output", type=Path, default=Path("data/frontier.json"))
    p.add_argument("--oracle-output", type=Path, default=Path("data/parallel-oracle-input.json"))
    args = p.parse_args()
    cases = []
    for k in [10, 32, 128, 512]:
        for relays in [1, 3, 8]:
            cases.append(relay_case(args.seed + 100*k + relays, k, relays))
    for n in [16, 64, 256, 1024]:
        for d in [.02, .12, .35]:
            for e in [0, 3, 100000]:
                cases.append(random_case(args.seed + n*100 + int(d*1000) + e, n, d, e, False))
    for n in [32, 128, 512, 2048]:
        for d in [.02, .12]:
            for e in [0, 3, 100000]:
                cases.append(random_case(args.seed + n*100 + int(d*1000) + e + 10, n, d, e, True))
    args.output.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=cases), separators=(",", ":")), encoding="utf-8")
    oracle = [oracle_case(args.seed + i, 3 if i < 4 else 4) for i in range(24)]
    args.oracle_output.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=oracle)), encoding="utf-8")
    print(f"frontier={len(cases)} oracle-input={len(oracle)} seed={args.seed}")


if __name__ == "__main__":
    main()
