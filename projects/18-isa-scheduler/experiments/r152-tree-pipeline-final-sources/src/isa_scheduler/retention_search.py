"""Bounded original-order feasibility search without physical-age states.

For distinct original identities and COPY-only relays, a completed mask fixes
the live set. An original may issue with <=W live identities after it; if the
pre-issue live set has W identities, it must last-consume at least one. Such
an order materializes via <=W-1 oldest-first relays per original. This bridge
concerns feasibility, not COPY optimality. No alias, reread, rewrite or spill.
"""
from time import perf_counter

from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded, InfeasibleSchedule


def find_retention_order(block, *, time_budget_ms=250, max_states=30000, prepared=None,
                         max_nodes=8192):
    if time_budget_ms <= 0 or max_states < 1 or max_nodes < 1:
        raise ValueError('Positive retention search budgets required')
    started = perf_counter(); deadline = started + time_budget_ms / 1000
    nodes = block.instructions; n = len(nodes); window = block.window
    if n > max_nodes:
        raise BudgetExceeded(f'Retention search limited to {max_nodes} originals')
    if any(node.op not in ('GET', 'SET', 'ADD', 'MULW') for node in nodes):
        raise InfeasibleSchedule('Retention search rejects unknown operations/original COPY; matcher failure only')
    prepared = prepared or PreparedGraph(block, time_budget_ms=time_budget_ms)
    if prepared.block is not block:
        raise ValueError('PreparedGraph belongs to another block')
    ranks, _ = prepared.demand(deadline)
    dependencies = [sum(1 << source for source in deps) for deps in prepared.deps]
    consumers = [sum(1 << user for user in users) for users in prepared.data_users]
    final = (1 << n) - 1
    initial_ready = sum(1 << index for index, deps in enumerate(dependencies) if not deps)
    seen = {0}; expanded = transitions = blocked_full = capacity_pruned = memo_hits = 0
    stored_choices = forced_dead = 0
    choice_limit = max(1024, min(200000, max_states * 4))

    def choices(done, live, ready):
        nonlocal transitions, blocked_full, capacity_pruned, memo_hits, forced_dead
        rows = []; undone = final ^ done; count = live.bit_count()
        while ready:
            bit = ready & -ready; ready ^= bit; index = bit.bit_length() - 1
            transitions += 1
            if transitions % 128 == 1 and perf_counter() >= deadline:
                raise BudgetExceeded('Retention order search time budget exhausted')
            following = done | bit
            if following in seen:
                memo_hits += 1; continue
            after_undone = undone ^ bit; killed = 0
            for source in prepared.args_unique[index]:
                if not consumers[source] & after_undone:
                    killed |= 1 << source
            if count == window and not killed:
                blocked_full += 1; continue
            following_live = live & ~killed
            produced = bool(consumers[index] & after_undone)
            if produced: following_live |= bit
            if following_live.bit_count() > window:
                capacity_pruned += 1; continue
            freed = killed.bit_count(); net = freed - produced
            if not produced:
                # Moving a legal ready original with no future data use earlier
                # only removes live uses/dependencies. It cannot increase any
                # later frontier. This is a feasibility-only compression; no
                # assertion about minimum COPY or earliest physical ages.
                forced_dead += 1
                return [((0,), index, following, following_live)]
            if stored_choices + len(rows) >= choice_limit:
                raise BudgetExceeded('Retention order search stored-choice budget exhausted')
            rows.append(((-net, int(nodes[index].op == 'GET'), ranks[index], index),
                         index, following, following_live))
        rows.sort(key=lambda row: row[0])
        return rows

    # Each stack frame owns a complete resource frontier; reversible original
    # scheduling is represented by immutable masks. No Python recursion depth.
    stack = [(0, 0, initial_ready, None, 0)]; order = []
    while stack:
        if perf_counter() >= deadline:
            raise BudgetExceeded('Retention order search time budget exhausted')
        done, live, ready, candidates, cursor = stack[-1]
        if done == final:
            return order, {'expanded_states': expanded, 'reached_masks': len(seen),
                'transitions': transitions, 'blocked_full_without_last_use': blocked_full,
                'capacity_pruned': capacity_pruned, 'memo_hits': memo_hits,
                'forced_dead_rows': forced_dead, 'stored_choice_limit': choice_limit,
                'search_elapsed_ms': (perf_counter() - started) * 1000,
                'outcome': 'constructive_retention_order',
                'scope': 'bounded feasibility DFS; not minimum COPY; full frontier requires a last use'}
        if candidates is None:
            if expanded >= max_states:
                raise BudgetExceeded('Retention order search state budget exhausted')
            expanded += 1; candidates = choices(done, live, ready)
            stored_choices += len(candidates)
            stack[-1] = (done, live, ready, candidates, 0)
        if cursor >= len(candidates):
            stored_choices -= len(candidates)
            stack.pop()
            if order: order.pop()
            continue
        _, index, following, following_live = candidates[cursor]
        stack[-1] = (done, live, ready, candidates, cursor + 1)
        if following in seen:
            memo_hits += 1; continue
        seen.add(following)
        following_ready = ready & ~(1 << index)
        for user in prepared.users[index]:
            if dependencies[user] & following == dependencies[user]:
                following_ready |= 1 << user
        order.append(index); stack.append((following, following_live, following_ready, None, 0))
    # This is exhaustive only for the actually explored supported model. Caller
    # must not confuse this status with a bounded run or a matcher rejection.
    error = InfeasibleSchedule('proven_infeasible_under_model: exhaustive retention-order masks '
                              'with dead-output feasibility dominance; '
                              f'original_identity COPY-only, n={n}, W={window}, states={expanded}')
    error.retention_certificate = {'kind': 'retention_order_dominance_closed_masks',
        'node_count': n, 'window': window, 'memory_order': block.memory_order,
        'original_order_dependencies': [list(node.order_deps) for node in nodes],
        'completed_masks_hex': [hex(mask) for mask in sorted(seen)],
        'scope': 'distinct original identities once; COPY-only; no original COPY/alias/reread/recompute/spill; '
                 'closed safe original transitions, ready dead output may dominate other choices'}
    raise error


def schedule_retention(block, *, time_budget_ms=250, max_states=30000, prepared=None):
    started = perf_counter(); deadline = started + time_budget_ms / 1000
    order, diagnostics = find_retention_order(block, time_budget_ms=time_budget_ms,
                                             max_states=max_states, prepared=prepared)
    candidate = emit_order(block, order, deadline=deadline)
    if candidate is None:
        raise AssertionError('Retention order bridge failed to materialize')
    candidate['stats'].update(strategy='retention', retention_search=diagnostics,
                             elapsed_ms=(perf_counter() - started) * 1000)
    return candidate
