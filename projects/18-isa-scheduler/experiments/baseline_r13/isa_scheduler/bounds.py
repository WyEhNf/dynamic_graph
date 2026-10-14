"""Necessary relaxed register-capacity bound for a strictly screened forest.

The age window is stricter than a machine with W freely retained value slots.
For an unshared expression tree, Sethi-style demand is a lower bound in that
relaxed machine. COPY does not increase its capacity. This certifies only the
single-emission, identity-preserving, COPY-only model, never the general task
with recomputation, alias folding or external spill.
"""


def forest_capacity_bound(block):
    nodes = block.instructions
    if any(node.op not in ("GET", "SET", "ADD", "MULW") for node in nodes):
        return None
    get_regs = [node.reg for node in nodes if node.op == "GET"]
    set_regs = [node.reg for node in nodes if node.op == "SET"]
    if (len(get_regs) != len(set(get_regs)) or len(set_regs) != len(set(set_regs))
            or set(get_regs) & set(set_regs)):
        return None
    uses = [0] * len(nodes)
    for node in nodes:
        for source in set(node.args):
            uses[source] += 1
            if uses[source] > 1:
                return None  # Tree recurrence is unsound on shared DAGs.
    demand = [1] * len(nodes)
    for node in nodes:
        children = sorted((demand[source] for source in set(node.args)), reverse=True)
        demand[node.index] = max((value + offset for offset, value in enumerate(children)), default=1)
    required = max(demand, default=0)
    return {"kind": "unshared_pure_forest_relaxed_capacity", "minimum_register_slots": required,
            "window": block.window, "infeasible_under_model": required > block.window,
            "scope": "distinct GET/SET registers; unshared data forest; each original node once; COPY only; no alias folding, recomputation or spill",
            "argument": "relax age restriction to W freely retained value slots; tree demand exceeds W"}


def fixed_order_copy_bound(block, original_order):
    """Necessary COPY counts for this order, not for all possible reorderings.

    Every logical original value retains a distinct latest physical output in
    the identity-preserving model. With span L and c own relays, L+c <= (c+1)W
    gives c >= ceil((L-W)/(W-1)). For k values persistent across L original
    steps, their distinct ages sum increases by k per original step; a relay
    reduces it by at most W-k. The age-sum range is at most k(W-k).
    """
    nodes, window = block.instructions, block.window
    count = len(nodes)
    if len(original_order) != count or set(original_order) != set(range(count)):
        raise ValueError("Order trace must emit every original node once")
    ranks = [0]*count
    for rank,index in enumerate(original_order):ranks[index]=rank
    last = [-1]*count
    for node in nodes:
        if any(ranks[source] >= ranks[node.index] for source in set(node.args)|set(node.order_deps)):
            raise ValueError("Order trace is not topologically legal")
        for source in set(node.args):last[source]=max(last[source],ranks[node.index])
    individual = sum(max(0,(last[i]-ranks[i]-window+window-2)//(window-1))
                     for i in range(count) if last[i]>=0)
    candidates = sorted((i for i in range(count) if last[i]>=0),
                        key=lambda i:last[i]-ranks[i],reverse=True)
    latest_birth, earliest_death, persistent, best_k = -1,count,0,0
    for k,index in enumerate(candidates[:max(0,window-1)],start=1):
        latest_birth=max(latest_birth,ranks[index]);earliest_death=min(earliest_death,last[index])
        steps=max(0,earliest_death-latest_birth-1)
        denominator=window-k
        required=max(0,(k*steps-k*denominator+denominator-1)//denominator)
        if required>persistent:persistent,best_k=required,k
    events=[0]*(count+1)
    for index,death in enumerate(last):
        if death>=0:
            events[ranks[index]]+=1;events[death]-=1
    live=peak=0
    for delta in events:live+=delta;peak=max(peak,live)
    return {"copy_lower_bound":max(individual,persistent),"individual_sum":individual,
            "persistent_prefix_bound":persistent,"persistent_values":best_k,
            "fixed_order_peak_live":peak,
            "scope":"this original-node order only; single emission; identity preserving; COPY only; no alias folding/recompute/spill"}
