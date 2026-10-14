"""Output-private shared-input incidence recognizer proposing a rook minor.

Pure GET/ADD/MULW/SET only. Memory ordering is not part of the minor graph.
The independent raw checker validates all branch sets and required rook edges;
only its result authorizes the declared distinct-original COPY-only bound.
Offline research, not enabled by any default optimizer.
"""
from math import isqrt
from time import perf_counter

THEOREM = 'https://arxiv.org/abs/1210.8205v2'


def propose_rook_minor(block, *, time_budget_ms=100):
    started = perf_counter(); deadline = started + time_budget_ms / 1000
    nodes = block.instructions; sinks = [node.index for node in nodes if node.op == 'SET']
    dimension = isqrt(len(sinks))
    if dimension < 2 or dimension * dimension != len(sinks): return None
    if any(node.op not in ('GET', 'SET', 'ADD', 'MULW') for node in nodes): return None
    owner = [0] * len(nodes)
    for offset, terminal in enumerate(sinks): owner[terminal] = 1 << offset
    for node in reversed(nodes):
        if node.index % 128 == 0 and perf_counter() >= deadline: return None
        if node.op == 'GET': continue
        if owner[node.index].bit_count() != 1: return None
        for source in set(node.args):
            if nodes[source].op == 'SET': return None
            owner[source] |= owner[node.index]
    footprints = {}
    for node in nodes:
        if node.op == 'GET' and owner[node.index]:
            footprints.setdefault(owner[node.index], []).append(node.index)
    if len(footprints) != 2 * dimension: return None
    if any(mask.bit_count() != dimension or len(roots) < dimension for mask, roots in footprints.items()): return None
    masks = sorted(footprints); first = masks[0]
    columns = [mask for mask in masks if mask != first and mask & first]
    rows = [mask for mask in masks if mask not in columns]
    if len(rows) != dimension or len(columns) != dimension: return None
    for group in (rows, columns):
        if any(left & right for i, left in enumerate(group) for right in group[i + 1:]): return None
        if sum(group) != (1 << len(sinks)) - 1: return None
    if any((row & col).bit_count() != 1 for row in rows for col in columns): return None
    cores = [[] for _ in sinks]
    for node in nodes:
        if node.op != 'GET': cores[owner[node.index].bit_length() - 1].append(node.index)
    branch_sets = []
    for i, row in enumerate(rows):
        for j, col in enumerate(columns):
            terminal = (row & col).bit_length() - 1
            members = cores[terminal] + [footprints[row][j], footprints[col][i]]
            branch_sets.append(sorted(members))
    return {'kind': 'rook_branch_sets_treewidth', 'dimension': dimension,
            'window': block.window, 'branch_sets': branch_sets,
            'treewidth_lower_bound': dimension * (dimension + 1) // 2 - 1,
            'theorem': THEOREM, 'theorem_location': 'Harvey-Wood v2 Theorem3, k=2',
            'elapsed_ms': (perf_counter() - started) * 1000,
            'scope': 'original data-edge undirected minor; distinct original identities emitted once, COPY-only; '
                     'no original COPY/alias/reread/recompute/spill; hazard edges excluded'}


def check_rook_minor(data, certificate):
    # This helper validates original JSON independently of parse_block. It
    # reads real data edges only, never scheduler ownership/membership hints.
    from .minor_bounds import raw_graph
    graph = raw_graph(data)
    if any(row['op'] not in ('GET', 'SET', 'ADD', 'MULW') for row in data['instructions']):
        raise ValueError('Rook proof excludes original COPY/unknown operations')
    d = certificate.get('dimension'); branch_sets = certificate.get('branch_sets')
    if certificate.get('kind') != 'rook_branch_sets_treewidth' or type(d) is not int or d < 2:
        raise ValueError('Invalid rook proof kind/dimension')
    if not isinstance(branch_sets, list) or len(branch_sets) != d * d:
        raise ValueError('Full d*d branch set array required')
    window = 2 ** data['bit_width']
    lower = d * (d + 1) // 2 - 1
    if certificate.get('window') != window or certificate.get('treewidth_lower_bound') != lower:
        raise ValueError('Rook window/theorem bound mismatch')
    allocated = {}; sets = []
    for coordinate, members in enumerate(branch_sets):
        if not isinstance(members, list) or not members or len(members) != len(set(members)):
            raise ValueError('Nonempty unique branch members required')
        selected = set(members)
        for member in members:
            if type(member) is not int or member not in graph or member in allocated:
                raise ValueError('Branch sets overlap or contain invalid originals')
            allocated[member] = coordinate
        stack = [members[0]]; reached = {members[0]}
        while stack:
            current = stack.pop()
            for neighbor in graph[current] & selected - reached:
                reached.add(neighbor); stack.append(neighbor)
        if reached != selected: raise ValueError('Branch set is not connected on original data edges')
        sets.append(selected)
    edges = set()
    for vertex, first in allocated.items():
        for neighbor in graph[vertex]:
            second = allocated.get(neighbor)
            if second is not None and second != first: edges.add(tuple(sorted((first, second))))
    required = 0
    for first in range(d * d):
        for second in range(first + 1, d * d):
            if first // d == second // d or first % d == second % d:
                required += 1
                if (first, second) not in edges: raise ValueError('Required same-row/same-column rook edge is absent')
    return {'verified_rook_dimension': d, 'verified_required_edges': required,
            'verified_treewidth_lower_bound': lower,
            'verified_infeasible_under_original_identity_model': lower > window,
            'verified_branch_members': len(allocated), 'actual_minor_edges': len(edges),
            'scope': 'raw original data edges only; branch sets disjoint, connected, all rook adjacencies present; '
                     'Harvey-Wood Theorem3 k=2 plus live-before/current path bags; no alias/recompute/reread/spill'}
