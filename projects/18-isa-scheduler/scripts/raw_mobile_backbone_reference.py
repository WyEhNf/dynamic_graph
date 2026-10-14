"""Source-only independent N<=9 physical-ring reference, no project imports.

This Dijkstra reference allows early COPY and every old/new physical replica.
Only original identity + raw window histories are states. A closed negative is
scoped to the requested mobile/backbone neighborhood, not unrestricted DAGs.
There is no CLI and no import-time solve. Execution awaits the reviewed runner.
"""
import heapq
import re
from time import perf_counter


def raw_graph(data):
    if set(data) != {'block_id', 'bit_width', 'instructions'}:
        raise ValueError('Unsupported raw block fields')
    if type(data['bit_width']) is not int or not 2 <= data['bit_width'] <= 5:
        raise ValueError('Bits2..5 required')
    rows = data['instructions']
    if not 1 <= len(rows) <= 9:
        raise ValueError('Independent raw reference N1..9 only')
    ids, args, deps = set(), [], []
    for index, row in enumerate(rows):
        identity = row.get('id', index)
        if type(identity) not in (int, str) or identity in ids:
            raise ValueError('Invalid external ID; identity is array position')
        ids.add(identity)
        op = row.get('op')
        if op not in ('GET', 'SET', 'ADD', 'MULW'):
            raise ValueError('Unsupported original opcode, including COPY')
        allowed = {'id', 'op', 'inputs'} | ({'reg'} if op in ('GET', 'SET') else set())
        if set(row) - allowed:
            raise ValueError('Unknown original instruction fields')
        tokens = row.get('inputs', [])
        if not isinstance(tokens, list) or len(tokens) != {'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}[op]:
            raise ValueError('Invalid original arity')
        sources = []
        for token in tokens:
            if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token):
                raise ValueError('Invalid raw t#')
            source = index - int(token[2:])
            if source < 0 or rows[source]['op'] == 'SET':
                raise ValueError('Invalid original identity reference')
            sources.append(source)
        previous = set(sources)
        if op in ('GET', 'SET'):
            reg = row.get('reg')
            if not isinstance(reg, str) or not reg:
                raise ValueError('Invalid register')
            # Pairwise memory relations are independent of production parser.
            for earlier, old in enumerate(rows[:index]):
                if old['op'] in ('GET', 'SET') and old['reg'] == reg and (op == 'SET' or old['op'] == 'SET'):
                    previous.add(earlier)
        args.append(tuple(sources))
        deps.append(previous)
    return rows, args, deps, 1 << data['bit_width']


def validate_initial(data, candidate, graph):
    rows, args, deps, width = graph
    order = candidate['original_order']
    if len(order) != len(rows) or set(order) != set(range(len(rows))):
        raise ValueError('Initial original-order permutation missing')
    emitted, ring, prefixes, slots = set(), (), [], []
    cursor = copies = 0
    physical = candidate['output']['optimized_instructions']
    if candidate['output']['block_id'] != data['block_id']:
        raise ValueError('Wrong initial block ID')
    for position, row in enumerate(physical):
        if row.get('id') != position:
            raise ValueError('Invalid physical ID')
        if row['op'] == 'COPY':
            token = row.get('source')
            if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token):
                raise ValueError('Invalid initial COPY token')
            distance = int(token[2:])
            if not 1 <= distance <= len(ring) or ring[-distance] is None:
                raise ValueError('Initial COPY outside window or of SET')
            identity = ring[-distance]
            copies += 1
        else:
            if cursor >= len(order):
                raise ValueError('Too many originals')
            node = order[cursor]
            if row['op'] != rows[node]['op'] or row.get('reg') != rows[node].get('reg') or not deps[node] <= emitted:
                raise ValueError('Initial operation/register/hazard mismatch')
            observed = []
            for token in row.get('inputs', []):
                if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token):
                    raise ValueError('Invalid physical operand')
                distance = int(token[2:])
                if not 1 <= distance <= len(ring):
                    raise ValueError('Initial reference outside window')
                observed.append(ring[-distance])
            if tuple(observed) != args[node]:
                raise ValueError('Initial ordered identity mismatch')
            # Prefix ending immediately before this original includes preceding COPY.
            prefixes.append((position, frozenset(emitted), ring, copies))
            slots.append(position)
            emitted.add(node)
            cursor += 1
            identity = None if rows[node]['op'] == 'SET' else node
        ring = (ring + (identity,))[-width:]
    if cursor != len(rows) or copies != candidate['copies']:
        raise ValueError('Incomplete initial or wrong COPY cost')
    return prefixes


