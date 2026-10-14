"""Serialized spine-branch capacity DP and an independently checkable witness.

Only pure unique/disjoint GET/SET registers, disjoint arithmetic spines sharing
GET roots, every original row covered, and <=16 SET branches are accepted.
Choosing entire branches serially is a restricted policy, not general DAG
optimality. A physical COPY relay emitter constructs the actual witness.
"""
from collections import OrderedDict,deque
from time import perf_counter
from .model import BudgetExceeded,InfeasibleSchedule
from .sink_bounds import sink_spine_projections


def schedule_branches(block,prepared,*,time_budget_ms=100,max_branches=16):
    started=perf_counter();deadline=started+time_budget_ms/1000
    if prepared.block is not block:raise ValueError("PreparedGraph belongs to a different block")
    nodes=block.instructions
    projections=list(sink_spine_projections(block))
    stores=[node.index for node in nodes if node.op=="SET"]
    if not projections or len(projections)!=len(stores) or len(projections)>max_branches:
        raise InfeasibleSchedule("branch_dp requires at most 16 complete pure spine branches; no global proof")
    branches=[];covered=set();arithmetic_seen=set();membership={}
    for terminal,indices,_ in projections:
        arithmetic=[index for index in indices if nodes[index].op in ("ADD","MULW")]
        if arithmetic_seen & set(arithmetic):raise InfeasibleSchedule("branch_dp rejects shared arithmetic between spines")
        arithmetic_seen.update(arithmetic);covered.update(indices)
        spans={}
        for stage,index in enumerate(arithmetic):
            for source in prepared.args_unique[index]:
                if nodes[source].op=="GET":
                    spans.setdefault(source,[stage,stage])[1]=stage
        for source in spans:membership[source]=membership.get(source,0)+1
        branches.append({"terminal":terminal,"arithmetic":arithmetic,"spans":spans})
    if covered!=set(range(len(nodes))):raise InfeasibleSchedule("branch_dp rejects uncovered/dead original rows")
    shared={source:1<<offset for offset,source in enumerate(source for source,count in membership.items() if count>1)}
    branch_masks=[sum(shared[source] for source in branch["spans"] if source in shared) for branch in branches]
    count=len(branches);final=(1<<count)-1
    unions=[0]*(final+1)
    for mask in range(1,final+1):
        if mask%512==0 and perf_counter()>=deadline:raise BudgetExceeded("Branch DP preprocessing budget exhausted")
        bit=mask&-mask;unions[mask]=unions[mask^bit]|branch_masks[bit.bit_length()-1]
    cache={}
    def peak(done,branch_index):
        used=unions[done];pending_other=unions[final^(done|(1<<branch_index))]
        key=branch_index,used,pending_other
        if key in cache:return cache[key]
        active=(used&unions[final^done]).bit_count()
        births={};deaths={}
        for source,(first,last) in branches[branch_index]["spans"].items():
            bit=shared.get(source,0)
            if not bit or not used&bit:births[first]=births.get(first,0)+1
            if not bit or not pending_other&bit:deaths[last]=deaths.get(last,0)+1
        maximum=active
        for stage in sorted(set(births)|set(deaths)|{0}):
            active+=births.get(stage,0)
            maximum=max(maximum,active+int(stage>0))
            active-=deaths.get(stage,0)
            maximum=max(maximum,active+1)
        cache[key]=maximum
        return maximum
    queue=deque([0]);parents={0:None};explored=0;found=False
    while queue:
        if perf_counter()>=deadline:raise BudgetExceeded("Branch capacity DP time budget exhausted")
        done=queue.pop();explored+=1
        if done==final:found=True;break
        choices=[]
        for branch_index in range(count):
            bit=1<<branch_index
            if done&bit or (done|bit) in parents:continue
            if peak(done,branch_index)<=block.window:
                following=done|bit
                remaining=unions[final^following]
                retained=(unions[following]&remaining).bit_count()
                choices.append((retained,branch_index,following))
        for _,branch_index,following in sorted(choices,reverse=True):
            parents[following]=(done,branch_index);queue.append(following)
    if not found:raise InfeasibleSchedule("serialized_branch_order_capacity_infeasible; not general interleaved-DAG proof")
    branch_order=[];mask=final
    while mask:
        mask,index=parents[mask];branch_order.append(index)
    branch_order.reverse()
    planned=[];gets_done=set()
    for branch_index in branch_order:
        branch=branches[branch_index]
        for index in branch["arithmetic"]:
            missing=[source for source in prepared.args_unique[index] if nodes[source].op=="GET" and source not in gets_done]
            for source in sorted(missing,key=lambda source:(branch["spans"][source][1],source)):
                planned.append(source);gets_done.add(source)
            planned.append(index)
        planned.append(branch["terminal"])
    output=[];live=OrderedDict();positions=[-1]*len(nodes);remaining=list(prepared.remaining)
    prefix=copies=stalled=live_peak=0
    while prefix<len(planned):
        if perf_counter()>=deadline:raise BudgetExceeded("Branch witness emission budget exhausted")
        index=planned[prefix];node=nodes[index];now=len(output)
        if live:
            oldest=next(iter(live));age=now-positions[oldest]
            if age>block.window:raise InfeasibleSchedule("Branch witness live value expired")
            if age==block.window and not(oldest in prepared.args_unique[index] and remaining[oldest]==1):
                output.append({"id":now,"op":"COPY","source":f"t#{block.window}"})
                positions[oldest]=now;live.move_to_end(oldest);copies+=1;stalled+=1
                if stalled>=block.window or copies>block.window*max(1,len(nodes)):
                    raise InfeasibleSchedule("Branch relay policy did not progress; not global proof")
                continue
        row={"id":now,"op":node.op}
        if node.reg is not None:row["reg"]=node.reg
        if node.args:row["inputs"]=[f"t#{now-positions[source]}" for source in node.args]
        output.append(row);positions[index]=now
        for source in prepared.args_unique[index]:
            remaining[source]-=1
            if remaining[source]==0:live.pop(source,None)
        if remaining[index]:live[index]=now
        live_peak=max(live_peak,len(live));prefix+=1;stalled=0
    return {"block_id":block.block_id,"optimized_instructions":output,"stats":{
        "strategy":"branch_dp","original_instruction_count":len(nodes),"optimized_instruction_count":len(output),
        "inserted_copy_count":copies,"total_copy_count":copies,"copy_ratio_output":copies/len(output),
        "inserted_copy_ratio_original":copies/len(nodes),"original_order":planned,
        "bit_width":block.bit_width,"max_back_distance":block.window,"elapsed_ms":(perf_counter()-started)*1000,
        "branch_dp":{"branches":count,"explored_masks":explored,"capacity_cache_entries":len(cache),
                     "peak_live_values":live_peak,"terminal_order":[branches[index]["terminal"] for index in branch_order],
                     "scope":"serialized disjoint arithmetic spines sharing GET roots; not global COPY optimum or general infeasibility"}}}
