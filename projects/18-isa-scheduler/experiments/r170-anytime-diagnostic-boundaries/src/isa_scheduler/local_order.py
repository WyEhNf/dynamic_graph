"""Bounded adjacent topological swaps with strict verified incumbent retention.

Only original order changes. Distinct original values, ordered operands and all
memory hazards remain intact; no algebraic rewrite/alias/recompute is allowed.
The span lower bound ranks moves only, never certifies global optimality.
"""
from collections import OrderedDict
from time import perf_counter
from .model import BudgetExceeded, InfeasibleSchedule
from .verify import VerificationContext


def emit_order(block, order, *, deadline, cutoff=None, materialize=True):
    """Greedy expiry relays for a checked topological original-node order.

    Simulation and emission share transition rules, but the independent raw
    input/output verifier is required before promoting any emitted candidate.
    None means cutoff/fixed-order failure, not global infeasibility.
    """
    tick=perf_counter();nodes=block.instructions;n=len(nodes);window=block.window
    if len(order)!=n or set(order)!=set(range(n)):raise ValueError('Order must be a permutation')
    rank=[0]*n
    for position,index in enumerate(order):rank[index]=position
    for node in nodes:
        if any(rank[source]>=rank[node.index] for source in (*node.args,*node.order_deps)):
            raise ValueError('Order violates data or memory dependencies')
    remaining=[0]*n;args_unique=[set(node.args) for node in nodes]
    for args in args_unique:
        for source in args:remaining[source]+=1
    positions=[-1]*n;live=OrderedDict();output=[];now=copies=stalled=steps=0
    tokens=tuple(f't#{distance}' for distance in range(window+1))
    for index in order:
        node=nodes[index];args=args_unique[index]
        while True:
            steps+=1
            if steps%32==1 and perf_counter()>=deadline:raise BudgetExceeded('Local-order simulation budget exhausted')
            if not live:break
            oldest=next(iter(live));age=now-positions[oldest]
            if age>window:return None
            if age<window or oldest in args and remaining[oldest]==1:break
            if materialize:output.append({'id':now,'op':'COPY','source':tokens[window]})
            positions[oldest]=now;live.move_to_end(oldest);now+=1;copies+=1;stalled+=1
            if stalled>=window or cutoff is not None and copies>=cutoff:return None
        if any(not 1<=now-positions[source]<=window for source in node.args):return None
        if materialize:
            row={'id':now,'op':node.op}
            if node.reg is not None:row['reg']=node.reg
            encoded=[tokens[now-positions[source]] for source in node.args]
            if node.op=='COPY':row['source']=encoded[0]
            elif encoded:row['inputs']=encoded
            output.append(row)
        positions[index]=now;now+=1
        for source in args:
            remaining[source]-=1
            if not remaining[source]:live.pop(source,None)
        if remaining[index]:live[index]=now-1
        stalled=0
    if not materialize:return copies
    total=copies+sum(node.op=='COPY' for node in nodes)
    return {'block_id':block.block_id,'optimized_instructions':output,'stats':{
        'strategy':'local_swap','original_instruction_count':n,'optimized_instruction_count':now,
        'inserted_copy_count':copies,'total_copy_count':total,
        'copy_ratio_output':total/now if now else 0,
        'inserted_copy_ratio_original':copies/n if n else 0,
        'bit_width':block.bit_width,'max_back_distance':window,'original_order':list(order),
        'elapsed_ms':(perf_counter()-tick)*1000}}


