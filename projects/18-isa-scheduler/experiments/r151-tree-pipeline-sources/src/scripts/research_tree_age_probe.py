"""Augment saved tree incumbents; fresh shapes use actual frozen R109 source."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from experiments.baseline_age_r109.optimizer import optimize as frozen_optimize
from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_age import schedule_tree_age
from isa_scheduler.workloads import generate_workload
from scripts.research_spine_age_probe import check


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def fresh(seed, family, count, bits):
    data = generate_workload(seed, family, count, bits); rng = random.Random(seed)
    original = data['instructions']; tuples = []
    for i, row in enumerate(original):
        args = tuple(i - int(t[2:]) for t in row.get('inputs', []))
        if row['op'] in ('ADD', 'MULW') and rng.randrange(2): args = args[::-1]
        tuples.append((row['op'], args, row.get('reg')))
    # Extra unused input is genuinely emitted, never trimmed.
    tuples.append(('GET', (), f'unused-{seed}'))
    done = set(); order = []
    while len(done) < len(tuples):
        ready = [i for i, (_, args, _) in enumerate(tuples) if i not in done and set(args) <= done]
        current = rng.choice(ready); done.add(current); order.append(current)
    positions = {node: offset for offset, node in enumerate(order)}; rows = []
    for offset, node in enumerate(order):
        op, args, reg = tuples[node]; row = {'id': f'tree-{seed}-{node}', 'op': op}
        if reg is not None: row['reg'] = f'unique-{seed}-{reg}'
        if args: row['inputs'] = [f't#{offset - positions[s]}' for s in args]
        rows.append(row)
    return {'family': family, 'seed': seed, 'input': {'block_id': f'tree-probe-{seed}', 'bit_width': bits, 'instructions': rows}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--holdout', action='store_true'); parser.add_argument('--budget-ms', type=float, default=500)
    parser.add_argument('--max-states', type=int, default=20000); parser.add_argument('--max-outcomes', type=int, default=16)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    source = ROOT / 'experiments/r107-age-portfolio-336'; old = {}; outputs = {}; orders = {}
    if options.holdout:
        cases = []
        for family in ('balanced_tree', 'ragged_tree', 'padded_tree'):
            for size in (47, 191, 769):
                for bits in (2, 3, 4, 5): cases.append(fresh(8450001 + len(cases), family, size, bits))
    else:
        report = json.loads((source / 'report.json').read_text()); variant = report['paired_variants']['after']
        old = {r['sha256']: r for r in report['records'] if r['variant'] == variant}
        outputs = {r['input_sha256']: r['output'] for r in map(json.loads, (source / 'optimized_outputs.jsonl').read_text().splitlines()) if r['variant'] == variant}
        orders = {r['input_sha256']: r['original_order'] for r in map(json.loads, (source / 'original_orders.jsonl').read_text().splitlines()) if r['variant'] == variant}
        cases = [c for c in map(json.loads, (source / 'inputs.jsonl').read_text().splitlines())
                 if c['family'] in ('balanced_tree', 'ragged_tree', 'padded_tree')]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(c, separators=(',', ':')) + '\n' for c in cases))
    records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = fingerprint(data); baseline = outputs.get(key); order = orders.get(key)
        old_status = old[key]['status'] if key in old else 'unknown'; baseline_seconds = None
        if options.holdout:
            tick = perf_counter()
            try:
                baseline = frozen_optimize(data, 'age_portfolio', time_budget_ms=250, max_states=30000)
                order = baseline['stats']['original_order']; old_status = 'verified'
            except Exception as error:
                old_status = 'budget_exhausted' if 'Budget' in type(error).__name__ else ('proven_infeasible_under_model' if 'proven_infeasible_under_model' in str(error) else 'scheduling_failure')
            baseline_seconds = perf_counter() - tick
        if baseline is not None:
            check(data, baseline, order)
            (folder / f'{key[:16]}-baseline-output.json').write_text(json.dumps({'input_sha256': key, 'output': baseline, 'original_order': order}) + '\n')
        before_copies = None if baseline is None else sum(r['op'] == 'COPY' for r in baseline['optimized_instructions'])
        best = baseline; best_order = order; best_copies = before_copies
        attempt = {'outcome': 'not_attempted_existing_zero_or_proof'}; tick = perf_counter()
        if before_copies != 0 and old_status != 'proven_infeasible_under_model':
            try:
                candidate = schedule_tree_age(parse_block(data), time_budget_ms=options.budget_ms,
                    max_states=options.max_states, max_outcomes=options.max_outcomes)
                candidate_order = candidate['stats']['original_order']; check(data, candidate, candidate_order)
                copies = candidate['stats']['inserted_copy_count']; attempt = {'outcome': 'verified_candidate', 'copies': copies, 'stats': candidate['stats']}
                if best_copies is None or copies < best_copies:
                    best = candidate; best_order = candidate_order; best_copies = copies
            except (BudgetExceeded, InfeasibleSchedule, ValueError) as error:
                attempt = {'outcome': 'unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure', 'message': str(error)}
        attempt['candidate_and_verify_seconds'] = perf_counter() - tick
        if best is not None:
            check(data, best, best_order)
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': best, 'original_order': best_order}) + '\n')
        row = {'sha256': key, 'family': case['family'], 'seed': case['seed'], 'node_count': len(data['instructions']),
               'bit_width': data['bit_width'], 'before_status': old_status, 'after_status': 'verified' if best is not None else old_status,
               'before_copies': before_copies, 'after_copies': best_copies, 'attempt': attempt, 'baseline_seconds': baseline_seconds}
        records.append(row); print(json.dumps({k: v for k, v in row.items() if k != 'attempt'}), flush=True)
    report = {'count': len(records), 'elapsed_seconds': perf_counter() - started, 'parameters': vars(options),
              'before_statuses': dict(Counter(r['before_status'] for r in records)), 'after_statuses': dict(Counter(r['after_status'] for r in records)),
              'before_copies': sum(r['before_copies'] or 0 for r in records), 'after_copies': sum(r['after_copies'] or 0 for r in records),
              'improved': sum(r['before_copies'] is not None and r['after_copies'] < r['before_copies'] for r in records),
              'recovered': sum(r['before_status'] != 'verified' and r['after_status'] == 'verified' for r in records),
              'records': records, 'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), ROOT / 'isa_scheduler/tree_age.py')},
              'baseline_source_manifest': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'experiments/baseline_age_r109').glob('*.py')},
              'scope': 'Old all48 tree inputs retain frozen336 incumbents, failure states unchanged; new36 is heldout, not replacement. Explicit candidate, default unchanged; all before/after outputs checked; costs are functional wall time, not isolated performance.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
