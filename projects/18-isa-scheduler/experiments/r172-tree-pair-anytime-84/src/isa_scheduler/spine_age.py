"""Restricted beam over complete shared-root spines with physical relay costs.

All original arithmetic stays in its true branch dependency order. Choices
interleave individual arithmetic instructions, with GET born on first use.
State includes every original prefix, born-root mask, remaining original root
uses and all live original identity ages. Not a global COPY optimum/proof.
"""
from collections import OrderedDict
from time import perf_counter

from .branch_copy import _branches
from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded, InfeasibleSchedule


def _step(block, branches, roots, root_slot, state, branch_index, deadline):
    prefixes, born, remaining, ages, cost, path = state
    stage = prefixes[branch_index]; branch = branches[branch_index]
    if stage >= len(branch['arithmetic']): return None
    nodes = block.instructions; value = branch['arithmetic'][stage]
    counters = list(remaining); positions = {original: -age for original, age in ages}
    live = OrderedDict(sorted(positions.items(), key=lambda row: row[1])); now = copies = steps = 0
    def uses(original):
        return counters[root_slot[original]] if original in root_slot else 1
    def issue(original):
        nonlocal now, copies, steps
        args = set(nodes[original].args); stalled = 0
        while live:
            steps += 1
            if steps % 32 == 1 and perf_counter() >= deadline: raise BudgetExceeded('Spine-age transition time budget')
            oldest = next(iter(live)); age = now - positions[oldest]
            if age > block.window: return False
            if age < block.window or oldest in args and uses(oldest) == 1: break
            positions[oldest] = now; live.move_to_end(oldest); now += 1; copies += 1; stalled += 1
            if stalled >= block.window: return False
        if any(source not in positions or not 1 <= now - positions[source] <= block.window for source in args): return False
        positions[original] = now; now += 1
        for source in args:
            if source in root_slot:
                slot = root_slot[source]; counters[slot] -= 1
                if counters[slot] == 0: live.pop(source, None)
            else: live.pop(source, None)
        if nodes[original].op == 'GET':
            if counters[root_slot[original]]: live[original] = now - 1
        elif nodes[original].op != 'SET': live[original] = now - 1
        return True
    missing = [source for source in set(nodes[value].args) if nodes[source].op == 'GET' and not born >> root_slot[source] & 1]
    # GET order is an explicit restricted policy; beam does not claim all
    # physical COPY placements or all GET birth orders are enumerated.
    for source in sorted(missing, key=lambda source: (-counters[root_slot[source]], source)):
        if not issue(source): return None
        born |= 1 << root_slot[source]
    if not issue(value): return None
    if stage + 1 == len(branch['arithmetic']):
        if not issue(branch['terminal']): return None
    after = list(prefixes); after[branch_index] += 1
    return tuple(after), born, tuple(counters), tuple(sorted((source, now - positions[source]) for source in live)), cost + copies, (branch_index, path)


