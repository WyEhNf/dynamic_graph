"""Bounded physical-age search inside strict shared reduction columns.

Proposals preserve every original node and ordered operands; only original
instruction order and legal COPY relays change. Row-role symmetry merges search
states because screened rows have identical scheduling topology, not because
their values are equal. No alias or algebraic rewrite is performed. Greedy
relay transitions and column/beam boundaries restrict the search; this is not
a whole-DAG optimality or impossibility certificate.
"""
import heapq
from itertools import count
from time import perf_counter

from .local_order import emit_order
from .model import BudgetExceeded, InfeasibleSchedule
from .reduction_columns import recognize_reduction_columns, schedule_reduction_columns


def _step(stages, accumulators, temporaries, weight, born, action, *, first, last, window):
    """Exact expiry relay simulation; positive ages denote distinct live roles."""
    rows = len(stages)
    ages = list(accumulators) + list(temporaries) + [weight]
    stages = list(stages)
    row, operation = action
    if operation == 'weight':
        args, dead, result = set(), set(), 2 * rows
    elif operation == 'private':
        args, dead, result = set(), set(), rows + row
    elif operation == 'product':
        args = {rows + row, 2 * rows}
        # This weight's remaining original MUL consumers are reconstructed
        # from stages; no scheduler remaining-count state enters verification.
        weight_last = sum(stage < 2 for stage in stages) == 1
        dead = {rows + row} | ({2 * rows} if weight_last else set())
        result = row if first else rows + row
    elif operation == 'addition':
        args, dead, result = {row, rows + row}, {row, rows + row}, row
    else:
        args, dead, result = {row}, {row}, None
    copies = 0
    while True:
        live = [i for i, age in enumerate(ages) if age]
        if not live:
            break
        oldest = max(live, key=lambda i: ages[i])
        if ages[oldest] > window:
            return None
        if ages[oldest] < window or oldest in dead:
            break
        ages = [age + 1 if age else 0 for age in ages]
        ages[oldest] = 1
        copies += 1
        if copies >= window:
            return None
    if any(not 1 <= ages[source] <= window for source in args):
        return None
    for source in dead:
        ages[source] = 0
    ages = [age + 1 if age else 0 for age in ages]
    if result is not None:
        ages[result] = 1
    if operation == 'weight':
        born = True
    elif operation == 'private':
        stages[row] = 1
    elif operation == 'product':
        stages[row] = 3 if first else 2
    elif operation == 'addition':
        stages[row] = 3
    else:
        stages[row] = 4
    return tuple(stages), tuple(ages[:rows]), tuple(ages[rows:2 * rows]), ages[-1], born, copies


def _key(stages, accumulators, temporaries, weight, born):
    return tuple(sorted(zip(stages, accumulators, temporaries))), weight, born


def _column(frontier, column, plan, *, deadline, beam_width, max_states, max_pending, window):
    rows = len(plan['rows'])
    first, last = column == 0, column == plan['width'] - 1
    def progress(state):
        return int(state[4]) + sum((stage - 1 if first and stage >= 3 else stage) for stage in state[0])
    serial = count()
    heap, best, finals = [], {}, {}
    expansions = 0
    for cost, accumulators, path in frontier:
        state = ((0,) * rows, accumulators, (0,) * rows, 0, False)
        key = _key(*state)
        if cost < best.get(key, float('inf')):
            best[key] = cost
            heapq.heappush(heap, (cost, -progress(state), next(serial), state, path))
    while heap:
        if expansions % 32 == 0 and perf_counter() >= deadline:
            if finals:
                break
            raise BudgetExceeded('Reduction age column budget exhausted before a complete boundary')
        cost, _, _, state, path = heapq.heappop(heap)
        if cost != best[_key(*state)]:
            continue
        stages, accumulators, temporaries, weight, born = state
        if all(stage == (4 if last else 3) for stage in stages):
            key = tuple(sorted(accumulators))
            if key not in finals:
                finals[key] = (cost, accumulators, path)
            if len(finals) >= beam_width:
                break
            continue
        expansions += 1
        if expansions > max_states:
            if finals:
                break
            raise BudgetExceeded('Reduction age column state limit before a complete boundary')
        actions = [(-1, 'weight')] if not born else []
        for row, stage in enumerate(stages):
            if stage == 0 and not any(s == 1 for s in stages) and sum(s in (1, 2) for s in stages) < max_pending:
                actions.append((row, 'private'))
            elif stage == 1 and born:
                actions.append((row, 'product'))
            elif stage == 2:
                actions.append((row, 'addition'))
            elif stage == 3 and last:
                actions.append((row, 'store'))
        for action in actions:
            result = _step(*state, action, first=first, last=last, window=window)
            if result is None:
                continue
            new_state, new_cost = result[:5], cost + result[5]
            key = _key(*new_state)
            if new_cost >= best.get(key, float('inf')):
                continue
            best[key] = new_cost
            heapq.heappush(heap, (new_cost, -progress(new_state), next(serial), new_state, (path, action)))
    if not finals:
        raise InfeasibleSchedule('No restricted reduction column witness; not global infeasibility')
    return list(finals.values()), expansions, bool(heap)