def improve_order(data, block, incumbent, *, time_budget_ms=50, max_trials=128, rounds=2, max_nodes=512, neighborhood='adjacent'):
    if time_budget_ms<=0 or max_trials<=0 or rounds<=0:raise ValueError('Positive local search budgets required')
    if neighborhood not in ('adjacent','relocate'):raise ValueError('Unknown local neighborhood')
    started=perf_counter();deadline=started+time_budget_ms/1000;n=len(block.instructions)
    best=incumbent;cost=incumbent['stats']['inserted_copy_count'];trials=promotions=0
    # Verify the initial candidate as well: direct callers may not supply trusted
    # optimizer output. No scheduler state is used by this checker.
    checked=perf_counter();context=VerificationContext(data);context.check(best)
    verify_ms=(perf_counter()-checked)*1000
    order=list(best['stats'].get('original_order',[]))
    outcome='no_improvement'
    if n>max_nodes or len(order)!=n or not cost:
        outcome='skipped_size_or_zero_copy'
    else:
        users=[set() for _ in range(n)];successors=[set() for _ in range(n)];deps=[]
        for node in block.instructions:
            deps.append(set((*node.args,*node.order_deps)))
            for source in set(node.args):users[source].add(node.index)
            for source in deps[-1]:successors[source].add(node.index)
        try:
            for _ in range(rounds):
                if perf_counter()>=deadline:raise BudgetExceeded('Local-order budget exhausted')
                rank=[0]*n
                for position,index in enumerate(order):rank[index]=position
                def span_bound(value):
                    last=max((rank[user] for user in users[value]),default=rank[value])
                    return max(0,(last-rank[value]-1)//block.window)
                candidates=[]
                for position in range(n-1):
                    left,right=order[position:position+2]
                    if left in deps[right]:continue
                    affected={left,right,*block.instructions[left].args,*block.instructions[right].args}
                    before=sum(span_bound(value) for value in affected)
                    rank[left],rank[right]=rank[right],rank[left]
                    delta=sum(span_bound(value) for value in affected)-before
                    rank[left],rank[right]=rank[right],rank[left]
                    if delta<=0:candidates.append((delta,position,position+1))
                if neighborhood=='relocate':
                    radius=min(32,2*block.window)
                    seen={(source,target) for _,source,target in candidates}
                    for source,index in enumerate(order):
                        if source%32==0 and perf_counter()>=deadline:raise BudgetExceeded('Local move scoring budget exhausted')
                        earliest=max((rank[dependency]+1 for dependency in deps[index]),default=0)
                        latest=min((rank[user]-1 for user in successors[index]),default=n-1)
                        for target in (max(earliest,source-radius),min(latest,source+radius)):
                            if target==source or (source,target) in seen:continue
                            seen.add((source,target));lo,hi=sorted((source,target))
                            touched=order[lo:hi+1]
                            affected=set(touched)
                            for value in touched:affected.update(block.instructions[value].args)
                            before=sum(span_bound(value) for value in affected)
                            moved=touched[:];moved.insert(target-lo,moved.pop(source-lo))
                            for offset,value in enumerate(moved,lo):rank[value]=offset
                            delta=sum(span_bound(value) for value in affected)-before
                            for offset,value in enumerate(touched,lo):rank[value]=offset
                            if delta<=0:candidates.append((delta,source,target))
                candidates.sort();improved=False
                # Scores are recomputed next round. Inside a round all moves
                # are based on the same order, avoiding stale dependency tests.
                base_order=order[:]
                for _,source,target in candidates:
                    if trials>=max_trials:outcome='trial_budget_exhausted';break
                    trial=base_order[:];trial.insert(target,trial.pop(source));trials+=1
                    simulated=emit_order(block,trial,deadline=deadline,cutoff=cost,materialize=False)
                    if simulated is None or simulated>=cost:continue
                    candidate=emit_order(block,trial,deadline=deadline,cutoff=cost)
                    if candidate is None:raise AssertionError('Simulation/emission transition mismatch')
                    checked=perf_counter();context.check(candidate);verify_ms+=(perf_counter()-checked)*1000
                    best=candidate;cost=simulated;order=trial;promotions+=1;improved=True;outcome='improved'
                    if not cost:break
                if not cost or trials>=max_trials or not improved:break
        except BudgetExceeded:
            outcome='time_budget_exhausted_retained_verified'
    stats={**incumbent['stats'],**best['stats'],'local_order':{
        'outcome':outcome,'trials':trials,'promotions':promotions,'max_trials':max_trials,
        'rounds':rounds,'max_nodes':max_nodes,'elapsed_ms':(perf_counter()-started)*1000,
        'verify_ms':verify_ms,'incumbent_strategy':incumbent['stats']['strategy'],
        'time_budget_ms':time_budget_ms,'neighborhood':neighborhood,
        'scope':'topological original-node moves; greedy COPY timing; no global optimality claim'}}
    return {**best,'stats':stats}
