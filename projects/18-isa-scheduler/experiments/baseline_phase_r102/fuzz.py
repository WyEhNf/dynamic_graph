"""Deterministic synthetic differential corpus and minimized counterexamples."""
import json
from pathlib import Path
import random
from itertools import combinations
from time import perf_counter

from .evaluation import evaluate_case, fingerprint, summarize
from .model import BudgetExceeded, InfeasibleSchedule, parse_block
from .optimizer import optimize
from .scheduler import schedule


def generate(seed, family, bits):
    rng = random.Random(seed)
    rows = []

    def emit(op, args=(), reg=None):
        index = len(rows)
        row = {"id": index, "op": op}
        if reg is not None:
            row["reg"] = reg
        if args:
            row["inputs"] = [f"t#{index-a}" for a in args]
        rows.append(row)

    if family == "hazard":
        emit("GET", reg="a")
        emit("GET", reg="b")
        emit("ADD", (0, 1))
        emit("SET", (2,), reg="a")
        emit("GET", reg="a")
        emit(rng.choice(("MULW", "ADD")), (4, 1))
        emit("SET", (5,), reg="out")
    else:
        target = rng.randint(7, 10) if family == "wide" else rng.randint(5, 10)
        roots = rng.randint(4, min(5, target - 2)) if family == "wide" else 2
        for i in range(roots):
            emit("GET", reg=f"r{i}")
        while len(rows) < target - 1:
            index = len(rows)
            if family == "highfanout":
                args = (0, index - 1)
            elif family == "branch":
                args = (rng.randrange(index), rng.randrange(index))
            else:
                args = (rng.randrange(roots), index - 1)
            emit(rng.choice(("ADD", "MULW")), args)
        emit("SET", (len(rows) - 1,), reg="out")
    return {"block_id": f"synthetic-{family}-{seed}", "bit_width": bits, "instructions": rows}


def minimize_dead_nodes(data, predicate, memory_order="hazard"):
    """Minimum node count among dependency-closed induced subgraphs (n <= 10).

This scope allows deleting GET/SET too, changing the input problem; the failure
predicate must still hold for the new input. It is not a global minimum over all
possible instruction programs or operand rewrites.
"""
    block = parse_block(data, memory_order)
    if len(block.instructions) > 10:
        raise ValueError("Counterexample minimizer limited to 10 nodes")
    for size in range(1, len(block.instructions) + 1):
        for subset in combinations(range(len(block.instructions)), size):
            indices = set(subset)
            kept = [node for node in block.instructions if node.index in indices]
            if any(not set(node.args) <= indices for node in kept):
                continue
            mapping = {node.index: i for i, node in enumerate(kept)}
            rows = []
            for node in kept:
                index = mapping[node.index]
                row = {"id": index, "op": node.op}
                if node.reg is not None:
                    row["reg"] = node.reg
                tokens = [f"t#{index-mapping[arg]}" for arg in node.args]
                if node.op == "COPY":
                    row["source"] = tokens[0]
                elif tokens:
                    row["inputs"] = tokens
                rows.append(row)
            candidate = {**data, "instructions": rows}
            if predicate(candidate):
                return candidate
    return data


def run_fuzz(count=10000, seed=18, counterexample_dir="outputs/counterexamples",
             time_budget_ms=100, max_states=10000, memory_order="hazard"):
    if count < 1:
        raise ValueError("count must be positive")
    started = perf_counter()
    records, saved = [], {}
    families = ("wide", "branch", "highfanout", "hazard")
    destination = Path(counterexample_dir)
    destination.mkdir(parents=True, exist_ok=True)
    recovered = improved = verified_cases = 0
    for case in range(count):
        family = families[case % len(families)]
        bits = 2 + ((case // len(families)) % 4)
        case_seed = seed + case
        data = generate(case_seed, family, bits)
        outcomes = {}
        for strategy in ("stable", "ready", "auto"):
            record, result = evaluate_case(data, strategy, source=f"synthetic:{family}:{case}",
                                           seed=case_seed, time_budget_ms=time_budget_ms,
                                           max_states=max_states, memory_order=memory_order)
            record["family"] = family
            records.append(record)
            outcomes[strategy] = (record, result)
        auto_row, auto_result = outcomes["auto"]
        if auto_result:
            verified_cases += 1
            baseline_successes = [r for r, result in (outcomes["stable"], outcomes["ready"]) if result]
            if not baseline_successes:
                recovered += 1
            if baseline_successes and auto_row["inserted_copy_count"] < min(r["inserted_copy_count"] for r in baseline_successes):
                improved += 1
        for strategy in ("stable", "ready"):
            row, result = outcomes[strategy]
            kind = f"{strategy}-recovered" if result is None and auto_result else None
            if kind and kind not in saved:
                def remains_failure(candidate):
                    try:
                        schedule(parse_block(candidate, memory_order), strategy=strategy)
                        return False
                    except (InfeasibleSchedule, BudgetExceeded):
                        try:
                            optimize(candidate, "exact", time_budget_ms=100, max_states=30000, memory_order=memory_order)
                            return True
                        except (InfeasibleSchedule, BudgetExceeded):
                            return False
                minimal = minimize_dead_nodes(data, remains_failure, memory_order)
                file = destination / f"{kind}.json"
                file.write_text(json.dumps(minimal, indent=2) + "\n", encoding="utf-8")
                saved[kind] = {"path": str(file), "sha256": fingerprint(minimal),
                               "minimization_scope": "minimum node count among dependency-closed induced subgraphs reproducing bounded failure/recovery predicate; original order and operands preserved"}
        if auto_result is None and "first-auto-failure" not in saved:
            failure_status = auto_row["status"]
            def still_same_failure(candidate):
                record, result = evaluate_case(candidate, "auto", time_budget_ms=100, max_states=30000, memory_order=memory_order)
                return result is None and record["status"] == failure_status
            minimized_failure = minimize_dead_nodes(data, still_same_failure, memory_order)
            file = destination / "first-auto-failure.json"
            file.write_text(json.dumps(minimized_failure, indent=2) + "\n", encoding="utf-8")
            saved["first-auto-failure"] = {"path": str(file), "status": auto_row["status"],
                                         "sha256": fingerprint(minimized_failure), "minimization_scope": "minimum node count among dependency-closed induced subgraphs reproducing bounded same-status failure"}
        if any(row["status"] == "verification_failure" for row, _ in outcomes.values()):
            file = destination / "semantic-failure.json"
            file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"Fuzz found incorrect semantics; retained input: {file}")
    return {"dataset": "synthetic deterministic small graphs; NOT official evaluation data",
            "seed": seed, "case_count": count, "memory_order": memory_order, "family_bit_width_coverage": {
                family: {str(bits): sum(r.get("family") == family and r.get("bit_width") == bits
                                       and r["strategy"] == "auto" for r in records) for bits in range(2, 6)}
                for family in families},
            "time_budget_ms_per_case": time_budget_ms, "max_states": max_states,
            "verified_cases_auto": verified_cases, "both_baselines_failed_but_auto_recovered": recovered,
            "auto_copy_improvements_over_best_baseline": improved,
            "counterexamples": saved, "elapsed_seconds": perf_counter() - started,
            "summary": summarize(records), "records": records}

