"""Tree DFS candidate extended with exact two-unary-chain age interleaving.

The screened forest has no shared data or register hazards. Cached plans are
role-relative subtree decisions, never original IDs or reordered arithmetic
arguments. Latest-age timing uses only deadline relays: this is a candidate
family, not global COPY optimality, nor proof when the family cannot progress.
"""
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule


def match_forest(block):
    nodes = block.instructions
    if block.window < 2: raise ValueError('Tree age search requires W>=2')
    if any(n.op not in ('GET', 'SET', 'ADD', 'MULW') for n in nodes):
        raise ValueError('Only GET/SET/ADD/MULW originals supported')
    gets = [n.reg for n in nodes if n.op == 'GET']
    sets = [n.reg for n in nodes if n.op == 'SET']
    if len(set(gets)) != len(gets) or len(set(sets)) != len(sets) or set(gets) & set(sets):
        raise ValueError('Tree search requires unique disjoint read/write registers')
    if any(n.order_deps for n in nodes): raise ValueError('Tree search does not absorb memory hazards')
    users = [[] for _ in nodes]
    children = [tuple(dict.fromkeys(n.args)) for n in nodes]
    for n in nodes:
        for source in children[n.index]:
            if nodes[source].op == 'SET': raise ValueError('SET has no temporary identity')
            users[source].append(n.index)
    if any(len(us) > 1 for us in users): raise ValueError('Shared values require general DAG strategy')
    if any(not users[n.index] and n.op not in ('SET', 'GET') for n in nodes):
        raise ValueError('Dead arithmetic is outside complete forest matcher')
    # Structural resource classes include ordered child roles. Cache reuse does
    # not exchange arithmetic operands or collapse equal original identities.
    classes = {}; shapes = []; depth = []; work = []; demand = []
    for n in nodes:
        key = (n.op, tuple(shapes[c] for c in children[n.index]), len(n.args))
        shapes.append(classes.setdefault(key, len(classes)))
        depth.append(1 + max((depth[c] for c in children[n.index]), default=0))
        work.append(1 + sum(work[c] for c in children[n.index]))
        needs = sorted((demand[c] for c in children[n.index]), reverse=True)
        demand.append(max((need + offset for offset, need in enumerate(needs)), default=1))
    roots = [n.index for n in nodes if n.op == 'SET']
    unused = [n.index for n in nodes if n.op == 'GET' and not users[n.index]]
    return {'children': children, 'users': users, 'shapes': shapes,
            'roots': roots, 'unused': unused, 'depth': max(depth, default=0), 'work': work, 'demand': demand}


def _advance(ages, consumed, produce, window):
    """Latest-age transition; every COPY and original advances physical slots."""
    current = list(ages); copies = 0
    while current and max(current) == window:
        oldest = current.index(window)
        if oldest in consumed: break
        if copies >= window: return None
        current = [1 if j == oldest else age + 1 for j, age in enumerate(current)]
        copies += 1
    if any(age > window for age in current): return None
    following = tuple(age + 1 for j, age in enumerate(current) if j not in consumed)
    if produce: following += (1,)
    if any(age > window for age in following): return None
    return copies, following


