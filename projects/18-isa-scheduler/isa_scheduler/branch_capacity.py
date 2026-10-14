"""Independent age-free capacity oracle for disjoint arithmetic spines.

All branch interleavings are covered. Pure unique/disjoint GET/SET registers
allow delaying each GET to its first consumer: moving a read later never raises
logical live capacity. GET-only intermediate states can therefore be contracted.
This is a necessary relaxation, not a physical distance-window COPY oracle.
"""
from collections import deque
from time import perf_counter
from .model import parse_block
from .sink_bounds import sink_spine_projections


def branch_capacity_oracle(data, *, time_budget_ms=1000, max_states=200000):
    if time_budget_ms<=0 or max_states<1:raise ValueError("Positive time/state budgets required")
    started=perf_counter();deadline=started+time_budget_ms/1000
    block=parse_block(data);nodes=block.instructions
    projections=list(sink_spine_projections(block))
    stores=[node.index for node in nodes if node.op=="SET"]
    if not projections or len(projections)!=len(stores):
        raise ValueError("Requires complete pure independent arithmetic spines")
    branches=[];seen=set();covered=set();root_spans={}
    for terminal,indices,_ in projections:
        arithmetic=[i for i in indices if nodes[i].op in ("ADD","MULW")]
        if seen&set(arithmetic):raise ValueError("Shared arithmetic is unsupported")
        seen.update(arithmetic);covered.update(indices);spans={}
        for stage,index in enumerate(arithmetic):
            for source in set(nodes[index].args):
                if nodes[source].op=="GET":spans.setdefault(source,[stage,stage])[1]=stage
        branch=len(branches)
        for source,span in spans.items():root_spans.setdefault(source,[]).append((branch,*span))
        branches.append((arithmetic,terminal,spans))
    if covered!=set(range(len(nodes))):raise ValueError("Uncovered/dead original rows")
    final=tuple(len(arithmetic)+1 for arithmetic,_,_ in branches)
    initial=(0,)*len(branches);pending=deque([initial]);parents={initial:None}
    explored=0;found=False;boundary_peak=0;reason=None
    while pending:
        if explored>=max_states:reason="state_budget_exhausted";break
        if perf_counter()>=deadline:reason="time_budget_exhausted";break
        state=pending.pop();explored+=1
        if state==final:found=True;break
        produced={source for source,spans in root_spans.items() if any(state[b]>first for b,first,_ in spans)}
        alive={source for source in produced if any(state[b]<=last for b,_,last in root_spans[source])}
        accum=sum(0<p<len(branches[b][0])+1 for b,p in enumerate(state))
        boundary_peak=max(boundary_peak,len(alive)+accum)
        choices=[]
        for b,position in enumerate(state):
            arithmetic,terminal,spans=branches[b]
            if position>=len(arithmetic)+1:continue
            following=list(state);following[b]+=1;following=tuple(following)
            if following in parents:continue
            if position==len(arithmetic):
                peak=len(alive)+accum
            else:
                index=arithmetic[position]
                missing=[source for source in set(nodes[index].args) if nodes[source].op=="GET" and source not in produced]
                before=len(alive)+accum+len(missing)
                after_roots=sum(any(following[j]<=last for j,_,last in root_spans[source]) for source in alive|set(missing))
                after_accum=sum(0<p<len(branches[j][0])+1 for j,p in enumerate(following))
                peak=max(before,after_roots+after_accum)
            if peak<=block.window:choices.append((position==len(arithmetic),b,following))
        # Finish an available store first; ordering changes cost, never coverage.
        for _,b,following in sorted(choices):
            parents[following]=(state,b);pending.append(following)
    order=[]
    if found:
        state=final
        while state!=initial:
            previous,b=parents[state];position=previous[b]
            order.append(branches[b][1] if position==len(branches[b][0]) else branches[b][0][position]);state=previous
        order.reverse();emitted=set();plan=[]
        for index in order:
            for source in sorted(set(nodes[index].args)):
                if nodes[source].op=="GET" and source not in emitted:plan.append(source);emitted.add(source)
            plan.append(index)
    else:plan=None
    return {"status":"relaxed_feasible" if found else reason or "relaxed_proven_infeasible",
            "original_order":plan,"explored_states":explored,"stored_states":len(parents),
            "branches":len(branches),"window":block.window,"boundary_peak_seen":boundary_peak,
            "elapsed_ms":(perf_counter()-started)*1000,
            "scope":"all interleavings of disjoint arithmetic spines sharing pure GET roots; just-in-time GET contraction; age-free necessary relaxation; identity-preserving single emission, COPY-only"}
