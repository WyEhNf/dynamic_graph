"""Fixed-backbone future-copy lower bound with exact bitset membership.

A separate optimized implementation preserves the old frozen search. Completed
sets and direct-user differences use exact integer masks. Physical actions and
frontier evidence keep the same representation for independent replay.
"""
import json
import heapq
from time import perf_counter

from .general_region_anytime import RegionAgenda, RegionStop, _prepare, _prefix, resource_layout as old_layout


def resource_layout(data, incumbent):
    layout = dict(old_layout(data, incumbent))
    n, w = layout['N'], layout['W']
    maximum = layout['whole_rows_bound_F_plus_NW']
    roles = tuple((max(0, n - 1), w) for _ in range(w))
    label = {'kind': 'immutable_label', 'label_version': 20063, 'done_mask': 2**32 - 1,
             'backbone_cursor': n, 'roles': roles, 'g': maximum, 'h': n,
             'predecessor_label': 20063, 'action': max(0, n - 1)}
    opened = dict(label, kind='unfinished_expansion', phase='prepare_neighbors',
                  next_ready_cursor=33, buffered_unpublished=33,
                  reason='producer_resource_reserve_after_saved_complete')
    encode = lambda row: len(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()) + 1
    layout['label_record_bound_bytes'] = encode(label)
    layout['open_record_bound_bytes'] = encode(opened)
    # Up to64 headers each contain actual <=32 mobile IDs; backbone can be
    # reconstructed from initial order/L/R, and is never serialized into labels.
    layout['scope'] += ' Mobile cursor included; all graph/identifier/proposal bounds remain real-input based.'
    return layout


def prepare_mobile(data, incumbent, check):
    graph = _prepare(data, incumbent, check)
    graph['layout'] = resource_layout(data, incumbent)
    if graph['layout']['label_record_bound_bytes'] > 1024 or graph['layout']['open_record_bound_bytes'] > 2048:
        raise ValueError('serialized_mobile_record_size_unsupported')
    graph['raw_data'], graph['incumbent'] = data, incumbent
    graph['dependency_masks'], graph['user_masks'] = [], []
    for node, users in zip(graph['nodes'], graph['users']):
        check()
        graph['dependency_masks'].append(sum(1 << dep for dep in set(node.args) | set(node.order_deps)))
        graph['user_masks'].append(sum(1 << user for user in users))
    return graph



def _step_bits(graph, index, completed, roles, check):
    """Exact latest/deadline emission; completed and user sets are bitmasks."""
    node = graph['nodes'][index]
    width = graph['block'].window
    args = set(node.args)
    ages = dict(roles)
    after = completed | (1 << index)
    users = graph['user_masks']
    last = {source for source in args if users[source] & ~after == 0}
    if graph['dependency_masks'][index] & ~completed or not args <= ages.keys():
        return None
    emitted = []
    rotations = 0
    while ages and max(ages.values()) == width:
        check()
        oldest = min(ages, key=lambda source: (-ages[source], source))
        if oldest in last:
            break
        if rotations >= width:
            return None
        emitted.append({'op': 'COPY', 'source': f't#{ages[oldest]}'})
        ages = {source: age+1 for source, age in ages.items()}
        ages[oldest] = 1
        if max(ages.values()) > width:
            return None
        rotations += 1
    if any(not 1 <= ages[source] <= width for source in args):
        return None
    row = {'op': node.op}
    if node.reg is not None:
        row['reg'] = node.reg
    if node.args:
        row['inputs'] = [f't#{ages[source]}' for source in node.args]
    emitted.append(row)
    ages = {source: age+1 for source, age in ages.items() if source not in last}
    if users[index] & ~after:
        ages[index] = 1
    if any(age > width for age in ages.values()):
        return None
    return tuple(sorted(ages.items())), emitted


class MobileDiagnostics:
    def __init__(self, agenda, unfinished, region):
        self.agenda, self.unfinished, self.region = agenda, unfinished, region


def iter_mobile_frontier(diagnostics):
    """Only the producer calls this after search clock stops; no export scan in core."""
    agenda = diagnostics.agenda
    yield dict(kind='header', region=diagnostics.region,
               open_count=len(agenda.pending), labels=len(agenda.labels))
    for version, (state, g, h, predecessor, action) in enumerate(agenda.labels):
        yield {'kind': 'immutable_label', 'label_version': version, 'done_mask': state[0],
               'backbone_cursor': state[1], 'roles': state[2], 'g': g, 'h': h,
               'predecessor_label': predecessor, 'action': action}
    for state in agenda.pending:
        version = agenda.best[state]
        _, g, h, _, _ = agenda.labels[version]
        yield {'kind': 'open', 'done_mask': state[0], 'backbone_cursor': state[1],
               'roles': state[2], 'g': g, 'h': h, 'label_version': version}
    if diagnostics.unfinished is not None:
        yield dict(diagnostics.unfinished, kind='unfinished_expansion')


