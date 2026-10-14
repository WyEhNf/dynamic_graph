"""Incremental liveness and demand-driven scheduling for bounded-distance ISA.

The Sethi-style static rank is a heuristic on shared DAGs and finite age windows,
not a claim of tree-optimality for this different machine model. No algebraic
rewrites, duplicated GETs, instruction deletion or reassociation are performed.
"""
from collections import OrderedDict
import heapq
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule


def demand_ranks(nodes, deps, users, size_aware=False):
    need = [1] * len(nodes)
    work = [1] * len(nodes)
    for node in nodes:
        weights = sorted((need[a] for a in set(node.args)), reverse=True)
        need[node.index] = max((weight + offset for offset, weight in enumerate(weights)), default=1)
        if size_aware:
            # Exact subtree size on unshared forests; clipped heuristic on DAGs.
            work[node.index] = min(len(nodes),1+sum(work[a] for a in set(node.args)))
    priority = lambda i: (-need[i], -work[i] if size_aware else 0, i)
    sinks = sorted((i for i, children in enumerate(users) if not children), key=priority)
    status, order = [0] * len(nodes), []
    for sink in sinks + list(range(len(nodes))):
        if status[sink]:
            continue
        stack = [(sink, False)]
        while stack:
            index, finish = stack.pop()
            if finish:
                if status[index] != 2:
                    status[index] = 2
                    order.append(index)
                continue
            if status[index]:
                continue
            status[index] = 1
            stack.append((index, True))
            children = sorted(deps[index], key=priority)
            stack.extend((child, False) for child in reversed(children) if not status[child])
    ranks = [0] * len(nodes)
    for rank, index in enumerate(order):
        ranks[index] = rank
    return ranks, need


class PreparedGraph:
    """Shared static structure only; every scheduling run owns its mutable state."""
    def __init__(self, block, time_budget_ms=None):
        started = perf_counter()
        deadline = started + time_budget_ms/1000 if time_budget_ms is not None else float("inf")
        nodes = block.instructions
        count = len(nodes)
        deps, users, data_users = [], [[] for _ in nodes], [[] for _ in nodes]
        remaining, args_unique = [0]*count, []
        for node in nodes:
            if node.index % 128 == 0 and perf_counter() >= deadline:
                raise BudgetExceeded("Shared graph preprocessing time budget exhausted")
            args = frozenset(node.args)
            args_unique.append(args)
            dependencies = args | frozenset(node.order_deps)
            deps.append(dependencies)
            for dependency in dependencies:
                users[dependency].append(node.index)
            for source in args:
                data_users[source].append(node.index)
                remaining[source] += 1
        height = [1]*count
        for index in range(count-1,-1,-1):
            height[index] += max((height[u] for u in users[index]),default=0)
        fixed_remaining, live, peak = remaining.copy(), 0, 0
        for node in nodes:
            for source in args_unique[node.index]:
                fixed_remaining[source] -= 1
                if fixed_remaining[source] == 0:
                    live -= 1
            if remaining[node.index] > 0:
                live += 1
            peak = max(peak,live)
        self.block = block
        self.deps, self.args_unique = tuple(deps), tuple(args_unique)
        self.users = tuple(tuple(row) for row in users)
        self.data_users = tuple(tuple(row) for row in data_users)
        self.remaining, self.pending = tuple(remaining), tuple(len(d) for d in deps)
        self.initial_freed=tuple(sum(remaining[source]==1 for source in args) for args in args_unique)
        self.height, self.original_peak_live = tuple(height), peak
        self.ranks = self.need = None
        self.size_ranks = self.size_need = None
        self.preprocess_ms = (perf_counter()-started)*1000
        self.rank_compute_ms = 0.0

    def demand(self, deadline, size_aware=False):
        if size_aware:
            if self.size_ranks is None:
                if perf_counter() >= deadline: raise BudgetExceeded("Size-aware demand preparation budget exhausted")
                started=perf_counter()
                ranks,need=demand_ranks(self.block.instructions,self.deps,self.users,True)
                self.size_ranks,self.size_need=tuple(ranks),tuple(need)
                self.rank_compute_ms+=(perf_counter()-started)*1000
            return self.size_ranks,self.size_need
        if self.ranks is None:
            if perf_counter() >= deadline:
                raise BudgetExceeded("Static demand preparation time budget exhausted")
            started = perf_counter()
            ranks, need = demand_ranks(self.block.instructions,self.deps,self.users)
            self.ranks, self.need = tuple(ranks), tuple(need)
            self.rank_compute_ms = (perf_counter()-started)*1000
        return self.ranks, self.need