def schedule_tree_pipeline(block, *, time_budget_ms=500, max_states=20000, max_outcomes=16,
                      max_depth=120):
    """Budgeted memo DP over DFS order and deadline-relay physical ages.

    Exhaustion raises BudgetExceeded. Truncation is explicitly recorded and
    never proves optimality; failures only describe this restricted candidate.
    Total deadline includes matching, plan restoration and emission.
    """
    started = perf_counter()
    if time_budget_ms <= 0 or max_states <= 0 or max_outcomes <= 0:
        raise ValueError('Positive time/state/outcome budgets required')
    deadline = started + time_budget_ms / 1000
    forest = match_forest(block)
    if forest['depth'] > max_depth: raise ValueError('Tree depth exceeds safe DP scope')
    nodes = block.instructions; children = forest['children']; window = block.window
    memo = {}; states = truncated = 0; pair_contexts = pair_states = 0
    pair_chains = {}
    for index, kids in enumerate(children):
        if len(kids) != 2: continue
        chains = []
        for child in kids:
            backward = []; current = child
            while nodes[current].op in ('ADD', 'MULW') and len(children[current]) == 1:
                backward.append(current); current = children[current][0]
            if nodes[current].op != 'GET': break
            backward.append(current); chains.append(tuple(reversed(backward)))
        if len(chains) == 2: pair_chains[index] = tuple(chains)

    def check():
        if perf_counter() >= deadline: raise BudgetExceeded('Tree age total time budget exhausted')

    def pair_candidates(index, external):
        nonlocal states, pair_states, pair_contexts
        pair_contexts += 1; chains = pair_chains[index]
        lengths = tuple(len(chain) for chain in chains); k = len(external)
        # Acyclic two-prefix lattice. Equal prefix/physical-age states merge;
        # no age dominance, numerical alias or outside-consumer ordering merge.
        frontier = {(0, 0, external): (0, None)}
        for progress in range(sum(lengths)):
            following = {}
            for (left, right, ages), (cost, path) in frontier.items():
                check()
                if states >= max_states: raise BudgetExceeded('Tree pipeline state budget exhausted')
                states += 1; pair_states += 1; prefixes = (left, right)
                for role in (0, 1):
                    if prefixes[role] >= lengths[role]: continue
                    active = [r for r in (0, 1) if prefixes[r]]
                    consumed = {k + active.index(role)} if prefixes[role] else set()
                    step = _advance(ages, consumed, True, window)
                    if step is None: continue
                    extra, after = step; new_prefixes = list(prefixes); new_prefixes[role] += 1
                    # _advance appends the emitted role. Restore explicit
                    # external/A/B role slots before storing the next state.
                    retained_roles = [r for r in active if r != role]
                    role_ages = {r: after[k + offset] for offset, r in enumerate(retained_roles)}
                    role_ages[role] = after[-1]
                    canonical = after[:k] + tuple(role_ages[r] for r in (0, 1) if new_prefixes[r])
                    state = (*new_prefixes, canonical); value = (cost + extra, (path, (role, prefixes[role])))
                    if state not in following or value[0] < following[state][0]: following[state] = value
            frontier = following
            if not frontier: return []
        results = []
        for (left, right, ages), (cost, path) in frontier.items():
            check(); step = _advance(ages, set(range(k, len(ages))), True, window)
            if step is None: continue
            extra, after = step; sequence = []
            while path is not None:
                path, action = path; sequence.append(action)
            results.append((cost + extra, after, ('pipeline', tuple(reversed(sequence)))))
        return results

    def solve(index, external):
        nonlocal states, truncated
        check(); key = (forest['shapes'][index], external)
        if key in memo: return memo[key]
        # Outside-subtree identities cannot be retired during this subtree.
        # Relaxing physical age to freely retained slots gives this necessary
        # pruning condition. It is internal pruning, not a new public proof.
        if forest['demand'][index] + len(external) > window:
            memo[key] = []; return memo[key]
        if states >= max_states: raise BudgetExceeded('Tree age state budget exhausted')
        states += 1; kids = children[index]; candidate = {}
        orientations = ((0, 1), (1, 0)) if len(kids) == 2 else (tuple(range(len(kids))),)
        for orientation in orientations:
            frontier = [(0, external, ())]
            for role in orientation:
                next_rows = {}
                for base, ages, plans in frontier:
                    for cost, after, plan in solve(kids[role], ages):
                        item = (base + cost, after, plans + ((role, plan),))
                        if after not in next_rows or item[0] < next_rows[after][0]: next_rows[after] = item
                frontier = list(next_rows.values())
                if len(frontier) > max_outcomes:
                    truncated += len(frontier) - max_outcomes
                    frontier.sort(key=lambda row: (row[0], sum(row[1]), row[1]))
                    frontier = frontier[:max_outcomes]
            for cost, ages, plans in frontier:
                consume = set(range(len(external), len(ages)))
                step = _advance(ages, consume, nodes[index].op != 'SET', window)
                if step is None: continue
                extra, after = step; item = (cost + extra, after, ('DFS', plans))
                if after not in candidate or item[0] < candidate[after][0]: candidate[after] = item
        if index in pair_chains:
            for item in pair_candidates(index, external):
                after = item[1]
                if after not in candidate or item[0] < candidate[after][0]: candidate[after] = item
        rows = sorted(candidate.values(), key=lambda row: (row[0], sum(row[1]), row[1]))
        if len(rows) > max_outcomes: truncated += len(rows) - max_outcomes
        memo[key] = rows[:max_outcomes]
        return memo[key]

    order = []; cost = 0
    for root in forest['roots']:
        result = solve(root, ())
        if not result: raise InfeasibleSchedule('Restricted tree DFS/relay candidates cannot progress; not global proof')
        root_cost, final_ages, plan = min(result, key=lambda row: row[0])
        assert not final_ages; cost += root_cost
        stack = [(root, plan, False)]
        while stack:
            check(); index, current_plan, finishing = stack.pop()
            if finishing: order.append(index); continue
            stack.append((index, current_plan, True))
            kind, payload = current_plan
            if kind == 'pipeline':
                for role, offset in reversed(payload):
                    stack.append((pair_chains[index][role][offset], None, True))
            else:
                for role, subplan in reversed(payload): stack.append((children[index][role], subplan, False))
    order.extend(forest['unused'])
    if len(order) != len(nodes) or len(set(order)) != len(nodes): raise AssertionError('Plan does not cover original forest')
    rows = []; live = {}; copies = 0
    for index in order:
        check(); node = nodes[index]; operands = set(node.args)
        while live and max(len(rows) - position for position in live.values()) == window:
            oldest = min(live, key=live.get)
            if oldest in operands: break
            if copies > window * max(1, len(nodes)): raise InfeasibleSchedule('Restricted relay emission exceeded safety bound')
            rows.append({'id': len(rows), 'op': 'COPY', 'source': f't#{len(rows) - live[oldest]}'})
            live[oldest] = len(rows) - 1; copies += 1; check()
        now = len(rows); row = {'id': now, 'op': node.op}
        if node.reg is not None: row['reg'] = node.reg
        if node.args: row['inputs'] = [f't#{now - live[arg]}' for arg in node.args]
        if any(now - live[arg] > window for arg in node.args): raise AssertionError('Plan expired operand')
        rows.append(row)
        for arg in operands: del live[arg]
        if forest['users'][index]: live[index] = now
    if copies != cost: raise AssertionError('Resource plan COPY cost differs from original-ID emitter')
    return {'block_id': block.block_id, 'optimized_instructions': rows, 'stats': {
        'strategy': 'tree_two_chain_pipeline', 'original_order': order, 'inserted_copy_count': copies,
        'original_instruction_count': len(nodes), 'optimized_instruction_count': len(rows),
        'copy_ratio_output': copies / len(rows) if rows else 0,
        'inserted_copy_ratio_original': copies / len(nodes) if nodes else 0,
        'max_back_distance': window, 'bit_width': block.bit_width,
        'elapsed_ms': (perf_counter() - started) * 1000,
        'tree_age': {'states': states, 'cached_contexts': len(memo), 'truncated_outcomes': truncated,
                     'max_outcomes': max_outcomes, 'pair_contexts': pair_contexts, 'pair_states': pair_states,
                     'scope': 'DFS with local two-unary-chain interleavings and deadline COPY; not global optimality'}}}