def schedule_reduction_age(block, *, time_budget_ms=1000, beam_width=6, max_states=4000, max_pending=1):
    if time_budget_ms <= 0 or beam_width < 1 or max_states < 1 or max_pending not in (1, 2):
        raise ValueError('Positive reduction age limits required')
    started = perf_counter()
    deadline = started + time_budget_ms / 1000
    plan = recognize_reduction_columns(block, deadline=deadline)
    if plan is None or len(plan['rows']) > 4:
        raise InfeasibleSchedule('Age search needs complete <=4-row reduction; restricted failure only')
    rows = len(plan['rows'])
    if block.window >= 3 * rows + 1:
        output = schedule_reduction_columns(block, time_budget_ms=max(.001, (deadline - perf_counter()) * 1000), plan=plan)
        if output['stats']['inserted_copy_count'] == 0:
            output['stats'].update(strategy='reduction_age', age_zero_incumbent=True,
                                  age_states_expanded=0, age_truncated_columns=0,
                                  elapsed_ms=(perf_counter() - started) * 1000)
            return output
    frontier = [(0, (0,) * rows, None)]
    expansions = truncated = cache_hits = 0
    transitions = {}
    for column in range(plan['width']):
        if perf_counter() >= deadline:
            raise BudgetExceeded('Reduction age cached boundary budget exhausted')
        following = {}
        for base_cost, accumulators, history in frontier:
            # Resource-role permutation only; recipes restore each row's real
            # original IDs. First/last columns have different instruction sets.
            permutation = sorted(range(rows), key=lambda row: (accumulators[row], row))
            canonical = tuple(accumulators[row] for row in permutation)
            key = (canonical, column == 0, column == plan['width'] - 1)
            if key not in transitions:
                choices, expanded, cut = _column([(0, canonical, None)], column, plan, deadline=deadline,
                    beam_width=beam_width, max_states=max_states, max_pending=max_pending, window=block.window)
                expansions += expanded
                transitions[key] = choices, cut
            else:
                cache_hits += 1
            choices, cut = transitions[key]
            truncated += cut
            for extra_cost, final_ages, recipe in choices:
                next_ages = [0] * rows
                for canonical_row, actual_row in enumerate(permutation):
                    next_ages[actual_row] = final_ages[canonical_row]
                final_key = tuple(sorted(next_ages))
                cost = base_cost + extra_cost
                if final_key in following and following[final_key][0] <= cost:
                    continue
                actions = []
                while recipe is not None:
                    recipe, action = recipe
                    actions.append(action)
                indices = []
                for row, operation in reversed(actions):
                    if operation == 'weight':
                        index = plan['weights'][column]
                    else:
                        real_row = plan['rows'][permutation[row]]
                        index = real_row[{'private': 'private', 'product': 'products', 'addition': 'additions', 'store': 'terminal'}[operation]]
                        if operation != 'store':
                            index = index[column]
                    indices.append(index)
                following[final_key] = (cost, tuple(next_ages), (history, tuple(indices)))
        frontier = sorted(following.values(), key=lambda item: item[0])[:beam_width]
    cost, _, path = min(frontier, key=lambda item: item[0])
    reverse = []
    while path is not None:
        path, segment = path
        reverse.append(segment)
    order = [index for segment in reversed(reverse) for index in segment]
    output = emit_order(block, order, deadline=deadline)
    if output is None or output['stats']['inserted_copy_count'] != cost:
        raise AssertionError('Abstract role transition differs from full original-ID relay emission')
    output['stats'].update(strategy='reduction_age', age_rows=rows, age_columns=plan['width'],
        age_beam_width=beam_width, age_max_states_per_column=max_states,
        age_max_pending_products=max_pending,
        age_states_expanded=expansions, age_truncated_columns=truncated,
        age_cached_transitions=len(transitions), age_cache_hits=cache_hits,
        elapsed_ms=(perf_counter() - started) * 1000,
        scope='original-once complete row chains; column boundaries and greedy COPY; row-role symmetry is scheduling isomorphism, not value aliasing')
    return output
