"""Same saved R125 incumbents and independent fresh structural holdout."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block, InfeasibleSchedule, BudgetExceeded
from isa_scheduler.spine_age import schedule_spine_age
from isa_scheduler.spine_lifetime import schedule_spine_lifetime
from isa_scheduler.evaluation import fingerprint
from scripts.research_spine_age_probe import check


def holdout_case(seed, bits, shape):
    rng = random.Random(seed); rows = [('GET', (), f'unused-{seed}')]
    roots = []
    for role in range(3):
        roots.append(len(rows)); rows.append(('GET', (), f'root-{role}'))
    for branch in range(4):
        private = len(rows); rows.append(('GET', (), f'private-{branch}'))
        previous = private
        sequence = []
        roles = ([0, 1, 0, 2], [1, 0, 2, 1], [2, 1, 0], [0, 2, 1, 2])[branch]
        if shape == 1: roles = list(reversed(roles))
        elif shape == 2: roles = [(role + branch) % 3 for role in roles]
        elif shape == 3: roles = roles + [branch % 3]
        for role in roles:
            sequence += [roots[role]] * rng.randrange(2, 13)
        for offset, root in enumerate(sequence):
            args = (root, previous) if rng.randrange(2) else (previous, root)
            rows.append(('MULW' if offset % 5 == 0 else 'ADD', args, None))
            previous = len(rows) - 1
        rows.append(('SET', (previous,), f'output-{branch}'))
    rows.append(('GET', (), f'unused-last-{seed}'))
    # Random actual topological original order; preserve original ordered args.
    done = set(); order = []
    while len(order) != len(rows):
        ready = [i for i, (_, args, _) in enumerate(rows) if i not in done and set(args) <= done]
        current = rng.choice(ready); done.add(current); order.append(current)
    positions = {node: offset for offset, node in enumerate(order)}; instructions = []
    for offset, original in enumerate(order):
        op, args, reg = rows[original]; row = {'id': f'macro-{seed}-{original}', 'op': op}
        if reg is not None: row['reg'] = f'opaque-{seed}-{reg}'
        if args: row['inputs'] = [f't#{offset - positions[source]}' for source in args]
        instructions.append(row)
    return {'family': f'root_run_crossing_shape{shape}', 'seed': seed,
            'input': {'block_id': f'macro-holdout-{seed}', 'bit_width': bits, 'instructions': instructions}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--source', default='experiments/r125-spine-age-cross')
    parser.add_argument('--holdout', action='store_true'); parser.add_argument('--budget-ms', type=float, default=1000)
    parser.add_argument('--beams', default='1,4'); parser.add_argument('--span', type=int, default=1)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    source = ROOT / options.source; source_report = None; incumbents = {}; old = {}
    if options.holdout:
        cases = [holdout_case(8370001 + shape * 10 + bits, bits, shape)
                 for shape in range(4) for bits in (2, 3, 4, 5)]
    else:
        source_report = json.loads((source / 'report.json').read_text())
        cases = list(map(json.loads, (source / 'inputs.jsonl').read_text().splitlines()))
        old = {row['sha256']: row for row in source_report['records']}
        for path in source.glob('*-output.json'):
            item = json.loads(path.read_text()); incumbents[item['input_sha256']] = item
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = fingerprint(data); block = parse_block(data); attempts = []
        saved = incumbents.get(key); best = None if saved is None else saved['output']
        order = None if saved is None else saved['original_order']
        copies = None if best is None else sum(row['op'] == 'COPY' for row in best['optimized_instructions'])
        before_status = old[key]['after_status'] if key in old else 'unknown_restricted_candidates'
        if best is not None: check(data, best, order)
        variants = ('individual', 'macro') if options.holdout else ('macro',)
        before_copies = copies
        for variant in variants:
            for beam in map(int, options.beams.split(',')):
                if copies == 0: break
                tick = perf_counter()
                try:
                    function = schedule_spine_lifetime if variant == 'macro' else schedule_spine_age
                    kwargs = {'max_span': options.span} if variant == 'macro' else {}
                    candidate = function(block, time_budget_ms=options.budget_ms, beam_width=beam, **kwargs)
                    check(data, candidate, candidate['stats']['original_order'])
                    if before_status == 'proven_infeasible_under_model':
                        raise AssertionError('Witness contradicts saved proof; audit required')
                    count = candidate['stats']['inserted_copy_count']
                    item = {'variant': variant, 'beam': beam, 'outcome': 'verified_candidate',
                            'copies': count, 'stats': candidate['stats']}
                    if copies is None or count < copies:
                        best = {'block_id': data['block_id'], 'optimized_instructions': candidate['optimized_instructions']}
                        order = candidate['stats']['original_order']; copies = count
                except (InfeasibleSchedule, BudgetExceeded) as error:
                    item = {'variant': variant, 'beam': beam, 'outcome': 'unknown_budget' if isinstance(error, BudgetExceeded)
                            else 'restricted_candidate_failure', 'message': str(error)}
                item['full_seconds'] = perf_counter() - tick; attempts.append(item)
            if variant == 'individual':
                before_copies = copies; before_status = 'verified' if best is not None else 'unknown_restricted_candidates'
                if best is not None:
                    (folder / f'{key[:16]}-baseline-output.json').write_text(json.dumps({'input_sha256': key, 'output': best, 'original_order': order}) + '\n')
        row = {'sha256': key, 'family': case['family'], 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
               'before_status': before_status, 'after_status': 'verified' if best is not None else before_status,
               'before_copies': before_copies, 'after_copies': copies, 'attempts': attempts}
        records.append(row)
        if best is not None:
            check(data, best, order)
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': best, 'original_order': order}) + '\n')
        print(json.dumps({k: v for k, v in row.items() if k != 'attempts'}), flush=True)
        (folder / 'partial-records.json').write_text(json.dumps(records, indent=2) + '\n')
    common = [row for row in records if row['before_copies'] is not None and row['after_copies'] is not None]
    report = {'count': len(cases), 'elapsed_seconds': perf_counter() - started,
              'before_statuses': dict(Counter(row['before_status'] for row in records)),
              'after_statuses': dict(Counter(row['after_status'] for row in records)),
              'common_count': len(common), 'common_before_copies': sum(row['before_copies'] for row in common),
              'common_after_copies': sum(row['after_copies'] for row in common),
              'improved': sum(row['after_copies'] < row['before_copies'] for row in common),
              'recovered': sum(row['before_copies'] is None and row['after_copies'] is not None for row in records),
              'records': records, 'parameters': vars(options),
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (Path(__file__), ROOT / 'isa_scheduler/spine_lifetime.py', ROOT / 'isa_scheduler/root_potential_bound.py', ROOT / 'isa_scheduler/spine_age.py')},
              'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'baseline_report_sha256': None if source_report is None else hashlib.sha256((source / 'report.json').read_bytes()).hexdigest(),
              'scope': 'Restricted segment candidate, actual originals/physical ages; retained saved incumbent, no optimum/negative certificate; not whole336 Level score'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
