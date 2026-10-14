"""Independent completed-mask DP in a freely retained value-slot relaxation.

It ignores physical output ages and all inserted COPY actions. Live logical
identities are determined solely by completed original nodes and remaining
consumers. Infeasibility here implies infeasibility of the stricter age-window
model, but feasibility is only a relaxed witness, not a runnable ISA schedule.
"""
from collections import deque
from time import perf_counter
from .model import BudgetExceeded


def capacity_oracle(block,capacity=None,*,max_nodes=20,max_states=200000,time_budget_ms=1000,depth_first=False):
    started=perf_counter();deadline=started+time_budget_ms/1000
    nodes=block.instructions;n=len(nodes)
    if n>max_nodes:raise BudgetExceeded(f"Relaxed capacity oracle limited to {max_nodes} nodes")
    capacity=block.window if capacity is None else capacity
    if type(capacity) is not int or capacity<1 or max_states<1 or time_budget_ms<=0:raise ValueError("Positive budgets and capacity required")
    dependencies=[];consumers=[0]*n
    for node in nodes:
        dependencies.append(sum(1<<source for source in set(node.args)|set(node.order_deps)))
        for source in set(node.args):consumers[source]|=1<<node.index
    final=(1<<n)-1
    queue=deque([(0,0)]);seen={0};parents={};explored=0
    feasible=False;terminal=None
    while queue:
        if perf_counter()>=deadline or explored>=max_states:raise BudgetExceeded("Relaxed capacity DP budget exhausted")
        done,live=queue.pop() if depth_first else queue.popleft();explored+=1
        if done==final:feasible=True;terminal=done;break
        undone=final^done
        while undone:
            bit=undone&-undone;undone^=bit;index=bit.bit_length()-1
            if dependencies[index]&done!=dependencies[index]:continue
            following=done|bit
            if following in seen:continue
            next_live=live
            for source in set(nodes[index].args):
                if not consumers[source]&~following:next_live&=~(1<<source)
            if consumers[index]&~following:next_live|=bit
            if next_live.bit_count()<=capacity:
                seen.add(following);parents[following]=(done,index);queue.append((following,next_live))
    order=[]
    if feasible:
        while terminal:
            terminal,index=parents[terminal];order.append(index)
        order.reverse()
    return {"outcome":"feasible_relaxed_capacity_only" if feasible else "proven_infeasible_relaxed_capacity_under_model",
            "capacity":capacity,"node_count":n,"explored_states":explored,"reached_states":len(seen),
            "elapsed_ms":(perf_counter()-started)*1000,"relaxed_original_order":order,
            "proof_scope":"completed original identities once; no alias folding/recompute/reread/spill; freely retained slots ignore physical ages; feasible relaxation is not ISA feasibility"}
