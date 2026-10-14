"""Global COPY necessary lower bound on a strictly screened forced pure spine.

Unlike fixed-order bounds, only forced arithmetic order is used. GET births
may be delayed and interleaved arbitrarily. Identity-preserving, original-once
COPY-only scope; no aliases/recomputation/rereads/spill. This is a lower bound,
not a scheduler and not an official scoring rule.
"""
from .spine_bounds import spine_capacity_bound


def spine_copy_bound(block):
    screen=spine_capacity_bound(block)
    if screen is None or screen['infeasible_under_model']:return None
    nodes=block.instructions;roots={node.index for node in nodes if node.op=='GET'}
    arithmetic=[node for node in nodes if node.op in ('ADD','MULW')]
    first={};last={}
    for stage,node in enumerate(arithmetic):
        for source in set(node.args)&roots:first.setdefault(source,stage);last[source]=stage
    candidates=sorted(roots,key=lambda source:(last[source]-first[source],-first[source],source),reverse=True)
    start=-1;end=len(arithmetic);bound=0;best=None
    for count,source in enumerate(candidates[:block.window-1],1):
        start=max(start,first[source]);end=min(end,last[source]);steps=max(0,end-start-1)
        slack=block.window-count
        required=max(0,(count*steps-count*slack+slack-1)//slack)
        if required>bound:
            bound=required;best={'roots':candidates[:count],'after_first_use_stage':start,
                                'before_last_use_stage':end,'forced_inner_steps':steps,
                                'persistent_identities':count,'age_sum_range':count*slack}
    return {'kind':'forced_spine_persistent_age_sum','copy_lower_bound':bound,'window':block.window,
            'witness':best,'root_count':len(roots),'spine_nodes':len(arithmetic),
            'scope':'all topological orders of this screened forced pure spine; distinct original identities once; COPY-only; no alias/recompute/reread/spill',
            'argument':'k root identities persist across L forced arithmetic steps; each step adds k to age sum; each COPY reduces it by at most W-k; total range <=k(W-k)'}