def schedule_spine_age(block, *, time_budget_ms=1000, beam_width=4, max_states=100000, prepared=None, cutoff=None, priority='consumer_floor'):
    if time_budget_ms <= 0 or beam_width < 1 or max_states < 1: raise ValueError('Positive spine-age limits required')
    if priority not in ('cost', 'consumer_floor'): raise ValueError('Unknown spine-age beam priority')
    if prepared is not None and prepared.block is not block: raise ValueError('PreparedGraph belongs to another block')
    # Official parser supports W4/8/16/32. Direct Block callers may construct
    # W1; some such programs are feasible, but this research matcher excludes
    # them explicitly instead of dividing by W-1 or claiming infeasibility.
    if block.window < 2: raise InfeasibleSchedule('Spine-age W1 unsupported; matcher restriction only, not infeasibility proof')
    tick = perf_counter(); deadline = tick + time_budget_ms / 1000
    prepared = prepared or PreparedGraph(block, time_budget_ms=time_budget_ms)
    branches, unused = _branches(block, prepared); nodes = block.instructions
    if perf_counter() >= deadline: raise BudgetExceeded('Spine-age preprocessing budget exhausted')
    for branch in branches:
        previous = None
        for original in branch['arithmetic']:
            arithmetic_args = {source for source in nodes[original].args if nodes[source].op in ('ADD', 'MULW')}
            if arithmetic_args != (set() if previous is None else {previous}):
                raise InfeasibleSchedule('Spine-age rejects non-chain arithmetic; matcher failure only')
            previous = original
    roots = sorted({root for branch in branches for root in branch['roots']}); root_slot = {root: slot for slot, root in enumerate(roots)}
    if len(roots) > 64: raise InfeasibleSchedule('Spine-age limited to 64 root roles; matcher restriction only')
    remaining = tuple(prepared.remaining[root] for root in roots)
    frontier = [(tuple(0 for _ in branches), 0, remaining, (), 0, None)]
    def rank(state):
        prefix, born, remaining, ages, cost, _ = state
        future = 0
        if priority == 'consumer_floor':
            physical = dict(ages)
            for slot, root in enumerate(roots):
                consumers = remaining[slot]
                if consumers:
                    # Unborn GET optimistically starts at age1. A current age
                    # a and u distinct remaining consumers require at least
                    # ceil((a+u-1-W)/(W-1)) own future relays. Ranking only.
                    age = physical.get(root, 1)
                    shortage = age + consumers - 1 - block.window
                    future += max(0, (shortage + block.window - 2) // (block.window - 1))
        return cost + future, cost, len(ages), sum(remaining), tuple(-n for n in prefix)
    expanded = transitions = pruned = 0
    for depth in range(sum(len(branch['arithmetic']) for branch in branches)):
        following = {}
        for state in frontier:
            if perf_counter() >= deadline or expanded >= max_states: raise BudgetExceeded('Spine-age beam unknown budget, no completed witness')
            expanded += 1
            for branch_index in range(len(branches)):
                transitions += 1; after = _step(block, branches, roots, root_slot, state, branch_index, deadline)
                if after is None or cutoff is not None and after[4] >= cutoff: continue
                key = after[:4]
                if key not in following or after[4] < following[key][4]: following[key] = after
        # Resource ties favor fewer live identities and fewer unfinished original
        # GET consumers, then deterministic original-prefix progress. Heuristic.
        choices = sorted(following.values(), key=rank)
        pruned += max(0, len(choices) - beam_width); frontier = choices[:beam_width]
        if not frontier: raise InfeasibleSchedule('Spine-age restricted beam found no complete witness; no infeasibility proof')
    best = min(frontier, key=lambda state: state[4]); path = []; link = best[5]
    while link is not None: branch_index, link = link; path.append(branch_index)
    path.reverse(); order = list(unused); born = set(unused); prefixes = [0] * len(branches)
    remaining = {root: prepared.remaining[root] for root in roots}
    for path_offset, branch_index in enumerate(path):
        if path_offset % 64 == 0 and perf_counter() >= deadline: raise BudgetExceeded('Spine-age original-order restoration budget exhausted')
        branch = branches[branch_index]; original = branch['arithmetic'][prefixes[branch_index]]
        missing = [source for source in set(nodes[original].args) if nodes[source].op == 'GET' and source not in born]
        for source in sorted(missing, key=lambda source: (-remaining[source], source)):
            order.append(source); born.add(source)
        order.append(original)
        for source in set(nodes[original].args):
            if source in remaining: remaining[source] -= 1
        prefixes[branch_index] += 1
        if prefixes[branch_index] == len(branch['arithmetic']): order.append(branch['terminal'])
    candidate = emit_order(block, order, deadline=deadline)
    if candidate is None or candidate['stats']['inserted_copy_count'] != best[4]:
        raise AssertionError('Spine-age identity/cost restoration disagrees with actual emitter')
    candidate['stats'].update(strategy='spine_age', beam_width=beam_width, expanded_states=expanded,
        transitions=transitions, pruned_states=pruned, beam_priority=priority, elapsed_ms=(perf_counter() - tick) * 1000,
        scope='Restricted original arithmetic-prefix beam, lazy GET birth, greedy physical COPY; no global optimum or negative certificate')
    return candidate
