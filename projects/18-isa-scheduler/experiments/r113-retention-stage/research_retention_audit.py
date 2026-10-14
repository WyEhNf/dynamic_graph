"""Raw physical-age feasibility oracle vs bounded retention-order DFS.

The raw oracle uses only Python stdlib, independently reconstructs references
and register hazards, and explores every legal original and every live COPY.
No scheduler DAG, liveness, emitter or retention state feeds the raw oracle.
Only drained states prove infeasibility; time/state limits remain unknown.
"""
import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import heapq
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]


def raw_physical_oracle(data, *, fixed=False, max_states=100000, time_budget_ms=200):
    rows = data['instructions']; n = len(rows); window = 2 ** data['bit_width']
    full = (1 << n) - 1; args = []; deps = []; consumers = [0] * n
    last_write = {}; readers = {}
    for index, row in enumerate(rows):
        sources = tuple(index - int(token[2:]) for token in row.get('inputs', []))
        if row['op'] not in ('GET', 'SET', 'ADD', 'MULW') or any(not 0 <= source < index for source in sources):
            raise ValueError('Unsupported original/raw reference')
        args.append(sources); dependencies = set(sources)
        for source in set(sources): consumers[source] |= 1 << index
        if row['op'] in ('GET', 'SET'):
            reg = row['reg']
            if reg in last_write: dependencies.add(last_write[reg])
            if row['op'] == 'GET': readers.setdefault(reg, set()).add(index)
            else:
                dependencies.update(readers.get(reg, set())); readers[reg] = set(); last_write[reg] = index
        if fixed and index: dependencies.add(index - 1)
        deps.append(sum(1 << source for source in dependencies))
    initial = (0, (0,) * n); costs = {initial: 0}; queue = [(0, *initial)]
    started = perf_counter(); deadline = started + time_budget_ms / 1000; expanded = 0
    while queue:
        copies, done, ages = heapq.heappop(queue)
        if costs.get((done, ages)) != copies: continue
        if done == full:
            return {'status': 'feasible_optimal_copy', 'copies': copies, 'states': len(costs),
                    'expanded': expanded, 'elapsed_ms': (perf_counter() - started) * 1000}
        expanded += 1
        if expanded % 64 == 1 and (perf_counter() >= deadline or len(costs) > max_states):
            return {'status': 'unknown_budget', 'states': len(costs), 'expanded': expanded,
                    'elapsed_ms': (perf_counter() - started) * 1000}
        live = [source for source, age in enumerate(ages) if age]
        actions = [(index, False) for index in range(n)
                   if not done >> index & 1 and deps[index] & done == deps[index]
                   and all(ages[source] for source in args[index])]
        actions.extend((source, True) for source in live)
        for index, copy in actions:
            after_done = done if copy else done | 1 << index
            after_ages = [0] * n; legal = True
            for source in live:
                if consumers[source] & ~after_done:
                    age = 1 if copy and source == index else ages[source] + 1
                    if age > window: legal = False; break
                    after_ages[source] = age
            if not legal: continue
            if not copy and consumers[index] & ~after_done: after_ages[index] = 1
            state = (after_done, tuple(after_ages)); cost = copies + copy
            if cost < costs.get(state, float('inf')):
                costs[state] = cost; heapq.heappush(queue, (cost, *state))
    return {'status': 'proven_infeasible_identity_model', 'states': len(costs),
            'expanded': expanded, 'elapsed_ms': (perf_counter() - started) * 1000}


