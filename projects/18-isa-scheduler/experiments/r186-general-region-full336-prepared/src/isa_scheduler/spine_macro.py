"""Experimental shared-root runs in a bounded physical-age beam.

A macro only chooses several consecutive originals from one private spine.
Every original is simulated separately by the frozen individual transition.
Progress buckets make variable-length actions comparable at equal original
arithmetic progress; no completion, COPY optimum or infeasibility guarantee.
"""
from time import perf_counter

from .branch_copy import _branches
from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded, InfeasibleSchedule
from .spine_age import _step


def schedule_spine_macro(block, *, time_budget_ms=1000, beam_width=4,
                        max_states=100000, prepared=None, cutoff=None,
                        max_span=16, priority='consumer_floor'):
    if time_budget_ms <= 0 or beam_width < 1 or max_states < 1 or max_span < 2:
        raise ValueError('Positive macro limits and span >=2 required')
    if priority not in ('cost', 'consumer_floor'):
        raise ValueError('Unknown macro priority')
    if prepared is not None and prepared.block is not block:
        raise ValueError('PreparedGraph belongs to another block')
    if block.window < 2:
        raise InfeasibleSchedule('Spine-macro W1 unsupported; matcher restriction only')
    tick = perf_counter(); deadline = tick + time_budget_ms / 1000
    prepared = prepared or PreparedGraph(block, time_budget_ms=time_budget_ms)
    branches, unused = _branches(block, prepared); nodes = block.instructions
    roots = sorted({root for branch in branches for root in branch['roots']})
    if len(roots) > 64:
        raise InfeasibleSchedule('Spine-macro limited to 64 roots; matcher restriction only')
    root_slot = {root: slot for slot, root in enumerate(roots)}
    spans = []
    for branch in branches:
        previous = None; signatures = []
        for original in branch['arithmetic']:
            arithmetic_args = {source for source in nodes[original].args
                               if nodes[source].op in ('ADD', 'MULW')}
            if arithmetic_args != (set() if previous is None else {previous}):
                raise InfeasibleSchedule('Spine-macro rejects non-chain arithmetic; matcher only')
            signatures.append(frozenset(source for source in nodes[original].args
                                        if nodes[source].op == 'GET'))
            previous = original
        lengths = [1] * len(signatures)
        for position in range(len(signatures) - 2, -1, -1):
            if signatures[position] == signatures[position + 1]:
                lengths[position] = min(max_span, 1 + lengths[position + 1])
        spans.append(lengths)
    if perf_counter() >= deadline:
        raise BudgetExceeded('Spine-macro preprocessing budget exhausted')
    remaining = tuple(prepared.remaining[root] for root in roots)
    initial = (tuple(0 for _ in branches), 0, remaining, (), 0, None)
    total = sum(len(branch['arithmetic']) for branch in branches)
    buckets = {0: {initial[:4]: initial}}

    def rank(state):
        prefix, born, remaining, ages, cost, _ = state
        future = 0
        if priority == 'consumer_floor':
            physical = dict(ages)
            for slot, root in enumerate(roots):
                consumers = remaining[slot]
                if consumers:
                    shortage = physical.get(root, 1) + consumers - 1 - block.window
                    future += max(0, (shortage + block.window - 2) // (block.window - 1))
        return cost + future, cost, len(ages), sum(remaining), tuple(-n for n in prefix)

    expanded = transitions = pruned = macro_actions = simulated = 0
    for depth in range(total):
        following = buckets.pop(depth, {})
        frontier = sorted(following.values(), key=rank)
        pruned += max(0, len(frontier) - beam_width)
        for state in frontier[:beam_width]:
            if perf_counter() >= deadline or expanded >= max_states:
                raise BudgetExceeded('Spine-macro beam budget unknown, no completed witness')
            expanded += 1
            for branch_index, prefix in enumerate(state[0]):
                if prefix == len(spans[branch_index]):
                    continue
                length = spans[branch_index][prefix]
                lengths = (1,) if length == 1 else (1, length)
                after = state
                for offset in range(1, length + 1):
                    simulated += 1
                    after = _step(block, branches, roots, root_slot, after, branch_index, deadline)
                    if after is None or cutoff is not None and after[4] >= cutoff:
                        break
                    if offset not in lengths:
                        continue
                    transitions += 1; macro_actions += offset > 1
                    target = buckets.setdefault(depth + offset, {})
                    key = after[:4]
                    if key not in target or after[4] < target[key][4]:
                        target[key] = after
                    # A future progress layer receives at most span earlier
                    # layers. Bound storage independently of total DAG size.
                    if len(target) > beam_width * 8:
                        keep = sorted(target.values(), key=rank)[:beam_width * 4]
                        pruned += len(target) - len(keep)
                        buckets[depth + offset] = {candidate[:4]: candidate for candidate in keep}
    complete = buckets.get(total, {})
    if not complete:
        raise InfeasibleSchedule('Spine-macro restricted beam found no witness; no infeasibility proof')
    best = min(complete.values(), key=lambda state: state[4])
    path = []; link = best[5]
    while link is not None:
        branch_index, link = link; path.append(branch_index)
    path.reverse(); order = list(unused); born = set(unused)
    prefixes = [0] * len(branches)
    remaining = {root: prepared.remaining[root] for root in roots}
    for path_offset, branch_index in enumerate(path):
        if path_offset % 64 == 0 and perf_counter() >= deadline:
            raise BudgetExceeded('Spine-macro original restoration budget exhausted')
        branch = branches[branch_index]
        original = branch['arithmetic'][prefixes[branch_index]]
        missing = [source for source in set(nodes[original].args)
                   if nodes[source].op == 'GET' and source not in born]
        for source in sorted(missing, key=lambda source: (-remaining[source], source)):
            order.append(source); born.add(source)
        order.append(original)
        for source in set(nodes[original].args):
            if source in remaining: remaining[source] -= 1
        prefixes[branch_index] += 1
        if prefixes[branch_index] == len(branch['arithmetic']):
            order.append(branch['terminal'])
    candidate = emit_order(block, order, deadline=deadline)
    if candidate is None or candidate['stats']['inserted_copy_count'] != best[4]:
        raise AssertionError('Spine-macro restoration disagrees with physical COPY simulation')
    candidate['stats'].update(strategy='spine_macro', beam_width=beam_width,
        max_span=max_span, beam_priority=priority, expanded_states=expanded,
        transitions=transitions, macro_actions=macro_actions, simulated_originals=simulated,
        pruned_states=pruned, elapsed_ms=(perf_counter() - tick) * 1000,
        scope='Restricted root-run progress buckets; every original simulated; no optimum or negative proof')
    return candidate
