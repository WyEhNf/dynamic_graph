"""O(n + inserted COPY) emission for a strictly screened postorder forest.

This preserves the size/pressure policy's emission on complete pure forests:
every non-SET has exactly one distinct consumer, SET is a data leaf, no register
hazards remain, and postorder completes a subtree before starting its sibling.
The next planned compute is always the highest net-release ready instruction.
Dead data nodes or shared values must use the general ready scheduler instead.
"""
from collections import OrderedDict
from time import perf_counter

from .bounds import forest_capacity_bound
from .model import BudgetExceeded, InfeasibleSchedule


def eligible(block, prepared):
    if prepared.block is not block: raise ValueError("Prepared graph belongs to a different block")
    cached=getattr(prepared,"complete_forest_eligibility",None)
    if cached is not None:return cached
    certificate=forest_capacity_bound(block)
    result=bool(certificate is not None and all(
        prepared.remaining[node.index]==(0 if node.op=="SET" else 1) for node in block.instructions))
    prepared.complete_forest_eligibility=result
    return result


def window_work_order(block,prepared):
    """Work-first where either child order fits relaxed W-slot capacity.

This is not a COPY optimality theorem: the physical age-window constraint is
stricter. Holding h ancestor results leaves W-h slots. If both child orders
fit, larger work first shortens the first result's waiting interval.
"""
    if not eligible(block,prepared):raise ValueError("Complete pure forest required")
    _,need=prepared.demand(float("inf"),size_aware=True)
    work=[1]*len(block.instructions)
    for node in block.instructions:
        work[node.index]=1+sum(work[source] for source in prepared.args_unique[node.index])
    order=[]
    roots=[node.index for node in block.instructions if node.op=="SET"]
    for root in roots:
        stack=[(root,0,False)]
        while stack:
            index,held,finish=stack.pop()
            if finish:order.append(index);continue
            if need[index]+held>block.window:
                raise InfeasibleSchedule("Forest relaxed register capacity exceeded; restricted model only")
            sources=list(prepared.args_unique[index])
            if len(sources)==2 and max(need[source] for source in sources)+held+1<=block.window:
                sources.sort(key=lambda source:(-work[source],-need[source],source))
            else:
                sources.sort(key=lambda source:(-need[source],-work[source],source))
            stack.append((index,held,True))
            for offset,source in reversed(list(enumerate(sources))):
                stack.append((source,held+offset,False))
    return order


def emit_forest(block,prepared,*,time_budget_ms=None,max_copy_factor=None,work_first=False,policy="size_pressure"):
    started=perf_counter()
    deadline=started+time_budget_ms/1000 if time_budget_ms is not None else float("inf")
    if prepared.block is not block: raise ValueError("Prepared graph belongs to a different block")
    if not eligible(block,prepared): raise ValueError("Complete, unshared, pure GET/SET forest required")
    if policy not in ("pressure","demand","size_pressure"):raise ValueError("Unsupported direct forest priority")
    ranks,_=prepared.demand(deadline,size_aware=policy=="size_pressure" or work_first)
    nodes,count=block.instructions,len(block.instructions)
    if work_first:order=window_work_order(block,prepared)
    else:
        order=[0]*count
        for index,rank in enumerate(ranks):order[rank]=index
    output,live,positions=[],OrderedDict(),[-1]*count
    copies=prefix=stalled=live_peak=0
    copy_factor=block.window-1 if max_copy_factor is None else max_copy_factor
    if type(copy_factor) is not int or copy_factor<1:raise ValueError("Positive integer COPY factor required")
    limit=max(block.window,copy_factor*max(1,count))
    while prefix<count:
        if perf_counter()>=deadline:raise BudgetExceeded("Forest emission time budget exhausted")
        node=nodes[order[prefix]]
        now=len(output)
        if live:
            oldest=next(iter(live))
            age=now-positions[oldest]
            if age>block.window:raise InfeasibleSchedule("Forest live value expired")
            if age==block.window and oldest not in prepared.args_unique[node.index]:
                output.append({"id":now,"op":"COPY","source":f"t#{block.window}"})
                positions[oldest]=now;live.move_to_end(oldest)
                copies+=1;stalled+=1
                if stalled>=block.window or copies>limit:
                    raise InfeasibleSchedule("Forest greedy relay cannot progress; not global infeasibility")
                continue
        row={"id":now,"op":node.op}
        if node.reg is not None:row["reg"]=node.reg
        if node.args:row["inputs"]=[f"t#{now-positions[source]}" for source in node.args]
        output.append(row);positions[node.index]=now
        for source in prepared.args_unique[node.index]:live.pop(source)
        if prepared.remaining[node.index]:live[node.index]=now
        live_peak=max(live_peak,len(live));prefix+=1;stalled=0
    return {"block_id":block.block_id,"optimized_instructions":output,"stats":{
        "strategy":"forest_work" if work_first else policy,"implementation":"complete_forest_postorder",
        "original_instruction_count":count,"optimized_instruction_count":len(output),
        "inserted_copy_count":copies,"total_copy_count":copies,
        "copy_ratio_output":copies/len(output) if output else 0,
        "inserted_copy_ratio_original":copies/count if count else 0,
        "bit_width":block.bit_width,"max_back_distance":block.window,
        "original_order":order,"elapsed_ms":(perf_counter()-started)*1000,
        "incremental":{"max_live_values":live_peak,"heap_pushes":0,
                       "shared_preprocess":True,"rank_compute_ms":prepared.rank_compute_ms}}}
