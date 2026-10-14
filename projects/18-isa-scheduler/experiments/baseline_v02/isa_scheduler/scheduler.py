"""A deterministic ready-list baseline with COPY relays and bounded failure.

This heuristic is not a complete feasibility solver: an unsuccessful scheduling
choice may fail even if a different ordering exists. No impossible COPY loop is
silently accepted. Remaining uses count distinct consuming instructions.
"""
from collections import Counter
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule


def schedule(block, strategy="ready", max_copy_factor=8, time_budget_ms=None):
    if strategy not in ("ready", "stable"):
        raise ValueError("strategy must be ready or stable")
    started = perf_counter()
    deadline = started + time_budget_ms / 1000 if time_budget_ms is not None else float("inf")
    nodes = block.instructions
    dependencies, users = [], [[] for _ in nodes]
    remaining = Counter()
    for node in nodes:
        deps = set(node.args)
        deps.update(node.order_deps)
        dependencies.append(deps)
        for dep in deps:
            users[dep].append(node.index)
        for arg in set(node.args):
            remaining[arg] += 1
    pending = [len(deps) for deps in dependencies]
    ready = {i for i, count in enumerate(pending) if count == 0}
    height = [0] * len(nodes)
    for i in range(len(nodes) - 1, -1, -1):
        height[i] = 1 + max((height[u] for u in users[i]), default=0)
    output, positions, done = [], {}, set()
    copies = 0
    stalled_copies = 0
    copy_limit = max(block.window, max_copy_factor * max(1, len(nodes)))
    while len(done) < len(nodes):
        if perf_counter() >= deadline:
            raise BudgetExceeded("Heuristic time budget exhausted")
        now = len(output)
        live = {i for i, count in remaining.items() if count > 0 and i in positions}
        lost = [i for i in live if now - positions[i] > block.window]
        if lost:
            raise InfeasibleSchedule(f"Live value(s) became unreachable: {lost}")
        expiring = {i for i in live if now - positions[i] == block.window}

        def can_emit(index):
            # Any value at the oldest reachable slot must die on this step.
            args = set(nodes[index].args)
            return all(i in args and remaining[i] == 1 for i in expiring)

        candidates = sorted(ready)
        if strategy == "stable":
            candidates = candidates[:1]
        eligible = [i for i in candidates if can_emit(i)]
        if eligible:
            if strategy == "ready":
                def score(i):
                    args = set(nodes[i].args)
                    freed = sum(remaining[a] == 1 for a in args)
                    oldest = max((now - positions[a] for a in args), default=0)
                    return freed, oldest, height[i], -i
                index = max(eligible, key=score)
            else:
                index = eligible[0]
            node = nodes[index]
            encoded = [f"t#{now - positions[a]}" for a in node.args]
            row = {"id": now, "op": node.op}
            if node.reg is not None:
                row["reg"] = node.reg
            if node.op == "COPY":
                row["source"] = encoded[0]
            elif encoded:
                row["inputs"] = encoded
            output.append(row)
            positions[index] = now
            for arg in set(node.args):
                remaining[arg] -= 1
            done.add(index)
            ready.remove(index)
            for user in users[index]:
                pending[user] -= 1
                if pending[user] == 0:
                    ready.add(user)
            stalled_copies = 0
        elif expiring:
            oldest = min(expiring, key=lambda i: (positions[i], i))
            output.append({"id": now, "op": "COPY", "source": f"t#{now - positions[oldest]}"})
            positions[oldest] = now
            copies += 1
            stalled_copies += 1
            if stalled_copies >= block.window or copies > copy_limit:
                raise InfeasibleSchedule(
                    f"No progress within the {block.window}-instruction window; "
                    "this heuristic cannot find a feasible schedule. Try ready strategy "
                    "or a wider bit_width; no optimal infeasibility claim is made."
                )
        else:
            raise InfeasibleSchedule("No ready instruction: inconsistent dependency graph")
    elapsed = (perf_counter() - started) * 1000
    total_copies = sum(row["op"] == "COPY" for row in output)
    return {
        "block_id": block.block_id,
        "optimized_instructions": output,
        "stats": {
            "strategy": strategy,
            "original_instruction_count": len(nodes),
            "optimized_instruction_count": len(output),
            "inserted_copy_count": copies,
            "total_copy_count": total_copies,
            "copy_ratio_output": total_copies / len(output) if output else 0.0,
            "inserted_copy_ratio_original": copies / len(nodes) if nodes else 0.0,
            "elapsed_ms": elapsed,
            "bit_width": block.bit_width,
            "max_back_distance": block.window,
        },
    }

