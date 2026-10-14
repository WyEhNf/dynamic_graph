"""Fresh physical-age and DFS-family differential audit; preserve unknowns."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_age import schedule_tree_age
from scripts.tree_raw_oracles import raw_optimum, dfs_deadline_optimum
from scripts.research_spine_age_probe import check


def generated(seed, bit_width, shape):
    rng = random.Random(seed); rows = []
    def emit(op, args=(), reg=None):
        rows.append((op, args, reg)); return len(rows) - 1
    unused = emit('GET', reg=f'unused-{seed}')
    for component in range(2 if shape == 'forest' else 1):
        values = []
        for leaf in range(rng.randint(2, 5)):
            value = emit('GET', reg=f'in-{component}-{leaf}')
            for _ in range(rng.randint(0, 6) if shape == 'padded' else rng.randint(0, 1)):
                value = emit(rng.choice(('ADD', 'MULW')), (value, value))
            values.append(value)
        while len(values) > 1:
            first = rng.randrange(len(values)) if shape in ('ragged', 'padded') else 0
            a = values.pop(first); second = rng.randrange(len(values)) if shape in ('ragged', 'padded') else 0
            b = values.pop(second); args = (a, b) if rng.randrange(2) else (b, a)
            values.append(emit(rng.choice(('ADD', 'MULW')), args))
        emit('SET', (values[0],), f'out-{component}')
    emit('GET', reg=f'unused-last-{seed}')
    # Actual original topology changes, beyond renaming emitted output IDs.
    done = set(); permutation = []
    while len(done) < len(rows):
        ready = [i for i, (_, args, _) in enumerate(rows) if i not in done and set(args) <= done]
        current = rng.choice(ready); done.add(current); permutation.append(current)
    positions = {node: offset for offset, node in enumerate(permutation)}; instructions = []
    for offset, node in enumerate(permutation):
        op, args, reg = rows[node]; row = {'id': f'opaque-{seed}-{node}', 'op': op}
        if reg is not None: row['reg'] = reg
        if args: row['inputs'] = [f't#{offset - positions[s]}' for s in args]
        instructions.append(row)
    return {'block_id': f'tree-audit-{seed}', 'bit_width': bit_width, 'instructions': instructions}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--count', type=int, default=120); parser.add_argument('--budget-ms', type=float, default=500)
    parser.add_argument('--max-states', type=int, default=20000)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = [{'seed': 8440001 + i, 'family': ('balanced', 'ragged', 'padded', 'forest')[(i // 4) % 4],
              'input': generated(8440001 + i, 2 + i % 4, ('balanced', 'ragged', 'padded', 'forest')[(i // 4) % 4])}
             for i in range(options.count)]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(c, separators=(',', ':')) + '\n' for c in cases))
    records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        exact = raw_optimum(data, budget_ms=options.budget_ms, max_states=options.max_states)
        dfs = dfs_deadline_optimum(data); tick = perf_counter()
        record = {'sha256': key, 'seed': case['seed'], 'family': case['family'], 'bit_width': data['bit_width'],
                  'node_count': len(data['instructions']), 'raw_oracle': exact, 'DFS_oracle': dfs}
        try:
            candidate = schedule_tree_age(parse_block(data), time_budget_ms=options.budget_ms,
                                          max_states=options.max_states, max_outcomes=1024)
            order = candidate['stats']['original_order']; check(data, candidate, order)
            copies = candidate['stats']['inserted_copy_count']; record.update(status='verified', copies=copies, stats=candidate['stats'])
            if exact['status'] == 'closed_identity_infeasible': raise AssertionError('Raw closed negative contradicts witness')
            if exact['status'] == 'optimal_under_identity_model' and copies < exact['copies']: raise AssertionError('Candidate beats independent global optimum')
            if not candidate['stats']['tree_age']['truncated_outcomes']:
                if dfs['status'] == 'complete_DFS_deadline_family' and copies != dfs['copies']: raise AssertionError('Memo differs from exhaustive DFS family')
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': candidate, 'original_order': order}) + '\n')
        except (BudgetExceeded, InfeasibleSchedule) as error:
            record.update(status='unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure', message=str(error))
        record['candidate_and_verify_seconds'] = perf_counter() - tick; records.append(record)
    result = {'count': len(cases), 'elapsed_seconds': perf_counter() - started,
              'candidate_statuses': dict(Counter(r['status'] for r in records)),
              'raw_oracle_statuses': dict(Counter(r['raw_oracle']['status'] for r in records)),
              'DFS_oracle_statuses': dict(Counter(r['DFS_oracle']['status'] for r in records)),
              'optimal_comparisons': sum(r['status'] == 'verified' and r['raw_oracle']['status'] == 'optimal_under_identity_model' for r in records),
              'candidate_above_global_optimum': sum(r['status'] == 'verified' and r['raw_oracle']['status'] == 'optimal_under_identity_model' and r['copies'] > r['raw_oracle']['copies'] for r in records),
              'parameters': vars(options), 'records': records,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  (Path(__file__), ROOT / 'scripts/tree_raw_oracles.py', ROOT / 'isa_scheduler/tree_age.py')},
              'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'scope': 'Fresh120 synthetic inputs, raw arbitrary-ready/early-COPY oracle has time/state unknowns; DFS oracle covers only orientations/deadline relay. No whole336 or official Level claim.'}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))


if __name__ == '__main__': main()
