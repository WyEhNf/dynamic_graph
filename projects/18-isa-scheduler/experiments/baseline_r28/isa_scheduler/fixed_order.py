"""Exact relay timing for one fixed original-node order, never global ordering.

At prefix i the identities of live values are determined by last uses, so the
state stores only their ages. There are at most P(W,k_i) assignments at that
prefix. Early relays are included. Original nodes are emitted once; a relay
refreshes one logical identity; no alias folding/recomputation/spill is allowed.
"""
import heapq
from math import perm
from time import perf_counter

from .bounds import fixed_order_copy_bound
from .model import BudgetExceeded, InfeasibleSchedule


def solve_fixed_order(block, order, incumbent=None, *, time_budget_ms=500, max_states=100000):
    started = perf_counter()
    if time_budget_ms <= 0 or max_states <= 0:
        raise ValueError("Positive time/state budgets required")
    bound = fixed_order_copy_bound(block, order)
    nodes, window, count = block.instructions, block.window, len(order)
    if bound["fixed_order_peak_live"] > window:
        raise InfeasibleSchedule("fixed_order_capacity_infeasible: original ordering only")
    if incumbent is not None and incumbent["stats"].get("original_order") != list(order):
        raise ValueError("Incumbent belongs to another original-node order")
    deadline = started + time_budget_ms / 1000
    ranks = {node: rank for rank, node in enumerate(order)}
    last = [-1]*count
    for node in nodes:
        for source in set(node.args): last[source] = max(last[source], ranks[node.index])
    live_ids, operands, retained = [()], [], []
    for rank, index in enumerate(order):
        active = live_ids[-1]
        lookup = {source: j for j, source in enumerate(active)}
        operands.append(tuple(lookup[arg] for arg in nodes[index].args))
        keep = tuple(j for j, source in enumerate(active) if last[source] > rank)
        retained.append(keep)
        after = tuple(active[j] for j in keep)
        if last[index] > rank: after += (index,)
        live_ids.append(after)
    state_bound = sum(perm(window, len(active)) for active in live_ids)
    initial = (0, ())
    distances, parents = {initial: 0}, {}
    frontier = [(0, 0, 0, initial)]
    explored = serial = 0
    best = incumbent
    best_cost = incumbent["stats"]["inserted_copy_count"] if incumbent else float("inf")
    outcome = "exhausted"

    def rebuild(state, copies):
        transitions = []
        while state != initial:
            previous, action = parents[state]
            transitions.append(action)
            state = previous
        rows = []
        for kind, index, ages in reversed(transitions):
            row = {"id": len(rows), "op": kind}
            if kind == "COPY_INSERTED":
                row.update(op="COPY", source=f"t#{ages[0]}")
            else:
                node = nodes[index]
                if node.reg is not None: row["reg"] = node.reg
                if kind == "COPY": row["source"] = f"t#{ages[0]}"
                elif ages: row["inputs"] = [f"t#{age}" for age in ages]
            rows.append(row)
        total_copy = sum(row["op"] == "COPY" for row in rows)
        return {"block_id": block.block_id, "optimized_instructions": rows, "stats": {
            "strategy": "fixed_order_exact", "original_instruction_count": count,
            "optimized_instruction_count": len(rows), "inserted_copy_count": copies,
            "total_copy_count": total_copy, "copy_ratio_output": total_copy/len(rows) if rows else 0,
            "inserted_copy_ratio_original": copies/count if count else 0,
            "original_order": list(order), "bit_width": block.bit_width,
            "max_back_distance": window}}

    while frontier:
        if perf_counter() >= deadline:
            outcome = "time_budget_exhausted"; break
        if explored >= max_states:
            outcome = "state_budget_exhausted"; break
        cost, _, _, state = heapq.heappop(frontier)
        if cost != distances.get(state): continue
        if cost >= best_cost:
            outcome = "optimal_for_fixed_order_under_model"; break
        explored += 1
        prefix, ages = state
        if prefix == count:
            best, best_cost = rebuild(state, cost), cost
            outcome = "optimal_for_fixed_order_under_model"; break
        transitions = []
        index = order[prefix]
        following = tuple(ages[j]+1 for j in retained[prefix])
        if last[index] > prefix: following += (1,)
        if all(age <= window for age in following):
            transitions.append((cost, (prefix+1, following),
                                (nodes[index].op, index, tuple(ages[j] for j in operands[prefix]))))
        for slot, age in enumerate(ages):
            if age == 1 or cost+1 >= best_cost: continue
            following = tuple(1 if j == slot else other+1 for j, other in enumerate(ages))
            if all(other <= window for other in following):
                transitions.append((cost+1, (prefix, following),
                                    ("COPY_INSERTED", live_ids[prefix][slot], (age,))))
        for next_cost, next_state, action in transitions:
            if next_cost < distances.get(next_state, float("inf")):
                distances[next_state] = next_cost
                parents[next_state] = (state, action)
                serial += 1
                heapq.heappush(frontier, (next_cost, -next_state[0], serial, next_state))
    if outcome == "exhausted":
        outcome = "optimal_for_fixed_order_under_model" if best else "fixed_order_infeasible_under_model"
    if best is None:
        if "budget_exhausted" in outcome: raise BudgetExceeded(outcome)
        raise InfeasibleSchedule(outcome)
    return {**best, "stats": {**best["stats"], "fixed_order_search": {
        "outcome": outcome, "explored_states": explored, "reached_states": len(distances),
        "combinatorial_state_bound": state_bound, "copy_lower_bound": bound["copy_lower_bound"],
        "elapsed_ms": (perf_counter()-started)*1000, "time_budget_ms": time_budget_ms,
        "max_states": max_states,
        "proof_scope": "fixed original order only; original nodes emitted once; identity-preserving COPY; no alias folding/recompute/spill"}}}
