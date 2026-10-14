"""Fixed-budget, one-worker diagnostic of the two remaining matrix inputs."""
import argparse
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
    parser.add_argument('--budget-ms', type=float, default=30000); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = [json.loads(line) for line in (ROOT / 'experiments/r110-retention-failures/inputs.jsonl').read_text().splitlines()]
    cases = [case for case in cases if (len(case['input']['instructions']), case['input']['bit_width']) in ((160, 4), (784, 5))]
    assert len(cases) == 2
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    started = perf_counter(); records = []
    for case in cases:
        data = case['input']; key = fingerprint(data); block = parse_block(data); model_path = folder / f'{key[:16]}.pbtxt'
        order, info = solve_retention_cpsat(block, time_budget_ms=options.budget_ms, workers=1,
                                          seed=8320001, export_model=model_path)
        item = {'sha256': key, 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
                'cpsat': info, 'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest()}
        if order is not None:
            output = emit_order(block, order, deadline=perf_counter() + 5)
            if output is None: raise AssertionError('CP-SAT matrix order failed actual COPY emission')
            verify(data, output); check_identity_witness(data, output, order)
            initial = {row['reg']: 47 - 17 * i for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
            for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                assert interpret(data['instructions'], initial, semantics) == interpret(output['optimized_instructions'], initial, semantics)
            core = {'block_id': data['block_id'], 'optimized_instructions': output['optimized_instructions']}
            item.update(copies=output['stats']['inserted_copy_count'], output_count=len(core['optimized_instructions']))
            (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': core, 'original_order': order}, indent=2) + '\n')
        records.append(item); print(json.dumps(item), flush=True)
        (folder / 'partial-records.json').write_text(json.dumps(records, indent=2) + '\n')
    report = {'count': len(cases), 'elapsed_seconds': perf_counter() - started, 'records': records,
        'parameters': {'workers': 1, 'seed': 8320001, 'budget_ms': options.budget_ms},
        'scope': 'Exact feasibility only, not COPY optimum; no default promotion; backend proof distinguished from portable certificate; unknown remains unknown',
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__), ROOT / 'isa_scheduler/retention_cpsat.py')},
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest()}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(folder / 'report.json'), 'elapsed_seconds': report['elapsed_seconds']}))


if __name__ == '__main__': main()
