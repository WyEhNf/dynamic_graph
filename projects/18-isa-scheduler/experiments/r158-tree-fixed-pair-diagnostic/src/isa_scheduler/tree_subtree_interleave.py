"""One fixed-order pair in a complete pure tree; explicit research only.

Two prefix indices determine every local identity still needed. Equal complete
age states may merge; no age dominance, alias, recomputation or early COPY.
Every proposed result is a complete original block, not only a local cost.
"""
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule, parse_block
from .tree_pipeline import match_forest, _advance


def schedule_fixed_tree_pair(data, incumbent, parent, *, time_budget_ms=500,
                             max_states=20000, max_outcomes=16):
    started = perf_counter(); deadline = started + time_budget_ms / 1000
    if min(time_budget_ms, max_states, max_outcomes) <= 0: raise ValueError('Positive budgets required')

    def check():
        if perf_counter() >= deadline: raise BudgetExceeded('Fixed tree pair total budget exhausted')

    block = parse_block(data); forest = match_forest(block); nodes = block.instructions
    children = forest['children']; users = forest['users']; window = block.window
    order = incumbent['original_order']; original_output = incumbent['output']['optimized_instructions']
    if sorted(order) != list(range(len(nodes))): raise ValueError('Incumbent needs complete original permutation')
    if not 0 <= parent < len(nodes) or len(children[parent]) != 2: raise ValueError('Binary parent required')
    subtrees = []
    for node in nodes:
        subtree = {node.index}
        for child in children[node.index]: subtree.update(subtrees[child])
        subtrees.append(subtree)
    members = subtrees[parent]; ranks = {node: position for position, node in enumerate(order)}
    start = min(ranks[node] for node in members); stop = max(ranks[node] for node in members)
    if stop - start + 1 != len(members) or order[stop] != parent:
        raise ValueError('Pair subtree must be contiguous in the saved original order')
    sides = tuple(tuple(node for node in order[start:stop] if node in subtrees[child])
                  for child in children[parent])
    if not any(any(len(children[node]) == 2 for node in side) for side in sides):
        raise ValueError('At least one side must contain a binary branch')
    # Retain the exact incumbent physical prefix, including its COPY history.
    prefix = []; history = []; done = set(); cursor = 0; latest = {}
    for row in original_output:
        check()
        if cursor == start: break
        position = len(prefix)
        if row['op'] == 'COPY':
            distance = int(row['source'][2:]); identity = history[position - distance]
            if not 1 <= distance <= window or identity is None: raise ValueError('Bad incumbent prefix COPY')
        else:
            identity = order[cursor]; cursor += 1; done.add(identity)
            if row['op'] != nodes[identity].op: raise ValueError('Incumbent prefix mismatch')
            if row['op'] == 'SET': identity = None
        prefix.append(dict(row)); history.append(identity)
        if identity is not None: latest[identity] = position
    if cursor != start: raise ValueError('Incomplete physical prefix')
    external = tuple(sorted(node for node in done if any(user not in done for user in users[node])))
    if any(node in members for node in external): raise AssertionError('Contiguous subtree starts with preborn member')
    initial_ages = tuple(len(prefix) - latest[node] for node in external)
    if any(not 1 <= age <= window for age in initial_ages): raise ValueError('Expired incumbent external')
    k = len(external); lengths = tuple(map(len, sides)); states = 0
    active_cache = {}

    def active(left, right):
        key = left, right
        if key not in active_cache:
            born = set(sides[0][:left]) | set(sides[1][:right])
            active_cache[key] = tuple(sorted(node for node in born if any(user not in born for user in users[node])))
        return active_cache[key]

    frontier = {(0, 0, initial_ages): (0, None)}
    for progress in range(sum(lengths)):
        following = {}
        for (left, right, ages), (cost, path) in frontier.items():
            check()
            if states >= max_states: raise BudgetExceeded('Fixed tree pair state budget exhausted')
            states += 1; prefixes = left, right; live = external + active(left, right)
            for side in (0, 1):
                if prefixes[side] == lengths[side]: continue
                node = sides[side][prefixes[side]]; operands = set(nodes[node].args)
                if not operands <= set(live): raise AssertionError('Fixed side is not topological')
                consume = {live.index(source) for source in operands}
                transition = _advance(ages, consume, True, window)
                if transition is None: continue
                extra, after = transition
                retained = tuple(source for source in live if source not in operands) + (node,)
                ages_by_role = dict(zip(retained, after)); updated = list(prefixes); updated[side] += 1
                next_live = external + active(*updated)
                if set(next_live) != set(retained): raise AssertionError('Live role restoration mismatch')
                state = (*updated, tuple(ages_by_role[source] for source in next_live))
                value = cost + extra, (path, (side, prefixes[side]))
                if state not in following or value[0] < following[state][0]: following[state] = value
        frontier = following
        if not frontier: raise InfeasibleSchedule('Fixed pair deadline candidates empty; not global proof')
    outlets = []
    for (left, right, ages), (cost, path) in frontier.items():
        check(); live = external + active(left, right)
        consume = {live.index(source) for source in set(nodes[parent].args)}
        transition = _advance(ages, consume, True, window)
        if transition is None: continue
        extra, after = transition; sequence = []
        while path is not None:
            path, action = path; sequence.append(action)
        outlets.append((cost + extra, after, tuple(reversed(sequence))))
    if not outlets: raise InfeasibleSchedule('Fixed pair parent cannot issue; not global proof')
    outlets.sort(key=lambda item: (item[0], sum(item[1]), item[1]))
    truncated = max(0, len(outlets) - max_outcomes); results = []
    for local_cost, outlet_ages, actions in outlets[:max_outcomes]:
        check(); pair_order = [sides[side][offset] for side, offset in actions] + [parent]
        proposed = order[:start] + pair_order + order[stop + 1:]
        rows = [dict(row) for row in prefix]
        live = {node: latest[node] for node in external}; completed = set(done); local_copies = 0
        for rank, node_index in enumerate(proposed[start:], start=start):
            check(); node = nodes[node_index]; operands = set(node.args)
            if not (set(node.args) | set(node.order_deps)) <= completed: raise AssertionError('Restored order dependency mismatch')
            while live and max(len(rows) - position for position in live.values()) == window:
                oldest = min(live, key=live.get)
                if oldest in operands: break
                rows.append({'id': len(rows), 'op': 'COPY', 'source': f't#{len(rows) - live[oldest]}'})
                live[oldest] = len(rows) - 1
                if rank <= stop: local_copies += 1
                check()
            if any(not 1 <= len(rows) - live[source] <= window for source in operands):
                raise AssertionError('Restored operand expired')
            row = {'id': len(rows), 'op': node.op}
            if node.reg is not None: row['reg'] = node.reg
            if node.args: row['inputs'] = [f't#{len(rows) - live[source]}' for source in node.args]
            rows.append(row); completed.add(node_index)
            for source in operands: del live[source]
            if any(user not in completed for user in users[node_index]): live[node_index] = len(rows) - 1
        if local_copies != local_cost: raise AssertionError('DP/emitted local COPY differs')
        copies = sum(row['op'] == 'COPY' for row in rows)
        output = {'block_id': block.block_id, 'optimized_instructions': rows}
        results.append({'output': output, 'original_order': proposed, 'copies': copies,
                        'local_copies': local_cost, 'outlet_ages': outlet_ages})
    best = min(results, key=lambda item: item['copies']); check()
    return {'best': best, 'completed_outlets': results, 'stats': {
        'parent': parent, 'sides': sides, 'rank_interval': (start, stop),
        'external_roles': external, 'external_ages': initial_ages,
        'states': states, 'outlets': len(outlets), 'truncated_outlets': truncated,
        'elapsed_ms': (perf_counter() - started) * 1000,
        'scope': 'Fixed side original orders, deadline COPY, exact role ages; explicit candidate, not global proof'}}
