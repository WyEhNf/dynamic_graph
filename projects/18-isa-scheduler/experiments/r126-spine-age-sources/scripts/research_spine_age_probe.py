"""Augment saved, independently checked incumbents; do not rerun old schedules."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block, InfeasibleSchedule, BudgetExceeded
from isa_scheduler.spine_age import schedule_spine_age
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify, interpret, IntegerSemantics


def check(data, output, order):
    verify(data, output); check_identity_witness(data, output, order)
    registers = {row['reg']: 71 - 23 * i for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
    for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
        assert interpret(data['instructions'], registers, semantics) == interpret(output['optimized_instructions'], registers, semantics)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--source', default='experiments/r107-age-portfolio-336')
    parser.add_argument('--families', default='cross_group_shared'); parser.add_argument('--budget-ms', type=float, default=1000)
    parser.add_argument('--beams', default='1,4'); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False); source = ROOT / options.source
    report = json.loads((source / 'report.json').read_text()); variant = report['paired_variants']['after']
    old = {r['sha256']: r for r in report['records'] if r['variant'] == variant}
    outputs = {row['input_sha256']: row['output'] for row in map(json.loads, (source / 'optimized_outputs.jsonl').read_text().splitlines()) if row['variant'] == variant}
    orders = {row['input_sha256']: row['original_order'] for row in map(json.loads, (source / 'original_orders.jsonl').read_text().splitlines()) if row['variant'] == variant}
    families = set(options.families.split(',')); cases = [case for case in map(json.loads, (source / 'inputs.jsonl').read_text().splitlines()) if case['family'] in families]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = fingerprint(data); block = parse_block(data); incumbent = outputs.get(key)
        incumbent_order = orders.get(key); before = old[key]; attempts = []
        if incumbent is not None:
            check(data, incumbent, incumbent_order)
            assert sum(row['op'] == 'COPY' for row in incumbent['optimized_instructions']) == before['inserted_copies']
        best = incumbent; best_order = incumbent_order; best_copies = before.get('inserted_copies', None)
        for beam in map(int, options.beams.split(',')):
            if best_copies == 0: break
            tick = perf_counter()
            try:
                candidate = schedule_spine_age(block, time_budget_ms=options.budget_ms, beam_width=beam)
                order = candidate['stats']['original_order']; check(data, candidate, order)
                if before['status'] == 'proven_infeasible_under_model':
                    raise AssertionError('New strict witness contradicts saved model proof; audit required')
                copies = candidate['stats']['inserted_copy_count']
                attempts.append({'beam': beam, 'outcome': 'verified_candidate', 'copies': copies, 'stats': candidate['stats']})
                if best_copies is None or copies < best_copies:
                    best = {'block_id': data['block_id'], 'optimized_instructions': candidate['optimized_instructions']}
                    best_order = order; best_copies = copies
            except (InfeasibleSchedule, BudgetExceeded) as error:
                attempts.append({'beam': beam, 'outcome': 'unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure', 'message': str(error)})
            attempts[-1]['full_seconds'] = perf_counter() - tick
        item = {'sha256': key, 'family': case['family'], 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
            'old_status': before['status'], 'before_copies': before.get('inserted_copies'), 'after_copies': best_copies,
            'after_status': 'verified' if best is not None else before['status'], 'attempts': attempts}
        records.append(item)
        if best is not None:
            check(data, best, best_order)
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': best, 'original_order': best_order}) + '\n')
        print(json.dumps({key: value for key, value in item.items() if key != 'attempts'}), flush=True)
        (folder / 'partial-records.json').write_text(json.dumps(records, indent=2) + '\n')
    result = {'source': options.source, 'count': len(cases), 'elapsed_seconds': perf_counter() - started,
        'before_statuses': dict(Counter(row['old_status'] for row in records)), 'after_statuses': dict(Counter(row['after_status'] for row in records)),
        'before_copies': sum(row['before_copies'] or 0 for row in records), 'after_copies': sum(row['after_copies'] or 0 for row in records),
        'common_success_count': sum(row['before_copies'] is not None and row['after_copies'] is not None for row in records),
        'common_before_copies': sum(row['before_copies'] for row in records if row['before_copies'] is not None and row['after_copies'] is not None),
        'common_after_copies': sum(row['after_copies'] for row in records if row['before_copies'] is not None and row['after_copies'] is not None),
        'recovered_outputs': sum(row['before_copies'] is None and row['after_copies'] is not None for row in records),
        'records': records, 'parameters': {'beams': options.beams, 'budget_ms_each_beam': options.budget_ms},
        'scope': 'Strict original-prefix/physical-age restricted beam; saved legal incumbent retained; all source inputs preserved in selection; no global proof/optimum/Level score',
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__), ROOT / 'isa_scheduler/spine_age.py')},
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
        'baseline_report_sha256': hashlib.sha256((source / 'report.json').read_bytes()).hexdigest()}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'records'}))


if __name__ == '__main__': main()