def search_mobile_backbone(data, incumbent, region, *, time_budget_ms=500,
        max_states=20000, max_transitions=20000, max_outcomes=16,
        absolute_deadline=None, on_completed=None, prepared=None):
    started = perf_counter()
    deadline = started + time_budget_ms / 1000
    if absolute_deadline is not None:
        deadline = min(deadline, absolute_deadline)
    if min(time_budget_ms, max_states, max_transitions, max_outcomes) <= 0:
        raise ValueError('Positive budgets required')
    agenda = RegionAgenda()
    bound_prunes = 0
    processed = attempted = goals = max_open = 0
    unfinished = current = first_goal = None
    phase, cursor, buffered = 'prepare', 0, []
    outcome = 'exhausted_improvement_search'
    best = dict(incumbent)
    best['copies'] = sum(row['op'] == 'COPY' for row in incumbent['output']['optimized_instructions'])
    upper = len(incumbent['output']['optimized_instructions'])

    def check():
        if perf_counter() >= deadline:
            raise RegionStop('total_deadline')

    def append_rows(rows, additions):
        for item in additions:
            check()
            rows.append(dict(item, id=len(rows)))

    try:
        graph = prepared if prepared is not None else prepare_mobile(data, incumbent, check)
        if graph['raw_data'] != data or graph['incumbent'] != incumbent:
            raise ValueError('Prepared mobile graph belongs to another input/incumbent')
        check()
        n, order = graph['n'], graph['order']
        if set(region) - {'L', 'R', 'mobile'}:
            raise ValueError('Unknown mobile region fields')
        left, right = region['L'], region['R']
        members = tuple(region['mobile'])
        if type(left) is not int or type(right) is not int or not 0 <= left <= right < n:
            raise ValueError('Invalid mobile region interval')
        if not 1 <= len(members) <= 32 or len(set(members)) != len(members):
            raise ValueError('Mobile originals must be unique and <=32')
        if any(type(node) is not int or not 0 <= node < n or not left <= graph['ranks'][node] <= right for node in members):
            raise ValueError('Mobile original outside interval')
        local = {node: rank for rank, node in enumerate(members)}
        full = (1 << len(members)) - 1
        backbone = tuple(node for node in order[left:right + 1] if node not in local)
        prefix, prefix_done, incoming = _prefix(graph, incumbent, left, check)
        prefix_mask = sum(1 << node for node in prefix_done)
        backbone_masks = [0]
        for node in backbone:
            check()
            backbone_masks.append(backbone_masks[-1] | (1 << node))
        fixed_positions = {node: pos for pos, node in enumerate(
            node for node in order[left:] if node not in local)}
        last_fixed_users = []
        for users in graph['users']:
            check()
            last_fixed_users.append(max((fixed_positions[user] for user in users
                                         if user in fixed_positions), default=-1))
        width = graph['block'].window

        def future_copy_bound(roles, cursor):
            # At least last_fixed_position - cursor fixed originals precede
            # this identity's final fixed consumer. One own COPY can reduce
            # its age by at most W-1; copies of other identities only add age.
            # Summing these per-identity requirements is therefore safe.
            total = 0
            for identity, age in roles:
                distance = last_fixed_users[identity] - cursor
                excess = age + distance - width
                if distance >= 0 and excess > 0:
                    total += (excess + width - 2) // (width - 1)
            return total

        class CopyBoundAgenda(RegionAgenda):
            def offer(self, state, g, h, predecessor, action):
                estimate = future_copy_bound(state[2], state[1])
                if g + h + estimate >= upper:
                    return False
                old = self.best.get(state)
                if old is not None and self.labels[old][1] <= g:
                    return False
                if state in self.expanded:
                    self.reopens += 1
                version = len(self.labels)
                self.labels.append((state,g,h,predecessor,action))
                self.best[state] = version
                self.pending.add(state)
                heapq.heappush(self.heap,(g+2*h+2*estimate,h,version))
                return True

        agenda = CopyBoundAgenda()
        agenda.offer((0, 0, incoming), len(prefix), n - left, None, None)
        phase = 'search'
        while agenda.heap:
            check()
            current = agenda.pop()
            if current is None:
                break
            version, state, g, h = current
            mask, backbone_cursor, roles = state
            if g + h + future_copy_bound(roles, backbone_cursor) >= upper:
                bound_prunes += 1
                continue
            completed = prefix_mask | backbone_masks[backbone_cursor]
            for node in members:
                check()
                if mask & (1 << local[node]):
                    completed |= 1 << node
            if mask == full and backbone_cursor == len(backbone):
                phase = 'restore_suffix'
                rows, path, label = [dict(row) for row in prefix], [], version
                while agenda.labels[label][3] is not None:
                    check()
                    _, _, _, parent, action = agenda.labels[label]
                    path.append(action)
                    label = parent
                path.reverse()
                live, issued = incoming, prefix_mask
                for index in path:
                    check()
                    moved = _step_bits(graph, index, issued, live, check)
                    if moved is None:
                        raise AssertionError('Mobile predecessor path cannot restore')
                    live, additions = moved
                    append_rows(rows, additions)
                    issued |= 1 << index
                if len(rows) != g or live != roles or issued != completed:
                    raise AssertionError('Exact mobile/backbone endpoint mismatch')
                for index in order[right + 1:]:
                    check()
                    moved = _step_bits(graph, index, issued, live, check)
                    if moved is None:
                        raise RegionStop('restricted_suffix_failure')
                    live, additions = moved
                    append_rows(rows, additions)
                    issued |= 1 << index
                proposed = list(order[:left]) + path + list(order[right + 1:])
                copies = len(rows) - n
                if issued != (1 << n) - 1 or len(proposed) != n or copies != sum(row['op'] == 'COPY' for row in rows):
                    raise AssertionError('Whole original+COPY objective mismatch')
                candidate = {'output': {'block_id': graph['block'].block_id, 'optimized_instructions': rows},
                             'original_order': proposed, 'copies': copies}
                goals += 1
                if first_goal is None:
                    first_goal = {'processed_states': processed, 'attempted_transitions': attempted,
                                  'search_emit_ms': (perf_counter() - started) * 1000}
                if len(rows) < upper:
                    best, upper = candidate, len(rows)
                if on_completed is not None:
                    on_completed(candidate)
                check()
                if goals >= max_outcomes:
                    raise RegionStop('complete_outlet_limit')
                phase = 'search'
                continue
            if processed >= max_states:
                raise RegionStop('state_budget')
            processed += 1
            phase, cursor, buffered = 'prepare_neighbors', 0, []
            candidates = [node for node in members if not mask & (1 << local[node])]
            if backbone_cursor < len(backbone):
                candidates.append(backbone[backbone_cursor])
            ready = []
            for index in candidates:
                check()
                node = graph['nodes'][index]
                if graph['dependency_masks'][index] & ~completed == 0:
                    ready.append(index)
            for cursor, index in enumerate(ready):
                check()
                if attempted >= max_transitions:
                    raise RegionStop('transition_budget')
                attempted += 1
                moved = _step_bits(graph, index, completed, roles, check)
                if moved is None:
                    continue
                next_roles, additions = moved
                ng, nh = g + len(additions), h - 1
                if ng + nh >= upper:
                    continue
                consumers = (graph['user_masks'][index] & ~(completed | (1 << index))).bit_count() if graph['nodes'][index].op == 'GET' else 0
                key = (len(additions) - 1, len(next_roles) - len(roles), consumers, graph['ranks'][index])
                next_mask = mask | (1 << local[index]) if index in local else mask
                next_cursor = backbone_cursor if index in local else backbone_cursor + 1
                buffered.append((key, index, next_mask, next_cursor, next_roles, ng, nh))
            phase = 'publish_neighbors'
            buffered.sort(key=lambda item: item[0])
            for cursor, (_, index, next_mask, next_cursor, next_roles, ng, nh) in enumerate(buffered):
                check()
                agenda.offer((next_mask, next_cursor, next_roles), ng, nh, version, index)
            agenda.expanded[state] = g
            max_open = max(max_open, len(agenda.pending))
            buffered, phase = [], 'search'
    except RegionStop as error:
        outcome = 'partial_outlet_limit' if str(error) == 'complete_outlet_limit' else 'partial_' + str(error)
        if current is not None:
            version, state, g, h = current
            unfinished = {'done_mask': state[0], 'backbone_cursor': state[1], 'roles': state[2],
                          'g': g, 'h': h, 'label_version': version, 'reason': str(error), 'phase': phase,
                          'next_ready_cursor': cursor,
                          'buffered_unpublished': len(buffered) if phase == 'prepare_neighbors' else max(0, len(buffered) - cursor)}
    return {'best': best, 'diagnostics': MobileDiagnostics(agenda, unfinished, dict(region)), 'stats': {
        'outcome': outcome, 'processed_states': processed, 'attempted_transitions': attempted,
        'accepted_labels': len(agenda.labels), 'complete_outputs': goals, 'first_complete': first_goal,
        'future_copy_bound_prunes': bound_prunes, 'reopens': agenda.reopens, 'stale': agenda.stale, 'max_open': max_open,
        'search_emit_ms': (perf_counter() - started) * 1000,
        'scope': 'Restricted mobile/backbone latest/deadline proposal family, not an optimality/infeasibility oracle.'}}
