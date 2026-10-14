"""Audit optional CP-SAT feasibility against already saved raw-age outcomes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.retention_cpsat import solve_retention_cpsat
from isa_scheduler.local_order import emit_order
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify, interpret, IntegerSemantics
from isa_scheduler.evaluation import fingerprint


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--oracle-report', required=True); parser.add_argument('--input', required=True)
    parser.add_argument('--budget-ms', type=float, default=1000); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False); (folder / 'models').mkdir()
    cases = [json.loads(line) for line in Path(options.input).read_text().splitlines() if line.strip()]
    reference = json.loads(Path(options.oracle_report).read_text())
    oracle = {(row['sha256'], row['fixed']): row for row in reference['records']}
    payload = ''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases)
    (folder / 'inputs.jsonl').write_text(payload, encoding='utf-8'); records = []; violations = []; started = perf_counter()
    outputs = (folder / 'optimized_outputs.jsonl').open('w', encoding='utf-8')
    for offset, case in enumerate(cases):
        data = case['input']; key = fingerprint(data); block = parse_block(data)
        for fixed in (False, True):
            model_path = folder / 'models' / f'{key[:16]}-{int(fixed)}.pbtxt'
            order, info = solve_retention_cpsat(block, time_budget_ms=options.budget_ms, fixed_order=fixed,
                                              workers=1, seed=8320001, export_model=model_path)
            known = oracle[key, fixed]; item = {'sha256': key, 'family': case['family'], 'fixed': fixed,
                'physical_reference': known['physical']['status'], 'retention_reference': known['retention'],
                'cpsat': info, 'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest()}
            if order is not None:
                candidate = emit_order(block, order, deadline=perf_counter() + 5)
                if candidate is None: raise AssertionError('CP-SAT bridge materialization failed')
                verify(data, candidate); check_identity_witness(data, candidate, order)
                initial = {row['reg']: 23 - 19 * i for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
                for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                    assert interpret(data['instructions'], initial, semantics) == interpret(candidate['optimized_instructions'], initial, semantics)
                item['copies'] = candidate['stats']['inserted_copy_count']
                core = {'block_id': data['block_id'], 'optimized_instructions': candidate['optimized_instructions']}
                outputs.write(json.dumps({'input_sha256': key, 'fixed': fixed, 'output': core, 'original_order': order}) + '\n')
                if known['physical']['status'].startswith('proven') or known['retention'].startswith('proven'): violations.append(item)
            elif info['outcome'].startswith('solver_proved'):
                if known['physical']['status'].startswith('feasible') or known['retention'] == 'verified_feasible': violations.append(item)
            records.append(item)
        if (offset + 1) % 100 == 0: print(json.dumps({'completed': offset + 1, 'elapsed_seconds': perf_counter() - started}), flush=True)
    outputs.close()
    report = {'count': len(cases), 'comparisons': len(records), 'statuses': dict(Counter(row['cpsat']['outcome'] for row in records)),
        'violations': violations, 'elapsed_seconds': perf_counter() - started, 'records': records,
        'scope': 'CP-SAT position+after-live interval+dead-row exact bridge model; original ordered args, RAW/WAR/WAW; '
                 'fixed/free model audited separately; no COPY optimality or independent portable CP infeasibility certificate',
        'reference_report_sha256': hashlib.sha256(Path(options.oracle_report).read_bytes()).hexdigest(),
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
        'optimized_outputs_sha256': hashlib.sha256((folder / 'optimized_outputs.jsonl').read_bytes()).hexdigest(),
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (Path(__file__), ROOT / 'isa_scheduler/retention_cpsat.py', ROOT / 'isa_scheduler/local_order.py')},
        'model_parameters': {'workers': 1, 'seed': 8320001, 'budget_ms': options.budget_ms}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'})); return int(bool(violations))


if __name__ == '__main__': raise SystemExit(main())
