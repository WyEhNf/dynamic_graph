"""Same frozen R164 selector, isolated AWA* with one literal total deadline."""
from collections import Counter
from time import perf_counter

from .model import BudgetExceeded, parse_block
from .tree_pipeline import match_forest
from .tree_pair_anytime import schedule_fixed_tree_pair_anytime


def refine_fixed_tree_pairs_anytime(data, incumbent, *, time_budget_ms=500, max_states=20000,
                            max_outcomes=16, max_parent_nodes=96, on_completed=None):
    started=perf_counter(); deadline=started+time_budget_ms/1000
    if min(time_budget_ms,max_states,max_outcomes,max_parent_nodes)<=0: raise ValueError('Positive budgets required')
    baseline_cost=sum(row['op']=='COPY' for row in incumbent['output']['optimized_instructions'])
    best={'output':incumbent['output'],'original_order':incumbent['original_order'],'copies':baseline_cost}
    processed=0; attempts=[]; complete_outputs=0; eligible=[]; parse_ms=scan_ms=0.0; stop='completed'; diagnostics=[]

    def check():
        if perf_counter()>=deadline: raise BudgetExceeded('Total warm-start budget exhausted')

    def sink(parent,candidate):
        nonlocal best,complete_outputs
        complete_outputs+=1
        if candidate['copies']<best['copies']: best=candidate
        if on_completed is not None: on_completed(parent,candidate)

    try:
        block=parse_block(data); forest=match_forest(block); check()
        parse_ms=(perf_counter()-started)*1000; nodes=block.instructions; children=forest['children']
        order=incumbent['original_order']
        if sorted(order)!=list(range(len(nodes))): raise ValueError('Complete incumbent permutation required')
        ranks={node:rank for rank,node in enumerate(order)}; subtrees=[]; branch=[]
        for node in nodes:
            check(); subtree={node.index}; contains=len(children[node.index])==2
            for child in children[node.index]: subtree.update(subtrees[child]); contains|=branch[child]
            subtrees.append(subtree); branch.append(contains)
        copies_by_identity=Counter(); copies_by_cursor=Counter(); history=[]; cursor=0
        for row in incumbent['output']['optimized_instructions']:
            check(); position=len(history)
            if row['op']=='COPY':
                distance=int(row['source'][2:])
                if not 1<=distance<=min(position,block.window): raise ValueError('Illegal incoming COPY distance')
                identity=history[position-distance]
                if identity is None: raise ValueError('Incoming COPY of SET')
                copies_by_identity[identity]+=1; copies_by_cursor[cursor]+=1
            else:
                if cursor>=len(order): raise ValueError('Too many incoming originals')
                identity=order[cursor]; cursor+=1
                if row['op']!=nodes[identity].op: raise ValueError('Incoming original opcode mismatch')
                if row['op']=='SET': identity=None
            history.append(identity)
        if cursor!=len(order): raise ValueError('Missing incoming original')
        copy_prefix=[0]
        for rank in range(len(nodes)+1): copy_prefix.append(copy_prefix[-1]+copies_by_cursor[rank])
        for parent,kids in enumerate(children):
            check()
            if len(kids)!=2 or not any(branch[child] for child in kids): continue
            members=subtrees[parent]
            if len(members)>max_parent_nodes: continue
            start=min(ranks[node] for node in members); end=max(ranks[node] for node in members)
            if end-start+1!=len(members) or order[end]!=parent: continue
            child_copies=sum(copies_by_identity[child] for child in kids)
            local_copies=copy_prefix[end+1]-copy_prefix[start]
            eligible.append((parent,child_copies,local_copies,len(members)))
        # A fixed heuristic ranking, not a COPY lower bound or impossibility
        # certificate. All selected pairs still use the initial incumbent.
        eligible.sort(key=lambda item:(-item[1],-item[2],item[3],item[0]))
        scan_ms=(perf_counter()-started)*1000-parse_ms
        for parent,child_copies,local_copies,size in eligible:
            check()
            if processed>=max_states: raise BudgetExceeded('Total warm-start state budget exhausted')
            tick=perf_counter(); streamed_before=complete_outputs
            result=schedule_fixed_tree_pair_anytime(data,incumbent,parent,
                time_budget_ms=max(1e-9,(deadline-perf_counter())*1000),max_states=max_states-processed,
                max_outcomes=max_outcomes,max_parent_nodes=max_parent_nodes,
                on_completed=lambda candidate:sink(parent,candidate),absolute_deadline=deadline)
            used=result['stats']['processed_states']; processed+=used
            if processed>max_states: raise AssertionError('Cumulative state budget exceeded')
            # Retain current-input references only. Export occurs after this
            # entire search returns, so no diagnostics I/O steals or extends
            # its literal absolute deadline. Producer disposes each reference.
            reference=len(diagnostics); diagnostics.append(result['diagnostics'])
            attempts.append({'parent':parent,'outcome':result['stats']['outcome'],'processed_states':used,
                'complete_outputs':complete_outputs-streamed_before,'copies':result['best']['copies'],
                'stats':result['stats'],'diagnostic_reference':reference,'elapsed_ms':(perf_counter()-tick)*1000})
            if result['stats']['outcome']!='exhausted_improvement_search':
                stop=result['stats']['outcome']; break
    except BudgetExceeded as error:
        stop='partial_budget'
        attempts.append({'parent':None,'outcome':'unknown_budget','message':str(error),
                         'processed_states':0,'complete_outputs':0})
    return {'best':best,'diagnostics':diagnostics,'stats':{'strategy':'explicit_fixed_w2_tree_pair_warm_start','outcome':stop,
        'baseline_copies':baseline_cost,'copies':best['copies'],'processed_states':processed,
        'complete_outputs':complete_outputs,'eligible_parents':eligible,'attempts':attempts,
        'parse_match_ms':parse_ms,'scan_selection_ms':scan_ms,'elapsed_ms':(perf_counter()-started)*1000,
        'parameters':{'total_time_budget_ms':time_budget_ms,'total_processed_state_budget':max_states,
                      'max_outcomes_each_pair':max_outcomes,'max_parent_nodes':max_parent_nodes},
        'scope':'Same initial saved incumbent per proposal and exact R164 selection. No gain composition/default hook. Diagnostics export after full input search, never within/pausing/extending deadline. Current-input references at most20k cumulative expansions; producer releases before next input.'}}
