"""One pipeline candidate, fixed saved48/36 incumbents, unchanged budgets."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_pipeline import schedule_tree_pipeline
from scripts.research_spine_age_probe import check


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--source', default='experiments/r148-tree-age-old48'); options = parser.parse_args()
    source = ROOT / options.source; folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    old = json.loads((source / 'report.json').read_text()); bank = {r['sha256']: r for r in old['records']}
    text = (source / 'inputs.jsonl').read_text(); (folder / 'inputs.jsonl').write_text(text)
    cases = list(map(json.loads, text.splitlines())); records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        previous = bank[key]; saved_path = source / f'{key[:16]}-output.json'
        saved = json.loads(saved_path.read_text()) if saved_path.exists() else None
        best = None if saved is None else saved['output']; order = None if saved is None else saved['original_order']; cost = previous['after_copies']
        if best is not None:
            check(data, best, order)
            (folder / f'{key[:16]}-baseline-output.json').write_text(json.dumps(saved) + '\n')
        attempt = {'outcome': 'not_attempted_existing_zero_or_proof'}; tick = perf_counter()
        if cost != 0 and previous['after_status'] != 'proven_infeasible_under_model':
            phase = 'schedule'
            try:
                candidate = schedule_tree_pipeline(parse_block(data), time_budget_ms=500, max_states=20000, max_outcomes=16)
                phase = 'independent_verify'
                candidate_order = candidate['stats']['original_order']; check(data, candidate, candidate_order)
                candidate_cost = candidate['stats']['inserted_copy_count']; attempt = {'outcome': 'verified_candidate', 'copies': candidate_cost, 'stats': candidate['stats']}
                # Preserve every completed candidate, including a worse one.
                (folder / f'{key[:16]}-candidate-output.json').write_text(json.dumps({'input_sha256': key, 'output': candidate, 'original_order': candidate_order}) + '\n')
                if cost is None or candidate_cost < cost: best = candidate; order = candidate_order; cost = candidate_cost
            except (BudgetExceeded, InfeasibleSchedule, ValueError) as error:
                if phase == 'independent_verify': raise
                attempt = {'outcome': 'unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure', 'message': str(error)}
        attempt['candidate_and_verify_seconds'] = perf_counter() - tick
        if best is not None:
            check(data, best, order)
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': best, 'original_order': order}) + '\n')
        records.append({'sha256': key, 'family': case['family'], 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
            'before_status': previous['after_status'], 'after_status': 'verified' if best is not None else previous['after_status'],
            'before_copies': previous['after_copies'], 'after_copies': cost, 'attempt': attempt})
    report = {'count': len(records), 'elapsed_seconds': perf_counter() - started,
              'before_statuses': dict(Counter(r['before_status'] for r in records)), 'after_statuses': dict(Counter(r['after_status'] for r in records)),
              'before_copies': sum(r['before_copies'] or 0 for r in records), 'after_copies': sum(r['after_copies'] or 0 for r in records),
              'improved': sum(r['before_copies'] is not None and r['after_copies'] < r['before_copies'] for r in records),
              'recovered': sum(r['before_status'] != 'verified' and r['after_status'] == 'verified' for r in records), 'records': records,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  (Path(__file__), ROOT / 'isa_scheduler/tree_pipeline.py', source / 'report.json', source / 'inputs.jsonl')},
              'parameters': {'time_budget_ms': 500, 'max_states': 20000, 'max_outcomes': 16},
              'scope': 'Same frozen48/36 inputs+actual saved incumbents, no baseline rescheduling. Whole336/72/default remains unchanged; local pipeline only; negative, unknown and worse attempts retained.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
