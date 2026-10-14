"""Copy-directed small neighborhoods, bitset engine and span-aware budgets.

This explicit optimizer reuses the physical mobile/backbone engine. Unlike the
old selector, a large private closure does not discard a useful smaller region.
External consumers and GET/SET hazards are still part of every engine state.
The search is heuristic: a truncated region/budget is never an infeasibility
certificate. Frozen research modules are deliberately left unchanged.
"""
from collections import Counter
from time import perf_counter

from .general_region_anytime import RegionStop
from .mobile_backbone_bound import prepare_mobile, search_mobile_backbone


def select_balanced_regions(graph, incumbent, check, max_regions=64):
    nodes, users, ranks = graph['nodes'], graph['users'], graph['ranks']
    copies, history, cursor = Counter(), [], 0
    width = graph['block'].window
    for row in incumbent['output']['optimized_instructions']:
        check()
        if row['op'] == 'COPY':
            identity = history[-int(row['source'][2:])]
            copies[identity] += 1
        else:
            identity = graph['order'][cursor]
            cursor += 1
            if nodes[identity].op == 'SET':
                identity = None
        history.append(identity)
        history = history[-width:]
    choices, seen = [], set()
    # Anchor selection is input/output-cost based, not graph-family based.
    anchors = sorted(copies, key=lambda node: (-copies[node], node))[:128]
    for anchor in anchors:
        check()
        consumers = sorted(users[anchor], key=ranks.get)
        if not consumers:
            continue
        seeds = [{anchor}, {anchor, consumers[-1]}]
        if len(consumers) <= 7:
            seeds.append({anchor, *consumers})
        # Expand private dependencies only while the region fits. The old
        # all-or-nothing closure rejected 3,855 anchors in the full336 run.
        expanded = set(seeds[-1])
        for _ in range(2):
            adjacent = set()
            for node in sorted(expanded):
                check()
                adjacent.update(src for src in set(nodes[node].args)
                                if len(users[src]) == 1)
                if len(users[node]) == 1:
                    adjacent.update(users[node])
            for node in sorted(adjacent - expanded,
                               key=lambda node: (abs(ranks[node]-ranks[anchor]), node)):
                if len(expanded) >= 12:
                    break
                expanded.add(node)
        seeds.insert(0, expanded)
        for variant, mobile in enumerate(seeds):
            check()
            left = min(ranks[node] for node in mobile)
            # Include every direct consumer in the fixed backbone even if it
            # did not fit the movable set; true last use remains exact.
            right = max(max(ranks[node] for node in mobile), ranks[consumers[-1]])
            identity = (left, right, tuple(sorted(mobile)))
            if identity in seen:
                continue
            seen.add(identity)
            choices.append({'region': {'L': left, 'R': right, 'mobile': list(identity[2])},
                'anchor': anchor, 'variant': variant, 'anchor_copies': copies[anchor],
                'span': right-left+1})
    # Interleave variants: all primary neighborhoods receive priority over
    # alternate neighborhoods of the same expensive anchor.
    choices.sort(key=lambda item: (item['variant'], -item['anchor_copies'],
                                  item['span'], item['anchor']))
    return choices[:max_regions], len(choices)


def refine_bound_mobile(data, incumbent, *, time_budget_ms=500,
        max_states=20000, max_transitions=20000, max_outcomes=4,
        max_regions=64, per_region_transitions=2000, on_completed=None,
        resource_snapshot=None):
    if min(time_budget_ms, max_states, max_transitions, max_outcomes,
           max_regions, per_region_transitions) <= 0 or max_regions > 64:
        raise ValueError('Positive budgets and at most 64 regions required')
    if max_states > 20000 or max_transitions > 20000:
        raise ValueError('This evidence layout supports at most 20000 work units')
    started = perf_counter()
    deadline = started + time_budget_ms/1000
    best = dict(incumbent)
    best['copies'] = sum(row['op'] == 'COPY' for row in incumbent['output']['optimized_instructions'])
    diagnostics, attempts, eligible = [], [], []
    processed = transitions = complete = selected_count = 0
    outcome = 'completed'

    def check():
        if perf_counter() >= deadline:
            raise RegionStop('total_deadline')

    def sink(index, candidate):
        nonlocal complete, best
        complete += 1
        if candidate['copies'] < best['copies']:
            best = candidate
        if on_completed is not None:
            on_completed(index, candidate)
        if resource_snapshot is not None:
            snapshot = resource_snapshot()
            if snapshot['disk_free_bytes'] < 512*1024**2:
                raise RegionStop('producer_resource_reserve')

    try:
        graph = prepare_mobile(data, incumbent, check)
        if resource_snapshot is not None:
            snapshot = resource_snapshot()
            need = graph['layout']['diagnostic_bound_bytes'] + 2*graph['layout']['complete_proposal_bound_bytes']
            if snapshot['disk_free_bytes'] < 512*1024**2 + need:
                raise RegionStop('resource_preflight')
        eligible, selected_count = select_balanced_regions(graph, incumbent, check, max_regions)
        for index, item in enumerate(eligible):
            check()
            if processed >= max_states:
                raise RegionStop('state_budget')
            if transitions >= max_transitions:
                raise RegionStop('transition_budget')
            remaining_ms = (deadline-perf_counter())*1000
            # Give long suffixes a useful allowance while preventing one
            # difficult region from consuming the entire graph budget.
            local_ms = min(max(100, min(250, item['span']/20)), remaining_ms)
            local_work = max(per_region_transitions, min(10000, 2*item['span']+128))
            result = search_mobile_backbone(data, incumbent, item['region'],
                time_budget_ms=local_ms, absolute_deadline=deadline,
                max_states=min(local_work, max_states-processed),
                max_transitions=min(local_work, max_transitions-transitions),
                max_outcomes=max_outcomes, prepared=graph,
                on_completed=lambda candidate, index=index: sink(index, candidate))
            stats = result['stats']
            processed += stats['processed_states']
            transitions += stats['attempted_transitions']
            attempts.append(dict(item, region_index=index, stats=stats))
            diagnostics.append(result['diagnostics'])
            # A local timeout, suffix failure or partial frontier does not
            # imply the next independently bounded region is unproductive.
            if stats['outcome'].startswith('partial_producer_resource'):
                raise RegionStop('producer_resource_reserve')
    except RegionStop as error:
        outcome = 'partial_' + str(error)
    return {'best': best, 'diagnostics': diagnostics, 'stats': {
        'outcome': outcome, 'processed_states': processed,
        'attempted_transitions': transitions, 'complete_outputs': complete,
        'eligible_regions': eligible, 'all_deduplicated_neighborhood_count': selected_count,
        'attempts': attempts, 'search_emit_ms': (perf_counter()-started)*1000,
        'parameters': {'time_budget_ms': time_budget_ms, 'max_states': max_states,
            'max_transitions': max_transitions, 'max_regions': max_regions,
            'per_region_transition_floor': per_region_transitions,
            'per_region_transition_rule': 'max(floor,min(10000,2*span+128)), clipped by remaining total',
            'per_region_ms_rule': 'max(100,min(250,span/20)), clipped by remaining total',
            'max_outcomes': max_outcomes},
        'scope': 'Same incumbent for all regions; physical identity/hazard engine; heuristic only.'}}
