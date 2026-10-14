"""Propose and raw-check resource graph symmetries; never rewrite operands.

Adjacent generators independently exchange row/column root groups and preserve
the other partition. This permits ordering group first-birth positions in a
feasibility model. Actual originals and ordered args are emitted unchanged.
"""
from collections import Counter
from math import isqrt
import re

from .closed_subgraph import projection_eligible


def check_matrix_symmetry(data, plan):
    rows = data['instructions']; count = len(rows)
    if any(row.get('op') not in ('GET', 'SET', 'ADD', 'MULW') for row in rows):
        raise ValueError('Pure supported originals required')
    parents = []
    for index, row in enumerate(rows):
        args = []
        for token in row.get('inputs', []):
            if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token):
                raise ValueError('Invalid original data token')
            source = index - int(token[2:])
            if not 0 <= source < index: raise ValueError('Original must reference earlier source')
            args.append(source)
        if len(args) != {'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}[row['op']]:
            raise ValueError('Original arity mismatch')
        parents.append(args)
    reads = [row.get('reg') for row in rows if row['op'] == 'GET']
    writes = [row.get('reg') for row in rows if row['op'] == 'SET']
    if (any(not isinstance(reg, str) or not reg for reg in reads + writes)
        or len(reads) != len(set(reads)) or len(writes) != len(set(writes)) or set(reads) & set(writes)):
        raise ValueError('Distinct disjoint register sets required; no memory hazards')
    axes = [plan.get('row_groups'), plan.get('column_groups')]
    d = plan.get('dimension')
    if type(d) is not int or d < 2 or plan.get('kind') != 'resource_matrix_adjacent_symmetries':
        raise ValueError('Invalid symmetry plan')
    allocated = set()
    for groups in axes:
        if not isinstance(groups, list) or len(groups) != d: raise ValueError('Expected d root groups')
        for group in groups:
            if not isinstance(group, list) or len(group) != d: raise ValueError('Expected d roots per group')
            for vertex in group:
                if type(vertex) is not int or not 0 <= vertex < count or vertex in allocated or rows[vertex]['op'] != 'GET':
                    raise ValueError('Root groups overlap or contain invalid roots')
                allocated.add(vertex)
    if allocated != {i for i, row in enumerate(rows) if row['op'] == 'GET'}:
        raise ValueError('Root groups must cover all originals GETs')
    for axis, name in enumerate(('row_generators', 'column_generators')):
        generators = plan.get(name)
        if not isinstance(generators, list) or len(generators) != d - 1:
            raise ValueError('Every adjacent transposition required')
        for pivot, mapping in enumerate(generators):
            if not isinstance(mapping, list) or any(type(v) is not int for v in mapping) or sorted(mapping) != list(range(count)):
                raise ValueError('Generator must be original permutation')
            for vertex, mapped in enumerate(mapping):
                if rows[vertex]['op'] != rows[mapped]['op'] or Counter(mapping[u] for u in parents[vertex]) != Counter(parents[mapped]):
                    raise ValueError('Generator is not a true resource data graph automorphism')
            for group_axis, groups in enumerate(axes):
                for offset, group in enumerate(groups):
                    target = pivot + 1 if offset == pivot else pivot if offset == pivot + 1 else offset
                    if group_axis != axis: target = offset
                    if {mapping[u] for u in group} != set(groups[target]):
                        raise ValueError('Generator must act on exactly the declared axis groups')
    return {'verified_dimension': d, 'verified_generators': 2 * (d - 1),
            'scope': 'Resource data graph automorphisms on all original nodes; pure distinct/disjoint registers; '
                     'root-group birth sorting only, actual ordered args/reg/op emitted unchanged; no COPY minimum claim'}


def block_data(block):
    rows = []
    for node in block.instructions:
        row = {'id': node.original_id, 'op': node.op}
        if node.reg is not None: row['reg'] = node.reg
        if node.args: row['inputs'] = [f't#{node.index - source}' for source in node.args]
        rows.append(row)
    return {'block_id': block.block_id, 'bit_width': block.bit_width, 'instructions': rows}


def propose_matrix_symmetry(block):
    if not projection_eligible(block): return None
    nodes = block.instructions; terminals = [node.index for node in nodes if node.op == 'SET']
    d = isqrt(len(terminals))
    if d < 2 or d * d != len(terminals): return None
    owner = [0] * len(nodes); users = [[] for _ in nodes]
    for offset, terminal in enumerate(terminals): owner[terminal] = 1 << offset
    for node in reversed(nodes):
        if node.op == 'GET': continue
        if owner[node.index].bit_count() != 1: return None
        for source in set(node.args): owner[source] |= owner[node.index]
    groups = {}
    for node in nodes:
        for source in set(node.args): users[source].append(node.index)
        if node.op == 'GET': groups.setdefault(owner[node.index], []).append(node.index)
    masks = sorted(groups)
    if len(masks) != 2 * d or any(mask.bit_count() != d or len(groups[mask]) != d for mask in masks): return None
    cols = [mask for mask in masks if mask != masks[0] and mask & masks[0]]
    rows = [mask for mask in masks if mask not in cols]
    if len(rows) != d or len(cols) != d: return None
    for partition in (rows, cols):
        if any(a & b for i, a in enumerate(partition) for b in partition[i + 1:]): return None
    if any((a & b).bit_count() != 1 for a in rows for b in cols): return None
    row_roots = {v for mask in rows for v in groups[mask]}; col_roots = {v for mask in cols for v in groups[mask]}
    # A layer is identified by the exact set of opposite-column GET identities
    # that each row GET multiplies. All rows must contain the same d layers.
    footprints = {}
    for root in row_roots:
        others = []
        for user in users[root]:
            node = nodes[user]
            if node.op != 'MULW' or len(set(node.args)) != 2: return None
            other = next((v for v in node.args if v != root), None)
            if other not in col_roots: return None
            others.append(other)
        if len(others) != d or len(set(others)) != d: return None
        footprints[root] = tuple(sorted(others))
    layers = sorted({footprints[v] for v in groups[rows[0]]})
    if len(layers) != d: return None
    labels = {}; axis_roots = [[], []]
    for i, mask in enumerate(rows):
        roots = sorted(groups[mask], key=lambda v: footprints[v])
        if [footprints[v] for v in roots] != layers: return None
        axis_roots[0].append(roots)
        for k, root in enumerate(roots): labels[('A', i, k)] = root
    for j, mask in enumerate(cols):
        roots = []
        for k, layer in enumerate(layers):
            matches = set(layer) & set(groups[mask])
            if len(matches) != 1: return None
            root = matches.pop(); roots.append(root); labels[('B', j, k)] = root
        if len(set(roots)) != d: return None
        axis_roots[1].append(roots)
    reference = None
    for i, rmask in enumerate(rows):
        for j, cmask in enumerate(cols):
            terminal = terminals[(rmask & cmask).bit_length() - 1]
            products = {}; additions = []; layer_for = {}
            for node in nodes:
                if node.op == 'MULW' and owner[node.index] == rmask & cmask:
                    matches = [k for k in range(d) if set(node.args) == {labels[('A', i, k)], labels[('B', j, k)]}]
                    if len(matches) != 1 or matches[0] in products: return None
                    k = matches[0]; products[k] = node.index; layer_for[node.index] = k
            if len(products) != d: return None
            current = nodes[terminal].args[0]; tail = []
            while nodes[current].op == 'ADD':
                a, b = nodes[current].args
                if a in layer_for and b in layer_for:
                    sequence = sorted((layer_for[a], layer_for[b])); additions.append(current); break
                previous, product = (a, b) if nodes[a].op == 'ADD' and b in layer_for else (b, a)
                if nodes[previous].op != 'ADD' or product not in layer_for: return None
                tail.append((layer_for[product], current)); current = previous
            else: return None
            for k, addition in reversed(tail): sequence.append(k); additions.append(addition)
            if sorted(sequence) != list(range(d)): return None
            if reference is None: reference = sequence
            elif sequence != reference: return None
            for k, product in products.items(): labels[('P', i, j, k)] = product
            for stage, addition in enumerate(additions): labels[('S', i, j, stage)] = addition
            labels[('T', i, j)] = terminal
    if len(labels) != len(nodes) or len(set(labels.values())) != len(nodes): return None
    plan = {'kind': 'resource_matrix_adjacent_symmetries', 'dimension': d,
            'row_groups': axis_roots[0], 'column_groups': axis_roots[1]}
    for axis, name in enumerate(('row_generators', 'column_generators')):
        generators = []
        for pivot in range(d - 1):
            mapping = [None] * len(nodes)
            for role, vertex in labels.items():
                target = list(role)
                coordinate = 1 if role[0] == 'A' else 1 if role[0] == 'B' else 1 + axis
                if role[0] in ('A', 'B') and ((axis == 0 and role[0] == 'B') or (axis == 1 and role[0] == 'A')):
                    mapped = role
                else:
                    value = target[coordinate]
                    target[coordinate] = pivot + 1 if value == pivot else pivot if value == pivot + 1 else value
                    mapped = tuple(target)
                mapping[vertex] = labels[mapped]
            generators.append(mapping)
        plan[name] = generators
    try: check_matrix_symmetry(block_data(block), plan)
    except ValueError: return None
    return plan
