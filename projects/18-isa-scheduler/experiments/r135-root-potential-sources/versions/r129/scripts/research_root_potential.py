"""Independent raw-age oracle audit followed by input-only larger certificates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.root_potential_bound import propose_root_potential_bound, check_root_potential_bound
from scripts.research_retention_audit import raw_physical_oracle, generated
from isa_scheduler.evaluation import fingerprint


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--source'); parser.add_argument('--count', type=int, default=400)
    parser.add_argument('--budget-ms', type=float, default=100); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    if options.source:
        cases = list(map(json.loads, (ROOT / options.source / 'inputs.jsonl').read_text().splitlines()))
    else:
        cases = [{'family': ('free', 'hazard', 'spine', 'hazard_barrier', 'mandatory_spine')[index % 5],
                  'seed': 8380001 + index,
                  'input': generated(8380001 + index, ('free', 'hazard', 'spine', 'hazard_barrier', 'mandatory_spine')[index % 5], 2 + (index // 5) % 4)}
                 for index in range(options.count)]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    started = perf_counter(); records = []; violations = []
    for case in cases:
        data = case['input']; cert = propose_root_potential_bound(data, time_budget_ms=1000)
        lower = check_root_potential_bound(data, cert)['lower_bound'] if cert else 0
        result = {'status': 'necessary_bound_only'} if options.source else raw_physical_oracle(data, time_budget_ms=options.budget_ms)
        row = {'sha256': fingerprint(data), 'family': case['family'], 'seed': case.get('seed'),
               'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
               'lower': lower, 'certificate': cert, **result}
        if result['status'] == 'feasible_optimal_copy' and lower > result['copies']:
            violations.append(row)
        records.append(row)
        if len(records) % 100 == 0: print(json.dumps({'completed': len(records), 'violations': len(violations)}), flush=True)
    report = {'count': len(records), 'elapsed_seconds': perf_counter() - started,
              'statuses': dict(Counter(row['status'] for row in records)),
              'positive_certificates': sum(row['lower'] > 0 for row in records),
              'positive_optimal_completed': sum(row['lower'] > 0 and row['status'] == 'feasible_optimal_copy' for row in records),
              'subsets_scanned': sum((row['certificate'] or {}).get('subsets_scanned', 0) for row in records),
              'violations': violations, 'records': records,
              'parameters': vars(options),
              'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (Path(__file__), ROOT / 'isa_scheduler/root_potential_bound.py', ROOT / 'scripts/research_retention_audit.py')},
              'scope': 'Input-only selected-root necessary bounds; raw-age all-order/copy oracle completed cases only; unknowns retained; no quality gain'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))
    return int(bool(violations))


if __name__ == '__main__': raise SystemExit(main())
