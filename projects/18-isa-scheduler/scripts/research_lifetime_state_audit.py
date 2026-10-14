"""Raw all-state physical-age graph, then reverse exact remaining COPY cost.

Independent parsing/data/hazards/transitions; no scheduler graph or emitter.
The candidate floor is the only imported proposed algorithm under audit.
"""
import argparse
from collections import Counter, deque
import hashlib
import heapq
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.spine_lifetime import lifetime_floor


def generated(seed, mode):
    rng = random.Random(seed); rows = []
    def emit(op, args=(), reg=None):
        index = len(rows); item = {'id': index, 'op': op}
        if reg is not None: item['reg'] = reg
        if args: item['inputs'] = [f't#{index - source}' for source in args]
        rows.append(item); return index
    roots = [emit('GET', reg='a'), emit('GET', reg='b')]
    previous = roots[1]
    for offset in range(rng.randint(2, 5)):
        source = roots[offset % 2]
        args = (previous, source) if rng.randrange(2) else (source, previous)
        previous = emit('ADD' if offset % 2 else 'MULW', args)
    if mode == 'hazard':
        emit('SET', (previous,), 'a'); fresh = emit('GET', reg='a')
        previous = emit('ADD', (fresh, roots[0]))
    elif mode == 'fork':
        fresh = emit('ADD', (roots[0], roots[1])); emit('SET', (fresh,), 'fork')
    emit('SET', (previous,), 'out'); emit('GET', reg='unused')
    return {'block_id': f'lifetime-state-{seed}', 'bit_width': 2, 'instructions': rows}


