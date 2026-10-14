"""Bounded serialized-branch beam with actual greedy COPY costs and root ages.

Pure unique/disjoint GET/SET, disjoint arithmetic spines and <=16 branches only.
This is a restricted ordering heuristic, not complete ISA code generation.
Every original is retained once; ordered arithmetic/register reads preserved.
"""
from collections import Counter,OrderedDict
from time import perf_counter
from .model import BudgetExceeded,InfeasibleSchedule
from .sink_bounds import sink_spine_projections
from .branch_dp import schedule_branches
from .local_order import emit_order
from .verify import VerificationContext


def _branches(block,prepared):
    nodes=block.instructions;projections=list(sink_spine_projections(block))
    if not projections or len(projections)!=sum(node.op=='SET' for node in nodes) or len(projections)>16:
        raise InfeasibleSchedule('branch_copy requires <=16 complete pure spine branches; no global proof')
    branches=[];covered=set();arithmetic_seen=set()
    for terminal,indices,_ in projections:
        arithmetic=[index for index in indices if nodes[index].op in ('ADD','MULW')]
        if arithmetic_seen.intersection(arithmetic):raise InfeasibleSchedule('branch_copy rejects shared arithmetic')
        arithmetic_seen.update(arithmetic);covered.update(indices)
        roots=Counter(source for index in arithmetic for source in prepared.args_unique[index] if nodes[source].op=='GET')
        branches.append({'terminal':terminal,'arithmetic':arithmetic,'roots':roots})
    unused=sorted(set(range(len(nodes)))-covered)
    if any(nodes[index].op!='GET' for index in unused):raise InfeasibleSchedule('branch_copy rejects uncovered computation')
    return branches,unused


def _transition(block,prepared,branches,done,index,ages,deadline,cutoff):
    nodes=block.instructions;branch=branches[index]
    remaining=Counter()
    produced=set()
    for offset,other in enumerate(branches):
        if done>>offset&1:produced.update(other['roots'])
        else:remaining.update(other['roots'])
    for value in branch['arithmetic']:remaining[value]=prepared.remaining[value]
    remaining[branch['terminal']]=0
    positions={source:-age for source,age in ages}
    live=OrderedDict((source,position) for source,position in sorted(positions.items(),key=lambda row:row[1]))
    now=copies=steps=stalled=0
    def issue(value):
        nonlocal now,copies,steps,stalled
        args=prepared.args_unique[value]
        while True:
            steps+=1
            if steps%64==1 and perf_counter()>=deadline:raise BudgetExceeded('Branch COPY beam transition budget exhausted')
            if not live:break
            oldest=next(iter(live));age=now-positions[oldest]
            if age>block.window:return False
            if age<block.window or oldest in args and remaining[oldest]==1:break
            positions[oldest]=now;live.move_to_end(oldest);now+=1;copies+=1;stalled+=1
            if stalled>=block.window or copies>=cutoff:return False
        if any(source not in positions or not 1<=now-positions[source]<=block.window for source in args):return False
        positions[value]=now;now+=1
        for source in args:
            remaining[source]-=1
            if not remaining[source]:live.pop(source,None)
        if remaining[value]:live[value]=now-1
        stalled=0;return True
    spans={}
    for stage,value in enumerate(branch['arithmetic']):
        for source in prepared.args_unique[value]:
            if nodes[source].op=='GET':spans[source]=stage
    for value in branch['arithmetic']:
        missing=[source for source in prepared.args_unique[value] if nodes[source].op=='GET' and source not in positions]
        for source in sorted(missing,key=lambda source:(spans[source],source)):
            if source in produced:return None
            if not issue(source):return None
            produced.add(source)
        if not issue(value):return None
    if not issue(branch['terminal']):return None
    # Only shared GET identities can survive an entire pure spine branch.
    if any(nodes[source].op!='GET' for source in live):raise AssertionError('Non-root branch frontier')
    return copies,tuple(sorted((source,now-positions[source])for source in live))


