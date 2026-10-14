"""Small raw-JSON oracles. No project parser, scheduler graph or emitter."""
import heapq
from itertools import product
from time import perf_counter


def raw_graph(data):
    rows = data['instructions']; args = []; deps = []; users = [set() for _ in rows]
    writes = {}; readers = {}
    for index, row in enumerate(rows):
        if row['op'] not in ('GET', 'SET', 'ADD', 'MULW'): raise ValueError('Unsupported original')
        sources = tuple(index - int(token[2:]) for token in row.get('inputs', []))
        if len(sources) != {'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}[row['op']]: raise ValueError('Bad arity')
        if any(not 0 <= s < index or rows[s]['op'] == 'SET' for s in sources): raise ValueError('Bad source')
        dependency = set(sources)
        for source in set(sources): users[source].add(index)
        if row['op'] in ('GET', 'SET'):
            register = row['reg']
            if register in writes: dependency.add(writes[register])
            if row['op'] == 'GET': readers.setdefault(register, set()).add(index)
            else:
                dependency.update(readers.get(register, set())); readers[register] = set(); writes[register] = index
        args.append(sources); deps.append(sum(1 << s for s in dependency))
    return args, deps, [sum(1 << c for c in us) for us in users]


def raw_optimum(data, *, budget_ms=500, max_states=20000):
    tick = perf_counter(); deadline = tick + budget_ms / 1000
    args, deps, users = raw_graph(data); n = len(args); full = (1 << n) - 1; window = 2 ** data['bit_width']
    initial = (0, (0,) * n); costs = {initial: 0}; queue = [(0, 0, initial)]; serial = explored = 0
    while queue:
        if perf_counter() >= deadline or explored >= max_states:
            return {'status': 'unknown_budget', 'states': len(costs), 'explored': explored}
        cost, _, state = heapq.heappop(queue)
        if costs[state] != cost: continue
        done, ages = state; explored += 1
        if done == full:
            return {'status': 'optimal_under_identity_model', 'copies': cost, 'states': len(costs), 'explored': explored}
        live = [i for i, age in enumerate(ages) if age]
        actions = [(i, False) for i in range(n) if not done >> i & 1 and deps[i] & done == deps[i]
                   and all(ages[s] for s in args[i])]
        actions += [(i, True) for i in live if ages[i] > 1]
        for original, copy in actions:
            after = done if copy else done | 1 << original; next_ages = [0] * n; legal = True
            for source in live:
                if users[source] & ~after:
                    age = 1 if copy and source == original else ages[source] + 1
                    if age > window: legal = False; break
                    next_ages[source] = age
            if not legal: continue
            if not copy and users[original] & ~after: next_ages[original] = 1
            following = (after, tuple(next_ages)); next_cost = cost + int(copy)
            if next_cost < costs.get(following, float('inf')):
                costs[following] = next_cost; serial += 1; heapq.heappush(queue, (next_cost, serial, following))
    return {'status': 'closed_identity_infeasible', 'states': len(costs), 'explored': explored}


def dfs_deadline_optimum(data, *, max_orders=65536):
    """Exhaust all DFS child orientations, using independently coded relays."""
    args, deps, users = raw_graph(data); rows = data['instructions']; window = 2 ** data['bit_width']
    children = [tuple(dict.fromkeys(a)) for a in args]
    binary = [i for i, cs in enumerate(children) if len(cs) == 2]
    if 2 ** len(binary) > max_orders: return {'status': 'unknown_order_limit'}
    best = None; tested = valid = 0
    roots = [i for i, row in enumerate(rows) if row['op'] == 'SET']
    unused = [i for i, row in enumerate(rows) if row['op'] == 'GET' and not users[i]]
    for choices in product((False, True), repeat=len(binary)):
        flips = dict(zip(binary, choices)); order = []
        for root in roots:
            stack = [(root, False)]
            while stack:
                node, finish = stack.pop()
                if finish: order.append(node); continue
                stack.append((node, True)); cs = children[node]
                if flips.get(node): cs = tuple(reversed(cs))
                stack.extend((child, False) for child in reversed(cs))
        order += unused; tested += 1
        if len(order) != len(rows) or len(set(order)) != len(rows): raise ValueError('Not a forest')
        live = {}; position = cost = done = 0; legal = True
        for node in order:
            if deps[node] & done != deps[node]: legal = False; break
            relays = 0
            while live:
                oldest = min(live, key=live.get); age = position - live[oldest]
                if age < window or oldest in args[node]: break
                if age > window or relays >= window: legal = False; break
                live[oldest] = position; position += 1; cost += 1; relays += 1
            if not legal: break
            if any(source not in live or not 1 <= position - live[source] <= window for source in args[node]): legal = False; break
            for source in set(args[node]): del live[source]
            done |= 1 << node
            if users[node] & ~done: live[node] = position
            position += 1
        if legal:
            valid += 1; best = cost if best is None else min(best, cost)
    return {'status': 'complete_DFS_deadline_family', 'copies': best, 'orders': tested, 'valid_orders': valid}