def solve_mobile_raw(data, incumbent, region, *, max_states=20000,
        max_discovered=20000, max_transitions=20000, time_budget_ms=500):
    started = perf_counter()
    if min(max_states, max_discovered, max_transitions, time_budget_ms) <= 0:
        raise ValueError('Positive finite budgets required')
    graph = raw_graph(data)
    rows, args, deps, width = graph
    n = len(rows)
    prefixes = validate_initial(data, incumbent, graph)
    if set(region) != {'L', 'R', 'mobile'}:
        raise ValueError('Invalid region fields')
    left, right, mobile = region['L'], region['R'], tuple(region['mobile'])
    order = tuple(incumbent['original_order'])
    rank = {node: index for index, node in enumerate(order)}
    if type(left) is not int or type(right) is not int or not 0 <= left <= right < n:
        raise ValueError('Invalid interval')
    if not mobile or len(set(mobile)) != len(mobile) or any(type(node) is not int or node not in rank or not left <= rank[node] <= right for node in mobile):
        raise ValueError('Invalid mobile originals')
    backbone = tuple(node for node in order[left:right + 1] if node not in mobile)
    suffix = order[right + 1:]
    prefix_length, prefix_done, ring, prefix_cost = prefixes[left]
    initial_mask = sum(1 << node for node in prefix_done)
    first = (initial_mask, 0, 0, ring)
    # Immutable labels preserve path versions if a state is improved later.
    labels = [(first, prefix_cost, None, None, None)]
    best = {first: 0}
    heap = [(prefix_cost, 0)]
    expansions = transitions = stale = 0
    goal = None
    outcome = 'closed_neighborhood_infeasible'
    interrupted = None
    while heap:
        if expansions >= max_states or (perf_counter() - started) * 1000 >= time_budget_ms:
            outcome = 'unknown_budget'
            break
        cost, version = heapq.heappop(heap)
        state, _, _, _, _ = labels[version]
        if best.get(state) != version:
            stale += 1
            continue
        mask, bc, sc, history = state
        if mask == (1 << n) - 1:
            goal, outcome = version, 'optimal_neighborhood'
            break
        expansions += 1
        done = {node for node in range(n) if mask & (1 << node)}
        if set(mobile) <= done and bc == len(backbone):
            candidates = [] if sc == len(suffix) else [suffix[sc]]
        else:
            candidates = [node for node in mobile if node not in done]
            if bc < len(backbone):
                candidates.append(backbone[bc])
        actions = []
        for node in candidates:
            if not deps[node] <= done or any(source not in history for source in args[node]):
                continue
            row = {'op': rows[node]['op']}
            if row['op'] in ('GET', 'SET'):
                row['reg'] = rows[node]['reg']
            if args[node]:
                row['inputs'] = [f't#{len(history)-max(i for i,value in enumerate(history) if value == source)}' for source in args[node]]
            next_bc = bc + int(bc < len(backbone) and node == backbone[bc])
            next_sc = sc + int(sc < len(suffix) and node == suffix[sc])
            identity = None if row['op'] == 'SET' else node
            after = (mask | (1 << node), next_bc, next_sc, (history + (identity,))[-width:])
            actions.append((after, 0, row, node))
        # EVERY physical replica is represented, including nonlatest/dead;
        # early copies unrestricted. Equal identity/ring successors may merge.
        for offset, identity in enumerate(history):
            if identity is not None:
                after = (mask, bc, sc, (history + (identity,))[-width:])
                actions.append((after, 1, {'op': 'COPY', 'source': f't#{len(history)-offset}'}, None))
        for action_cursor, (after, delta, row, node) in enumerate(actions):
            if transitions >= max_transitions or (perf_counter() - started) * 1000 >= time_budget_ms:
                outcome = 'unknown_transition_or_time_budget'
                interrupted = {'label_version': version, 'next_action_cursor': action_cursor, 'action_count': len(actions)}
                break
            transitions += 1
            candidate_cost = cost + delta
            previous = best.get(after)
            if previous is not None and labels[previous][1] <= candidate_cost:
                continue
            if previous is None and len(best) >= max_discovered:
                outcome = 'unknown_discovery_budget'
                interrupted = {'label_version': version, 'next_action_cursor': action_cursor, 'action_count': len(actions)}
                break
            next_version = len(labels)
            labels.append((after, candidate_cost, version, row, node))
            best[after] = next_version
            heapq.heappush(heap, (candidate_cost, next_version))
        if interrupted is not None:
            break
    candidate = None
    if goal is not None:
        path, issued, version = [], [], goal
        while labels[version][2] is not None:
            _, _, parent, row, node = labels[version]
            path.append(row)
            if node is not None:
                issued.append(node)
            version = parent
        path.reverse()
        issued.reverse()
        physical = [dict(row) for row in incumbent['output']['optimized_instructions'][:prefix_length]] + path
        for index, row in enumerate(physical):
            row['id'] = index
        candidate = {'output': {'block_id': data['block_id'], 'optimized_instructions': physical},
                     'original_order': list(order[:left]) + issued, 'copies': labels[goal][1]}
    return {'outcome': outcome, 'candidate': candidate, 'expanded_states': expansions,
            'discovered_states': len(best), 'immutable_label_count': len(labels), 'attempted_transitions': transitions,
            'stale': stale, 'unfinished': interrupted, 'remaining_heap': len(heap),
            'elapsed_ms': (perf_counter() - started) * 1000,
            'scope': 'N<=9 exact raw ring + strict identities + this mobile/backbone/fixed-prefix/fixed-suffix order. Early/old COPY included. Unknown never proof.'}
