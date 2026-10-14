"""Optional exact original-order feasibility model (OR-Tools CP-SAT).

Each live result uses [birth,last-data-consumer) at integer original positions.
An original with no future data use occupies [position,position+1): although
its result is dead, its physical row must fit. Cumulative W encodes the
retention-order bridge including the full-window last-use condition.
No COPY minimization objective. Not imported by the default optimizer.
"""
from time import perf_counter

from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded, InfeasibleSchedule


def solve_retention_cpsat(block, *, time_budget_ms=1000, max_nodes=1024, seed=8320001,
                          workers=1, export_model=None, fixed_order=False):
    if time_budget_ms <= 0 or max_nodes < 1 or workers < 1:
        raise ValueError('Positive CP-SAT limits required')
    nodes = block.instructions; count = len(nodes)
    if count > max_nodes: raise BudgetExceeded(f'CP-SAT model limited to {max_nodes} originals')
    if any(node.op not in ('GET', 'SET', 'ADD', 'MULW') for node in nodes):
        raise InfeasibleSchedule('CP-SAT retention rejects original COPY/unknown operations; matcher failure only')
    try:
        import ortools
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise RuntimeError('Optional OR-Tools environment required; see requirements-cpsat.lock') from exc
    tick = perf_counter(); deadline = tick + time_budget_ms / 1000
    graph = PreparedGraph(block, time_budget_ms=time_budget_ms)
    model = cp_model.CpModel(); ancestor = [0] * count; descendant = [0] * count
    for node in nodes:
        for source in graph.deps[node.index]: ancestor[node.index] |= ancestor[source] | 1 << source
    for index in range(count - 1, -1, -1):
        for user in graph.users[index]: descendant[index] |= descendant[user] | 1 << user
    positions = [model.new_int_var(ancestor[index].bit_count(), count - 1 - descendant[index].bit_count(), f'position_{index}')
                 for index in range(count)]
    model.add_all_different(positions); intervals = []
    for index, node in enumerate(nodes):
        if index % 64 == 0 and perf_counter() >= deadline:
            raise BudgetExceeded('CP-SAT model construction budget exhausted')
        for source in graph.deps[index]: model.add(positions[source] < positions[index])
        if fixed_order: model.add(positions[index] == index)
        consumers = graph.data_users[index]
        if consumers:
            last = model.new_int_var(0, count - 1, f'last_use_{index}')
            model.add_max_equality(last, [positions[user] for user in consumers])
            duration = model.new_int_var(1, count - 1, f'duration_{index}')
            model.add(duration == last - positions[index])
            intervals.append(model.new_interval_var(positions[index], duration, last, f'identity_{index}'))
        else:
            intervals.append(model.new_fixed_size_interval_var(positions[index], 1, f'dead_physical_row_{index}'))
    model.add_cumulative(intervals, [1] * len(intervals), block.window)
    validation = model.validate()
    if validation: raise ValueError(f'Invalid CP-SAT retention model: {validation}')
    if export_model is not None and not model.export_to_file(str(export_model)):
        raise ValueError('Could not export CP-SAT model')
    build_ms = (perf_counter() - tick) * 1000
    remaining = deadline - perf_counter()
    if remaining <= 0: raise BudgetExceeded('CP-SAT model construction exhausted search budget')
    solver = cp_model.CpSolver(); solver.parameters.max_time_in_seconds = remaining
    solver.parameters.num_search_workers = workers; solver.parameters.random_seed = seed
    status = solver.solve(model); info = {'backend': 'OR-Tools CP-SAT', 'backend_version': ortools.__version__,
        'solver_status': solver.status_name(status), 'build_ms': build_ms, 'solver_wall_seconds': solver.wall_time,
        'deterministic_time': solver.response_proto.deterministic_time, 'branches': solver.num_branches,
        'conflicts': solver.num_conflicts, 'workers': workers, 'seed': seed, 'time_budget_ms': time_budget_ms,
        'fixed_order': fixed_order, 'node_count': count, 'window': block.window,
        'scope': 'Exact stated original-order feasibility model; full-window dead physical rows included; '
                 'no COPY objective, alias, extra GET, recompute or spill; solver INFEASIBLE is backend proof, not independent portable certificate'}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        order = sorted(range(count), key=lambda index: solver.value(positions[index]))
        info['outcome'] = 'constructive_original_order'; return order, info
    if status == cp_model.INFEASIBLE:
        info['outcome'] = 'solver_proved_infeasible_stated_model'; return None, info
    if status == cp_model.MODEL_INVALID: raise ValueError('CP-SAT MODEL_INVALID')
    info['outcome'] = 'unknown_budget'; return None, info


def schedule_retention_cpsat(block, *, time_budget_ms=1000, max_nodes=1024, seed=8320001,
                             workers=1, export_model=None, fixed_order=False):
    order, info = solve_retention_cpsat(block, time_budget_ms=time_budget_ms, max_nodes=max_nodes,
        seed=seed, workers=workers, export_model=export_model, fixed_order=fixed_order)
    if order is None:
        error = InfeasibleSchedule('solver_proved_infeasible_stated_model: CP-SAT backend, no portable certificate') if info['outcome'].startswith('solver_proved') else BudgetExceeded('CP-SAT retention search budget unknown')
        error.cpsat_diagnostics = info; raise error
    # The solver limit is a search budget. Emission is a separately bounded
    # postprocess and must finish before a result can be called constructive.
    candidate = emit_order(block, order, deadline=perf_counter() + max(1, time_budget_ms / 1000))
    if candidate is None: raise AssertionError('CP-SAT retention bridge failed to materialize')
    candidate['stats'].update(strategy='retention_cpsat', retention_cpsat=info)
    return candidate