def schedule_incremental(block, policy="pressure", *, time_budget_ms=None, max_copy_factor=None, prepared=None):
    if policy not in ("pressure", "demand", "incremental", "stable_fast", "ready_fast", "affinity", "deadline", "age_first", "size_pressure"):
        raise ValueError("Unknown incremental policy")
    started = perf_counter()
    deadline = started + time_budget_ms / 1000 if time_budget_ms is not None else float("inf")
    reuse = prepared is not None
    prepared = prepared or PreparedGraph(block,time_budget_ms)
    if prepared.block is not block:
        raise ValueError("Prepared graph belongs to a different block instance")
    nodes, count = block.instructions, len(block.instructions)
    deps, users, data_users = prepared.deps, prepared.users, prepared.data_users
    args_unique, height = prepared.args_unique, prepared.height
    remaining, pending = list(prepared.remaining), list(prepared.pending)
    freed_count=list(prepared.initial_freed)
    if policy in ("stable_fast", "ready_fast"):
        ranks, need = list(range(count)), [1] * count
    else:
        ranks, need = prepared.demand(deadline,size_aware=policy=="size_pressure")
    done, ready, versions = [False] * count, [False] * count, [0] * count
    sole = [u[0] if len(u) == 1 else None for u in data_users]
    positions = [-1] * count
    affinity = [0] * count
    # Only currently materialized values with future data uses live here.
    # Insertion order follows latest output position: expiry is an O(1) query.
    live = OrderedDict()
    ready_heap = []
    heap_pushes = live_high_water = copies = completed = stalled = 0
    # Successful progress permits at most W-1 relays before each original row.
    # A fixed default 8*n guard incorrectly rejects high-pressure W=32 inputs.
    # Explicit user factors retain their earlier stricter guard semantics.
    copy_factor=block.window-1 if max_copy_factor is None else max_copy_factor
    if type(copy_factor) is not int or copy_factor<1:raise ValueError("Positive integer COPY factor required")
    copy_limit = max(block.window, copy_factor * max(count, 1))
    output, original_order = [], []

    def key(index):
        if policy == "stable_fast":
            return (index,)
        freed = freed_count[index]
        if policy == "ready_fast":
            # now - min(position) is the legacy oldest-operand score. A GET
            # has age zero, so infinity preserves its ordering against operands.
            oldest_position = min((positions[a] for a in args_unique[index]), default=float("inf"))
            return -freed, oldest_position, -height[index], index
        net = freed - int(remaining[index] > 0)
        if policy in ("deadline", "age_first"):
            oldest_position = min((positions[a] for a in args_unique[index]), default=float("inf"))
            if policy == "age_first":
                return int(nodes[index].op == "GET"), oldest_position, -net, ranks[index], index
            return -net, int(nodes[index].op == "GET"), oldest_position, -affinity[index], ranks[index], index
        if policy == "affinity":
            # Prefer finishing ready computations, then materialize inputs whose
            # direct co-operands already live. This can group shared-root uses.
            return -net, int(nodes[index].op == "GET"), -affinity[index], ranks[index], index
        if policy == "demand":
            return ranks[index], -net, index
        if policy in ("pressure", "size_pressure"):
            return -net, ranks[index], -need[index], index
        return -freed, -height[index], ranks[index], index

    def enqueue(index):
        nonlocal heap_pushes
        versions[index] += 1
        heapq.heappush(ready_heap, (key(index), index, versions[index]))
        heap_pushes += 1

    for index, degree in enumerate(pending):
        if degree == 0:
            ready[index] = True
            enqueue(index)
    while completed < count:
        if perf_counter() >= deadline:
            raise BudgetExceeded("Incremental scheduling time budget exhausted")
        now = len(output)
        expiring = None
        if live:
            oldest = next(iter(live))
            age = now - positions[oldest]
            if age > block.window:
                raise InfeasibleSchedule("Incremental live value expired")
            if age == block.window:
                expiring = oldest
        index = None
        stable_candidate = None
        if policy == "stable_fast":
            while ready_heap:
                _, candidate, version = ready_heap[0]
                if ready[candidate] and version == versions[candidate]:
                    stable_candidate = candidate
                    break
                heapq.heappop(ready_heap)
        if expiring is not None:
            consumer = sole[expiring]
            if (remaining[expiring] == 1 and consumer is not None and ready[consumer]
                    and (policy != "stable_fast" or stable_candidate == consumer)):
                index = consumer
            else:
                output.append({"id": now, "op": "COPY", "source": f"t#{block.window}"})
                positions[expiring] = now
                live.move_to_end(expiring)
                copies += 1
                stalled += 1
                if stalled >= block.window or copies > copy_limit:
                    raise InfeasibleSchedule("Incremental heuristic cannot progress; not a global infeasibility proof")
                continue
        else:
            while ready_heap:
                old_key, candidate, version = heapq.heappop(ready_heap)
                if ready[candidate] and version == versions[candidate]:
                    # COPY can only make the position term younger (worse).
                    # Lazy repair of an over-prioritized key is therefore safe;
                    # last-use improvements are eagerly enqueued above.
                    if policy in ("ready_fast", "deadline", "age_first") and old_key != key(candidate):
                        enqueue(candidate)
                        continue
                    index = candidate
                    break
        if index is None:
            raise InfeasibleSchedule("No incremental ready instruction")
        node = nodes[index]
        tokens = [f"t#{now - positions[source]}" for source in node.args]
        row = {"id": now, "op": node.op}
        if node.reg is not None:
            row["reg"] = node.reg
        if node.op == "COPY":
            row["source"] = tokens[0]
        elif tokens:
            row["inputs"] = tokens
        output.append(row)
        original_order.append(index)
        positions[index] = now
        done[index], ready[index] = True, False
        completed += 1
        stalled = 0
        for source in args_unique[index]:
            remaining[source] -= 1
            if remaining[source] == 0:
                live.pop(source, None)
                sole[source] = None
            elif remaining[source] == 1:
                consumer = next(u for u in data_users[source] if not done[u])
                sole[source] = consumer
                # This source transitions to its sole remaining consumer once.
                # Duplicate operands are already collapsed by args_unique.
                freed_count[consumer]+=1
                if ready[consumer]:
                    enqueue(consumer)
        if remaining[index] > 0:
            live[index] = now
            if policy in ("affinity", "deadline"):
                for user in data_users[index]:
                    for partner in args_unique[user] - {index}:
                        if not done[partner]:
                            affinity[partner] += 1
                            if ready[partner]:
                                enqueue(partner)
        live_high_water = max(live_high_water, len(live))
        for user in users[index]:
            pending[user] -= 1
            if pending[user] == 0:
                ready[user] = True
                enqueue(user)
    total_copies = sum(row["op"] == "COPY" for row in output)
    return {"block_id": block.block_id, "optimized_instructions": output, "stats": {
        "strategy": policy, "original_instruction_count": count,
        "optimized_instruction_count": len(output), "inserted_copy_count": copies,
        "total_copy_count": total_copies,
        "copy_ratio_output": total_copies / len(output) if output else 0.0,
        "inserted_copy_ratio_original": copies / count if count else 0.0,
        "elapsed_ms": (perf_counter() - started) * 1000,
        "bit_width": block.bit_width, "max_back_distance": block.window,
        "original_order": original_order,
        "incremental": {"max_live_values": live_high_water, "heap_pushes": heap_pushes,
                        "dependency_edges": sum(len(d) for d in deps), "rank": "Sethi-style demand heuristic",
                        "shared_preprocess": reuse, "preprocess_ms": prepared.preprocess_ms,
                        "rank_compute_ms": prepared.rank_compute_ms,
                        "original_order_peak_live": prepared.original_peak_live},
    }}
