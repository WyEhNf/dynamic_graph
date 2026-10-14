"""Finite-state COPY minimization oracle and bounded beam variant.

Proof scope: the supported pure operations, configured GET/SET dependency mode, each
original node emitted exactly once, COPY-only inserted instructions, no
recomputation or register rereads. States retain ages of live original values.
"""
import heapq
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule


def search(block, incumbent=None, *, time_budget_ms=100, max_states=30000,
           beam_width=None, exact_max_nodes=10, dominance=True, progress_tie=True):
    started = perf_counter()
    deadline = started + time_budget_ms / 1000
    nodes = block.instructions
    if beam_width is None and len(nodes) > exact_max_nodes:
        raise BudgetExceeded(f"Exact oracle limited to {exact_max_nodes} original nodes")
    deps, consumers = [], [0] * len(nodes)
    for node in nodes:
        dependencies = set(node.args)
        dependencies.update(node.order_deps)
        deps.append(sum(1 << d for d in dependencies))
        for arg in set(node.args):
            consumers[arg] |= 1 << node.index
    final_mask = (1 << len(nodes)) - 1
    initial = (0, ())
    frontier = [(0, 0, 0, initial)]
    distances = {initial: 0}
    parent = {}
    serial = explored = pruned = 0
    best = incumbent
    best_copies = incumbent["stats"]["inserted_copy_count"] if incumbent else float("inf")
    outcome = "exhausted"
    # For a fixed completed mask, live node identities are fixed. A no-more-
    # expensive state with componentwise younger ages can simulate every legal
    # continuation. This is a COPY-only single-emission model property; it is
    # not a theorem about algebraic rewrites or arbitrary machine state.
    pareto = {0: [(0, ())]}
    dominated = 0
    use_dominance = dominance and beam_width is None

    def admit(cost, next_state):
        nonlocal dominated
        if not use_dominance:
            return True
        mask, values = next_state
        bucket = pareto.setdefault(mask, [])
        def younger(left, right):
            return all(a[0] == b[0] and a[1] <= b[1] for a, b in zip(left, right)) and len(left) == len(right)
        if any(old_cost <= cost and younger(old_ages, values) for old_cost, old_ages in bucket):
            dominated += 1
            return False
        bucket[:] = [(old_cost, old_ages) for old_cost, old_ages in bucket
                     if not (cost <= old_cost and younger(values, old_ages))]
        bucket.append((cost, values))
        # Previously queued states remain valid and are not deleted. Parent
        # chains are preserved; this conservative form only rejects new states.
        return True

    def result_from(state, copies):
        transitions = []
        while state != initial:
            previous, transition = parent[state]
            transitions.append(transition)
            state = previous
        rows = []
        for kind, index, operand_ages in reversed(transitions):
            row = {"id": len(rows), "op": kind}
            if kind == "COPY_INSERTED":
                row["op"] = "COPY"
                row["source"] = f"t#{operand_ages[0]}"
            else:
                node = nodes[index]
                if node.reg is not None:
                    row["reg"] = node.reg
                tokens = [f"t#{age}" for age in operand_ages]
                if kind == "COPY":
                    row["source"] = tokens[0]
                elif tokens:
                    row["inputs"] = tokens
            rows.append(row)
        total = sum(r["op"] == "COPY" for r in rows)
        return {"block_id": block.block_id, "optimized_instructions": rows, "stats": {
            "strategy": "exact" if beam_width is None else "beam",
            "original_instruction_count": len(nodes), "optimized_instruction_count": len(rows),
            "inserted_copy_count": copies, "total_copy_count": total,
            "copy_ratio_output": total / len(rows) if rows else 0.0,
            "inserted_copy_ratio_original": copies / len(nodes) if nodes else 0.0,
            "bit_width": block.bit_width, "max_back_distance": block.window,
        }}

    while frontier:
        if perf_counter() >= deadline:
            outcome = "time_budget_exhausted"
            break
        if explored >= max_states:
            outcome = "state_budget_exhausted"
            break
        copies, _, _, state = heapq.heappop(frontier)
        if copies != distances.get(state):
            continue
        if copies >= best_copies:
            continue
        explored += 1
        mask, ages_tuple = state
        if mask == final_mask:
            best = result_from(state, copies)
            best_copies = copies
            # Uniform-cost search finds minimum COPY cost if no beam pruning.
            if beam_width is None:
                outcome = "optimal_under_model"
                break
            continue
        ages = dict(ages_tuple)
        actions = []
        for node in nodes:
            if node.index % 64 == 0 and perf_counter() >= deadline:
                outcome = "time_budget_exhausted"
                break
            if mask & (1 << node.index) or deps[node.index] & mask != deps[node.index]:
                continue
            if not all(a in ages for a in node.args):
                continue
            next_mask = mask | (1 << node.index)
            next_ages = {i: age + 1 for i, age in ages.items() if consumers[i] & ~next_mask}
            if consumers[node.index] & ~next_mask:
                next_ages[node.index] = 1
            if all(age <= block.window for age in next_ages.values()):
                transition = (node.op, node.index, tuple(ages[a] for a in node.args))
                actions.append((copies, (next_mask, tuple(sorted(next_ages.items()))), transition))
        if outcome == "time_budget_exhausted":
            break
        # Early COPY is included: limiting relays to expired values is incomplete.
        for source, source_age in ages.items():
            if source_age == 1 or copies + 1 >= best_copies:
                continue
            next_ages = {i: (1 if i == source else age + 1) for i, age in ages.items()}
            if all(age <= block.window for age in next_ages.values()):
                actions.append((copies + 1, (mask, tuple(sorted(next_ages.items()))),
                                ("COPY_INSERTED", source, (source_age,))))
        for cost, next_state, transition in actions:
            if cost < distances.get(next_state, float("inf")) and admit(cost, next_state):
                distances[next_state] = cost
                parent[next_state] = (state, transition)
                serial += 1
                progress = -next_state[0].bit_count() if progress_tie else 0
                heapq.heappush(frontier, (cost, progress, serial, next_state))
        if beam_width is not None and len(frontier) > beam_width:
            frontier = heapq.nsmallest(beam_width, frontier)
            heapq.heapify(frontier)
            pruned += 1
    if outcome == "exhausted" and beam_width is None:
        outcome = "optimal_under_model" if best else "proven_infeasible_under_model"
    elif outcome == "exhausted":
        outcome = "beam_exhausted_no_global_proof"
    if best is None:
        if outcome in ("time_budget_exhausted", "state_budget_exhausted"):
            raise BudgetExceeded(outcome)
        raise InfeasibleSchedule(outcome)
    result = {**best, "stats": {**best["stats"], "search": {
        "outcome": outcome, "explored_states": explored, "beam_prunings": pruned,
        "exact_max_nodes": exact_max_nodes, "max_states": max_states,
        "time_budget_ms": time_budget_ms, "elapsed_ms": (perf_counter() - started) * 1000,
        "proof_scope": "identical DAG edges; single emission; COPY only; no alias folding/recomputation",
        "memory_order": block.memory_order,
        "dominated_enqueue_states": dominated, "dominance_enabled": use_dominance,
        "progress_tie": progress_tie,
    }}}
    result["stats"]["elapsed_ms"] = (perf_counter() - started) * 1000
    return result