def audit(data, *, budget_ms=500, max_states=100000):
    tick = perf_counter(); deadline = tick + budget_ms / 1000
    rows = data['instructions']; n = len(rows); window = 2 ** data['bit_width']
    users = [set() for _ in rows]; args = []; deps = []; ancestors = [0] * n
    writers = {}; readers = {}
    for index, row in enumerate(rows):
        sources = tuple(index - int(token[2:]) for token in row.get('inputs', []))
        if row['op'] not in ('GET', 'SET', 'ADD', 'MULW') or any(not 0 <= s < index for s in sources):
            raise ValueError('Unsupported raw input')
        if len(sources) != {'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}[row['op']] or any(rows[s]['op'] == 'SET' for s in sources):
            raise ValueError('Raw arity or SET-as-temporary invalid')
        args.append(sources); dependencies = set(sources)
        for source in set(sources):
            users[source].add(index); ancestors[index] |= ancestors[source] | 1 << source
        if row['op'] in ('GET', 'SET'):
            reg = row['reg']
            if reg in writers: dependencies.add(writers[reg])
            if row['op'] == 'GET': readers.setdefault(reg, set()).add(index)
            else:
                dependencies.update(readers.get(reg, set())); readers[reg] = set(); writers[reg] = index
        deps.append(sum(1 << s for s in dependencies))
    consumer_masks = [sum(1 << c for c in consumers) for consumers in users]
    cones = [0] * n; descendants = [0] * n
    for source in range(n - 1, -1, -1):
        for consumer in users[source]: descendants[source] |= descendants[consumer] | 1 << consumer
    roots = [index for index, row in enumerate(rows) if row['op'] == 'GET']
    root_slot = {root: slot for slot, root in enumerate(roots)}; cores = {}
    for source in range(n):
        before = 0
        for consumer in users[source]:
            cones[source] |= ancestors[consumer] | 1 << consumer; before |= ancestors[consumer]
        if source in root_slot: cores[source] = descendants[source] & before
    full = (1 << n) - 1; initial = (0, (0,) * n)
    states = [initial]; indices = {initial: 0}; reverse = [[]]; queue = deque([0]); final = None
    edges = 0
    while queue:
        if len(states) > max_states or perf_counter() >= deadline:
            return {'status': 'unknown_enumeration_budget', 'states': len(states), 'edges': edges,
                    'elapsed_ms': (perf_counter() - tick) * 1000}
        current = queue.popleft(); completed, ages = states[current]
        if completed == full: final = current; continue
        live = [source for source, age in enumerate(ages) if age]
        actions = [(index, False) for index in range(n) if not completed >> index & 1
                   and deps[index] & completed == deps[index] and all(ages[s] for s in args[index])]
        actions.extend((source, True) for source in live)
        for original, copy in actions:
            after = completed if copy else completed | 1 << original
            after_ages = [0] * n; legal = True
            for source in live:
                if consumer_masks[source] & ~after:
                    age = 1 if copy and source == original else ages[source] + 1
                    if age > window: legal = False; break
                    after_ages[source] = age
            if not legal: continue
            if not copy and consumer_masks[original] & ~after: after_ages[original] = 1
            state = (after, tuple(after_ages)); target = indices.get(state)
            if target is None:
                target = len(states); states.append(state); indices[state] = target; reverse.append([]); queue.append(target)
            reverse[target].append((current, int(copy))); edges += 1
    if final is None:
        return {'status': 'closed_identity_infeasible', 'states': len(states), 'edges': edges,
                'elapsed_ms': (perf_counter() - tick) * 1000}
    distances = {final: 0}; heap = [(0, final)]
    while heap:
        if perf_counter() >= deadline:
            return {'status': 'unknown_reverse_budget', 'states': len(states), 'edges': edges,
                    'elapsed_ms': (perf_counter() - tick) * 1000}
        cost, current = heapq.heappop(heap)
        if distances[current] != cost: continue
        for previous, weight in reverse[current]:
            candidate = cost + weight
            if candidate < distances.get(previous, float('inf')):
                distances[previous] = candidate; heapq.heappush(heap, (candidate, previous))
    violations = []; positive = 0; max_lower = 0
    for index, exact in distances.items():
        if perf_counter() >= deadline:
            return {'status': 'unknown_floor_check_budget', 'states': len(states), 'edges': edges,
                    'elapsed_ms': (perf_counter() - tick) * 1000}
        completed, physical = states[index]; live = tuple((source, age) for source, age in enumerate(physical) if age)
        born = sum(1 << slot for slot, root in enumerate(roots) if completed >> root & 1)
        remaining = tuple((consumer_masks[root] & ~completed).bit_count() for root in roots)
        lower = lifetime_floor(live, born, remaining, roots, root_slot, cones, cores, completed, window)
        positive += lower > 0; max_lower = max(max_lower, lower)
        if lower > exact: violations.append({'completed': completed, 'ages': physical, 'lower': lower, 'exact': exact})
    return {'status': 'complete_all_reachable_states', 'states': len(states), 'edges': edges,
            'finite_remaining_states': len(distances), 'dead_remaining_states': len(states) - len(distances),
            'positive_floor_states': positive, 'max_floor': max_lower, 'initial_optimum': distances[0],
            'violations': violations, 'elapsed_ms': (perf_counter() - tick) * 1000}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--count', type=int, default=120); parser.add_argument('--budget-ms', type=float, default=500)
    parser.add_argument('--max-states', type=int, default=20000)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = [{'family': ('spine', 'fork', 'hazard')[index % 3], 'seed': 8410001 + index,
              'input': generated(8410001 + index, ('spine', 'fork', 'hazard')[index % 3])}
             for index in range(options.count)]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    records = []; started = perf_counter()
    for case in cases:
        result = audit(case['input'], budget_ms=options.budget_ms, max_states=options.max_states)
        result.update(seed=case['seed'], family=case['family']); records.append(result)
    report = {'count': len(cases), 'elapsed_seconds': perf_counter() - started,
              'statuses': dict(Counter(row['status'] for row in records)),
              'finite_states_checked': sum(row.get('finite_remaining_states', 0) for row in records),
              'positive_floor_states': sum(row.get('positive_floor_states', 0) for row in records),
              'dead_remaining_states': sum(row.get('dead_remaining_states', 0) for row in records),
              'violations': [row for row in records if row.get('violations')], 'records': records,
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (Path(__file__), ROOT / 'isa_scheduler/spine_lifetime.py')},
              'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'parameters': vars(options), 'scope': 'Only fully drained forward graphs have exact reverse remaining costs; no output quality/Level verdict'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))
    return int(bool(report['violations']))


if __name__ == '__main__': raise SystemExit(main())
