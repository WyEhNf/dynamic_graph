"""Experimental ordered arithmetic aliases; every original row still executes.

GET and SET are distinct atoms, even for repeated registers. Only COPY and
identical ordered ADD/MULW expression trees share materialized values. This
changes the identity model and must not inherit identity-capacity certificates.
It assumes the documented local pure arithmetic semantics, not official consent
to operand substitution. Independent symbolic and integer verification remains
mandatory. This scan-based research prototype has O(n^2 + n*COPY) worst cost.
"""
from collections import Counter, OrderedDict
from time import perf_counter
from .incremental import PreparedGraph
from .model import BudgetExceeded, InfeasibleSchedule


def ordered_classes(block, deadline=float("inf")):
    classes, intern = [], {}
    for node in block.instructions:
        if node.index%128==0 and perf_counter()>=deadline:
            raise BudgetExceeded("Ordered-alias class construction budget exhausted")
        if node.op == "COPY":
            classes.append(classes[node.args[0]])
            continue
        key = ((node.op, node.index) if node.op in ("GET", "SET") else
               (node.op, tuple(classes[source] for source in node.args)))
        classes.append(intern.setdefault(key, len(intern)))
    return tuple(classes)


def schedule_aliases(block, *, time_budget_ms=None, prepared=None):
    started = perf_counter()
    deadline = started + time_budget_ms/1000 if time_budget_ms is not None else float("inf")
    prepared = prepared or PreparedGraph(block, time_budget_ms)
    if prepared.block is not block:
        raise ValueError("Prepared graph belongs to a different block")
    classes = ordered_classes(block, deadline)
    ranks, _ = prepared.demand(deadline)
    remaining, pending = list(prepared.remaining), list(prepared.pending)
    ready = {i for i, degree in enumerate(pending) if degree == 0}
    active, positions, live = Counter(), {}, OrderedDict()
    output, order = [], []
    copies = stalled = peak = 0

    def after_counts(index):
        consumed = Counter(classes[source] for source in prepared.args_unique[index])
        affected = set(consumed) | {classes[index]}
        return {c: active[c]-consumed[c]+(remaining[index] if c == classes[index] else 0)
                for c in affected}

    def priority(index):
        after = after_counts(index)
        freed = sum(int(active[c] > 0)-int(value > 0) for c, value in after.items())
        return -freed, ranks[index], index

    while len(order) < len(block.instructions):
        if perf_counter() >= deadline:
            raise BudgetExceeded("Ordered-alias research scheduling budget exhausted")
        now = len(output)
        expiring = next(iter(live), None)
        if expiring is not None:
            age = now-positions[expiring]
            if age > block.window:
                raise InfeasibleSchedule("Ordered-alias heuristic expired a live class; not a proof")
            if age != block.window:
                expiring = None
        selected, selected_key = None, None
        for offset,i in enumerate(ready):
            if offset%128==0 and perf_counter()>=deadline:
                raise BudgetExceeded("Ordered-alias ready scan budget exhausted")
            if expiring is not None and classes[i] != expiring and after_counts(i).get(expiring,active[expiring])!=0:
                continue
            key=priority(i)
            if selected_key is None or key<selected_key:selected,selected_key=i,key
        if expiring is not None:
            if selected is None:
                output.append({"id": now, "op": "COPY", "source": f"t#{block.window}"})
                positions[expiring] = now
                live.move_to_end(expiring)
                copies += 1
                stalled += 1
                if stalled >= block.window or copies > max(block.window, (block.window-1)*len(block.instructions)):
                    raise InfeasibleSchedule("Ordered-alias heuristic stalled; not a global infeasibility proof")
                continue
        if selected is None:
            raise InfeasibleSchedule("Ordered-alias heuristic has no ready instruction")
        index = selected
        node = block.instructions[index]
        tokens = [f"t#{now-positions[classes[source]]}" for source in node.args]
        if any(not 1 <= now-positions[classes[source]] <= block.window for source in node.args):
            raise InfeasibleSchedule("Ordered-alias input outside the legal reference window")
        row = {"id": now, "op": node.op}
        if node.reg is not None:
            row["reg"] = node.reg
        if node.op == "COPY":
            row["source"] = tokens[0]
        elif tokens:
            row["inputs"] = tokens
        output.append(row)
        order.append(index)
        ready.remove(index)
        stalled = 0
        for source in prepared.args_unique[index]:
            remaining[source] -= 1
            active[classes[source]] -= 1
        c = classes[index]
        active[c] += remaining[index]
        positions[c] = now
        for affected in set(classes[source] for source in node.args) | {c}:
            if active[affected] == 0:
                live.pop(affected, None)
        if active[c] > 0:
            live[c] = now
            live.move_to_end(c)
        peak = max(peak, len(live))
        for user in prepared.users[index]:
            pending[user] -= 1
            if pending[user] == 0:
                ready.add(user)
    total = sum(row["op"] == "COPY" for row in output)
    return {"block_id": block.block_id, "optimized_instructions": output, "stats": {
        "strategy": "alias_pressure", "original_instruction_count": len(order),
        "optimized_instruction_count": len(output), "inserted_copy_count": copies,
        "total_copy_count": total, "copy_ratio_output": total/len(output) if output else 0,
        "inserted_copy_ratio_original": copies/len(order) if order else 0,
        "elapsed_ms": (perf_counter()-started)*1000, "original_order": order,
        "bit_width": block.bit_width, "max_back_distance": block.window,
        "value_identity_model": "ordered_structural_arithmetic_aliases",
        "fixed_order_lower_bound_applicable": False,
        "alias_classes": len(set(classes)), "max_live_classes": peak,
        "scope": "explicit local pure arithmetic experiment; no GET/SET merging or deletion"}}
