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