def generated(seed, mode, bits):
    rng = random.Random(seed); rows = []; values = []
    def emit(op, sources=(), reg=None):
        index = len(rows); row = {'id': index, 'op': op}
        if reg is not None: row['reg'] = reg
        if sources: row['inputs'] = [f't#{index - source}' for source in sources]
        rows.append(row)
        if op != 'SET': values.append(index)
        return index
    roots = [emit('GET', reg=f'r{index}') for index in range(rng.randint(1, 5))]
    for step in range(rng.randint(2, 5)):
        if mode == 'hazard' and step % 2:
            emit('SET', (rng.choice(values),), rng.choice([f'r{i}' for i in range(len(roots))]))
            emit('GET', reg=rng.choice([f'r{i}' for i in range(len(roots))]))
        else:
            sources = ((values[-1], rng.choice(roots)) if mode == 'spine' else
                       (rng.choice(values),) * 2 if mode == 'duplicates' else
                       (rng.choice(values), rng.choice(values)))
            emit(rng.choice(('ADD', 'MULW')), sources)
    if mode == 'dead': emit('GET', reg='unused')
    emit('SET', (values[-1],), 'out')
    return {'block_id': f'retention-audit-{mode}-{seed}', 'bit_width': bits, 'instructions': rows}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--count', type=int, default=1000); parser.add_argument('--seed', type=int, default=8280001)
    parser.add_argument('--oracle-ms', type=float, default=200); options = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    from isa_scheduler.model import parse_block, InfeasibleSchedule, BudgetExceeded
    from isa_scheduler.retention_search import schedule_retention
    from isa_scheduler.retention_certificate import check_retention_certificate
    from isa_scheduler.identity_witness import check_identity_witness
    from isa_scheduler.verify import verify, interpret, IntegerSemantics
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    records = []; corpus = []; violations = []; started = perf_counter()
    for index in range(options.count):
        seed = options.seed + index; mode = ('random', 'spine', 'hazard', 'duplicates', 'dead')[index % 5]
        bits = 2 if index % 2 == 0 else 2 + (index // 2) % 4
        data = generated(seed, mode, bits); sha = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        corpus.append({'family': mode, 'seed': seed, 'input': data})
        for fixed in (False, True):
            physical = raw_physical_oracle(data, fixed=fixed, time_budget_ms=options.oracle_ms)
            block = parse_block(data)
            if fixed:
                block = replace(block, instructions=tuple(replace(node, order_deps=tuple(sorted(set(node.order_deps) | ({node.index - 1} if node.index else set())))) for node in block.instructions))
            tick = perf_counter(); candidate = None
            try:
                candidate = schedule_retention(block, time_budget_ms=1000, max_states=100000)
                verify(data, candidate); check_identity_witness(data, candidate, candidate['stats']['original_order'])
                inputs = {row['reg']: 31 - 13 * offset for offset, row in enumerate(data['instructions']) if row['op'] == 'GET'}
                for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                    assert interpret(data['instructions'], inputs, semantics) == interpret(candidate['optimized_instructions'], inputs, semantics)
                outcome = 'verified_feasible'
            except BudgetExceeded: outcome = 'unknown_budget'
            except InfeasibleSchedule as exc:
                if 'proven_infeasible_under_model' not in str(exc): raise
                if not fixed: check_retention_certificate(data, exc.retention_certificate)
                outcome = 'proven_infeasible_identity_model'
            item = {'sha256': sha, 'seed': seed, 'family': mode, 'bit_width': bits, 'fixed': fixed,
                    'physical': physical, 'retention': outcome, 'retention_ms': (perf_counter() - tick) * 1000}
            if candidate is not None: item['retention_copies'] = candidate['stats']['inserted_copy_count']
            records.append(item)
            contradiction = ((physical['status'] == 'feasible_optimal_copy' and outcome == 'proven_infeasible_identity_model') or
                             (physical['status'] == 'proven_infeasible_identity_model' and outcome == 'verified_feasible'))
            if contradiction:
                violations.append(item); (folder / f'counterexample-{seed}-{int(fixed)}.json').write_text(json.dumps(data, indent=2) + '\n')
        if (index + 1) % 100 == 0: print(json.dumps({'completed_inputs': index + 1, 'elapsed_seconds': perf_counter() - started}), flush=True)
    payload = ''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in corpus)
    (folder / 'inputs.jsonl').write_text(payload, encoding='utf-8')
    report = {'count': options.count, 'comparison_count': len(records), 'seed': options.seed, 'oracle_ms': options.oracle_ms,
        'oracle_scope': 'raw JSON independently rebuilt ordered data args+register RAW/WAR/WAW; all ready originals+all live COPY actions; latest unique original identities, no aliases/recompute/reread/spill',
        'retention_statuses': dict(Counter(row['retention'] for row in records)),
        'physical_statuses': dict(Counter(row['physical']['status'] for row in records)),
        'joint_completed': sum(row['retention'] != 'unknown_budget' and row['physical']['status'] != 'unknown_budget' for row in records),
        'violations': violations, 'elapsed_seconds': perf_counter() - started, 'records': records,
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'retention_source_sha256': hashlib.sha256((ROOT / 'isa_scheduler/retention_search.py').read_bytes()).hexdigest()}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'})); return int(bool(violations))


if __name__ == '__main__': raise SystemExit(main())