def schedule_branch_copy(data,block,prepared,*,time_budget_ms=250,beam_width=16,max_states=4096):
    if time_budget_ms<=0 or beam_width<1 or max_states<1:raise ValueError('Positive branch beam budgets required')
    if prepared.block is not block:raise ValueError('PreparedGraph belongs to another block')
    started=perf_counter();deadline=started+time_budget_ms/1000
    branches,unused=_branches(block,prepared);context=VerificationContext(data)
    best=None;best_cost=float('inf');baseline_error=None
    # A verified old capacity-first order remains available even if the new
    # quality search cannot complete. Its budget is part of the same total.
    try:
        candidate=schedule_branches(block,prepared,time_budget_ms=max(.001,(deadline-perf_counter())*1000))
        context.check(candidate);best=candidate;best_cost=candidate['stats']['inserted_copy_count']
    except (InfeasibleSchedule,BudgetExceeded) as exc:baseline_error=str(exc)
    frontier=[(0,0,(),())];expanded=transitions=pruned=0;outcome='beam_complete_restricted_neighborhood'
    try:
        for depth in range(len(branches)) if best_cost else ():
            following={}
            for cost,done,ages,path in frontier:
                if perf_counter()>=deadline:raise BudgetExceeded('Branch COPY beam time budget exhausted')
                if expanded>=max_states:outcome='state_budget_retained';raise BudgetExceeded(outcome)
                expanded+=1
                for index in range(len(branches)):
                    if done>>index&1:continue
                    transitions+=1
                    transition=_transition(block,prepared,branches,done,index,ages,deadline,best_cost-cost)
                    if transition is None:continue
                    extra,after=transition;next_cost=cost+extra
                    if next_cost>=best_cost:continue
                    next_done=done|1<<index;key=next_done,after
                    state=next_cost,next_done,after,path+(index,)
                    if key not in following or next_cost<following[key][0]:following[key]=state
            choices=sorted(following.values(),key=lambda state:(state[0],len(state[2]),state[1],state[2]))
            pruned+=max(0,len(choices)-beam_width);frontier=choices[:beam_width]
            if not frontier:break
        complete=[state for state in frontier if len(state[3])==len(branches)]
        for cost,_,_,path in complete:
            if cost>=best_cost:continue
            planned=unused[:];gets=set(unused)
            for index in path:
                branch=branches[index];spans={}
                for stage,value in enumerate(branch['arithmetic']):
                    for source in prepared.args_unique[value]:
                        if block.instructions[source].op=='GET':spans[source]=stage
                for value in branch['arithmetic']:
                    missing=[source for source in prepared.args_unique[value] if block.instructions[source].op=='GET' and source not in gets]
                    for source in sorted(missing,key=lambda source:(spans[source],source)):
                        planned.append(source);gets.add(source)
                    planned.append(value)
                planned.append(branch['terminal'])
            candidate=emit_order(block,planned,deadline=deadline)
            if candidate is None:raise AssertionError('Branch beam transition did not materialize')
            if candidate['stats']['inserted_copy_count']!=cost:raise AssertionError('Branch COPY transition cost mismatch')
            context.check(candidate);best=candidate;best_cost=cost
    except BudgetExceeded:
        if outcome!='state_budget_retained':outcome='time_budget_retained'
    if best is None:
        if 'budget' in outcome:raise BudgetExceeded('Branch COPY beam no verified candidate within budget')
        raise InfeasibleSchedule('Branch COPY beam no verified serialized-branch witness; no global proof')
    return {**best,'stats':{**best['stats'],'strategy':'branch_copy','elapsed_ms':(perf_counter()-started)*1000,
            'branch_copy':{'branches':len(branches),'expanded_states':expanded,'transitions':transitions,
                           'pruned_states':pruned,'beam_width':beam_width,'max_states':max_states,
                           'outcome':outcome,'baseline_error':baseline_error,
                           'scope':'bounded complete-spine order beam; real greedy relay costs and root ages; no global COPY optimality'}}}
