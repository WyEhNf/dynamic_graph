"""Isolated mobile selector/portfolio. Same initial incumbent for every region."""
from collections import Counter
from pathlib import Path
import shutil
from time import perf_counter

from .general_region_anytime import RegionStop
from .mobile_backbone_anytime import prepare_mobile, search_mobile_backbone


def select_mobile_regions(graph, incumbent, check, max_regions=64):
    nodes, users, ranks = graph['nodes'], graph['users'], graph['ranks']
    incoming = [[] for _ in nodes]
    for node in nodes:
        check()
        incoming[node.index] = sorted(set(node.args))
    copies, history, cursor = Counter(), [], 0
    width = graph['block'].window
    for row in incumbent['output']['optimized_instructions']:
        check()
        if row['op'] == 'COPY':
            d = int(row['source'][2:])
            identity = history[-d]
            if identity is None:
                raise ValueError('COPY of SET in initial output')
            copies[identity] += 1
        else:
            identity = graph['order'][cursor]
            cursor += 1
            if nodes[identity].op == 'SET':
                identity = None
        history.append(identity)
        history = history[-width:]
    choices, rejected, seen = [], [], set()
    for anchor in sorted(copies):
        check()
        consumers = users[anchor]
        if not consumers:
            rejected.append({'anchor': anchor, 'reason': 'copied_dead_identity_no_consumers'})
            continue
        if len(consumers) <= 31:
            mobile = {anchor} | consumers
        else:
            mobile = {max(consumers, key=lambda node: ranks[node])}
        changed = True
        while changed:
            changed = False
            for node in sorted(mobile):
                check()
                additions = {src for src in incoming[node] if len(users[src]) == 1}
                if len(users[node]) == 1:
                    additions.update(users[node])
                if not additions <= mobile:
                    mobile.update(additions)
                    changed = True
                if len(mobile) > 32:
                    break
            if len(mobile) > 32:
                break
        if len(mobile) > 32:
            rejected.append({'anchor': anchor, 'reason': 'closure_exceeds_32', 'closed_size_at_rejection': len(mobile)})
            continue
        if any(nodes[node].op == 'GET' and not users[node] <= mobile for node in mobile):
            rejected.append({'anchor': anchor, 'reason': 'shared_GET_consumers_outside_mobile'})
            continue
        minimum = min(ranks[node] for node in mobile)
        previous = -1
        for index in sorted(mobile):
            check()
            for dep in set(nodes[index].args) | set(nodes[index].order_deps):
                if dep not in mobile and ranks[dep] < minimum:
                    previous = max(previous, ranks[dep])
        left = previous + 1
        right = max(ranks[node] for node in mobile)
        for index in sorted(mobile):
            check()
            for consumer in users[index] - mobile:
                right = max(right, ranks[consumer])
        region = {'L': left, 'R': right, 'mobile': sorted(mobile)}
        identity = (left, right, tuple(region['mobile']))
        if identity in seen:
            rejected.append({'anchor': anchor, 'reason': 'duplicate_neighborhood'})
            continue
        seen.add(identity)
        gap = max(ranks[consumer] for consumer in consumers) - ranks[anchor]
        choices.append({'region': region, 'anchor': anchor, 'initial_anchor_copies': copies[anchor],
                        'anchor_to_last_use_original_gap': gap})
    choices.sort(key=lambda item: (-item['initial_anchor_copies'], -item['anchor_to_last_use_original_gap'], item['anchor']))
    return choices[:max_regions], rejected, len(choices)


def refine_mobile_backbones(data, incumbent, *, time_budget_ms=500, max_states=20000,
        max_transitions=20000, max_outcomes=16, max_regions=64, on_completed=None,
        resource_snapshot=None):
    started = perf_counter()
    deadline = started + time_budget_ms / 1000
    if min(time_budget_ms, max_states, max_transitions, max_outcomes, max_regions) <= 0 or max_regions > 64:
        raise ValueError('Positive budgets; at most64 regions')
    best = {'output': incumbent['output'], 'original_order': incumbent['original_order'],
            'copies': sum(row['op'] == 'COPY' for row in incumbent['output']['optimized_instructions'])}
    attempts, diagnostics, eligible, rejected, caps, snapshots = [], [], [], [], [], []
    processed = transitions = complete = selected_count = 0
    layout = None
    outcome = 'completed'
    reserve = 512 * 1024**2
    if resource_snapshot is None:
        resource_snapshot = lambda: {'disk_free_bytes': shutil.disk_usage(Path(__file__).resolve().parents[1]).free}

    def check():
        if perf_counter() >= deadline:
            raise RegionStop('total_deadline')

    def sink(region_index, candidate):
        nonlocal best, complete
        complete += 1
        if candidate['copies'] < best['copies']:
            best = candidate
        if on_completed is not None:
            on_completed(region_index, candidate)
        snapshot = resource_snapshot()
        snapshots.append(dict(snapshot, stage='after_saved_complete', region_index=region_index))
        if snapshot['disk_free_bytes'] < reserve:
            raise RegionStop('producer_resource_reserve_after_saved_complete')

    try:
        graph = prepare_mobile(data, incumbent, check)
        layout = graph['layout']
        need = layout['diagnostic_bound_bytes'] + 2 * layout['complete_proposal_bound_bytes'] + 64 * 1024**2
        snapshot = resource_snapshot()
        snapshots.append(dict(snapshot, stage='before_search', input_package_bound_bytes=need))
        if need > reserve or snapshot['disk_free_bytes'] < reserve + need:
            raise RegionStop('resource_preflight_unknown')
        check()
        eligible, rejected, selected_count = select_mobile_regions(graph, incumbent, check, max_regions)
        for region_index, item in enumerate(eligible):
            check()
            if processed >= max_states:
                raise RegionStop('state_budget')
            if transitions >= max_transitions:
                raise RegionStop('transition_budget')
            result = search_mobile_backbone(data, incumbent, item['region'],
                time_budget_ms=max(1e-9, (deadline - perf_counter()) * 1000), absolute_deadline=deadline,
                max_states=max_states - processed, max_transitions=max_transitions - transitions,
                max_outcomes=max_outcomes, prepared=graph,
                on_completed=lambda candidate, index=region_index: sink(index, candidate))
            stats = result['stats']
            processed += stats['processed_states']
            transitions += stats['attempted_transitions']
            attempts.append(dict(item, region_index=region_index, stats=stats, diagnostic_reference=len(diagnostics)))
            diagnostics.append(result['diagnostics'])
            if stats['outcome'] == 'partial_outlet_limit':
                caps.append(region_index)
                outcome = 'partial_outlet_limit'
                continue
            if stats['outcome'] != 'exhausted_improvement_search':
                outcome = stats['outcome']
                break
    except RegionStop as error:
        outcome = 'partial_' + str(error)
    return {'best': best, 'diagnostics': diagnostics, 'stats': {'outcome': outcome,
        'processed_states': processed, 'attempted_transitions': transitions, 'complete_outputs': complete,
        'attempts': attempts, 'eligible_regions': eligible, 'rejected_anchors': rejected,
        'all_deduplicated_neighborhood_count': selected_count, 'outlet_limited_regions': caps,
        'resource_layout': layout, 'resource_snapshots': snapshots,
        'search_emit_ms': (perf_counter() - started) * 1000,
        'parameters': {'total_ms': time_budget_ms, 'expansions': max_states,
                       'transition_attempts': max_transitions, 'mobile_nodes': 32,
                       'outlets_each_region': max_outcomes, 'max_regions': max_regions},
        'scope': 'All proposals from identical initial; literal search budget includes parse/selection/emission/sink. Export later. No default hook.'}}
