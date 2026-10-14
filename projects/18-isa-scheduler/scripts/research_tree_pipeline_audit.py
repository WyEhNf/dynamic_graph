"""Replay frozen120 inputs/oracle results with the single pipeline change."""
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
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True); options = parser.parse_args()
    source = ROOT / 'experiments/r146-tree-age-audit'; folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    old = json.loads((source / 'report.json').read_text()); bank = {r['sha256']: r for r in old['records']}
    input_text = (source / 'inputs.jsonl').read_text(); (folder / 'inputs.jsonl').write_text(input_text)
    cases = list(map(json.loads, input_text.splitlines())); records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        previous = bank[key]; raw = previous['raw_oracle']
        record = {'sha256': key, 'seed': case['seed'], 'family': case['family'], 'node_count': len(data['instructions']),
                  'bit_width': data['bit_width'], 'old_copies': previous['copies'], 'saved_raw_oracle': raw}
        tick = perf_counter()
        try:
            candidate = schedule_tree_pipeline(parse_block(data), time_budget_ms=500, max_states=20000, max_outcomes=1024)
            order = candidate['stats']['original_order']; check(data, candidate, order)
            cost = candidate['stats']['inserted_copy_count']
            if raw['status'] == 'optimal_under_identity_model' and cost < raw['copies']: raise AssertionError('Raw global optimum contradicted')
            if raw['status'] == 'closed_identity_infeasible': raise AssertionError('Raw negative contradicted')
            if not candidate['stats']['tree_age']['truncated_outcomes'] and cost > previous['copies']: raise AssertionError('Untruncated superset worsened DFS family')
            record.update(status='verified', copies=cost, stats=candidate['stats'])
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': candidate, 'original_order': order}) + '\n')
        except (BudgetExceeded, InfeasibleSchedule) as error:
            record.update(status='unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure', message=str(error))
        record['candidate_and_verify_seconds'] = perf_counter() - tick; records.append(record)
    report = {'count': len(records), 'elapsed_seconds': perf_counter() - started,
              'statuses': dict(Counter(r['status'] for r in records)),
              'saved_raw_oracle_statuses': dict(Counter(r['saved_raw_oracle']['status'] for r in records)),
              'improved': sum(r['status'] == 'verified' and r['copies'] < r['old_copies'] for r in records),
              'old_copies': sum(r['old_copies'] for r in records),
              'new_copies_verified': sum(r['copies'] for r in records if r['status'] == 'verified'),
              'above_saved_global_optimum': sum(r['status'] == 'verified' and r['saved_raw_oracle']['status'] == 'optimal_under_identity_model'
                                                   and r['copies'] > r['saved_raw_oracle']['copies'] for r in records),
              'records': records, 'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  (Path(__file__), ROOT / 'isa_scheduler/tree_pipeline.py', source / 'report.json', source / 'inputs.jsonl')},
              'scope': 'Same120 original inputs and68 exact/52unknown saved raw results, not a new oracle proof. Pipeline is local superset of DFS, no global optimality/Level claim.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
