"""Necessary capacity bound for a strictly screened mandatory arithmetic spine.

GET roots can be delayed/reordered; spine arithmetic itself is forced by data
edges. Distinct root identities must stay materialized between first and last
spine uses. This is a relaxed W-slot bound, not age-window sufficiency.
"""


def spine_capacity_bound(block):
    nodes=block.instructions
    if any(node.op not in ("GET","SET","ADD","MULW") for node in nodes):return None
    roots=[node.index for node in nodes if node.op=="GET"]
    stores=[node for node in nodes if node.op=="SET"]
    arithmetic=[node for node in nodes if node.op in ("ADD","MULW")]
    if len(stores)!=1 or not arithmetic:return None
    if len({nodes[index].reg for index in roots})!=len(roots):return None
    if stores[0].reg in {nodes[index].reg for index in roots}:return None
    if stores[0].args!=(arithmetic[-1].index,):return None
    root_set=set(roots)
    first,last={},{}
    for stage,node in enumerate(arithmetic):
        sources=set(node.args)
        if stage==0:
            if not sources or not sources<=root_set:return None
        else:
            previous=arithmetic[stage-1].index
            if previous not in sources or not (sources-{previous})<=root_set:return None
        for source in sources & root_set:
            first.setdefault(source,stage);last[source]=stage
    if set(first)!=root_set:return None  # Unused GETs require another model.
    # Since all non-root rows form this chain plus one store, no hidden consumers
    # can branch from an earlier spine output. Explicitly screen nonetheless.
    users={node.index:set() for node in nodes}
    for node in nodes:
        for source in set(node.args):users[source].add(node.index)
    for stage,node in enumerate(arithmetic):
        expected=arithmetic[stage+1].index if stage+1<len(arithmetic) else stores[0].index
        if users[node.index]!={expected}:return None
    born=[0]*len(arithmetic);died=[0]*len(arithmetic)
    for source in roots:born[first[source]]+=1;died[last[source]]+=1
    active=peak=0;critical_stage=None
    for stage in range(len(arithmetic)):
        active+=born[stage]
        before=active+int(stage>0)
        if before>peak:peak,critical_stage=before,stage
        active-=died[stage]
        after=active+1 # Spine result remains for its successor/store.
        if after>peak:peak,critical_stage=after,stage
    return {"kind":"mandatory_spine_root_interval_capacity","minimum_register_slots":peak,
            "window":block.window,"infeasible_under_model":peak>block.window,"critical_spine_stage":critical_stage,
            "root_count":len(roots),"spine_nodes":len(arithmetic),
            "scope":"one forced arithmetic spine; unique GET registers; one disjoint SET; each original node once; identity preserving COPY only; no alias folding/recompute/reread/spill",
            "argument":"first-to-last root use intervals are mandatory across fixed arithmetic spine cuts; include live prior/result spine value; relax physical age window to W freely retained slots"}
