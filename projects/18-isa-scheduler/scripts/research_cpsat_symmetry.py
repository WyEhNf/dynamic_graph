"""Same-input fixed-budget pair against the actual frozen R119 CP model."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.retention_cpsat import solve_retention_cpsat
from isa_scheduler.matrix_symmetry import propose_matrix_symmetry, check_matrix_symmetry
from isa_scheduler.local_order import emit_order
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify, interpret, IntegerSemantics
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.workloads import generate_workload


def transformed(data, seed):
    block = parse_block(data); rng = random.Random(seed); completed = set(); order = []
    while len(order) < len(block.instructions):
        ready = [node.index for node in block.instructions if node.index not in completed and set(node.args) <= completed]
        current = rng.choice(ready); completed.add(current); order.append(current)
    positions = {original: offset for offset, original in enumerate(order)}; rows = []
    for offset, original in enumerate(order):
        node = block.instructions[original]; row = {'id': f'id-{seed}-{original * 17}', 'op': node.op}
        if node.reg is not None: row['reg'] = f'reg-{seed}-{original}'
        args = list(node.args)
        if len(args) == 2 and rng.randrange(2): args.reverse()
        if args: row['inputs'] = [f't#{offset - positions[source]}' for source in args]
        rows.append(row)
    return {'block_id': f'sym-holdout-{seed}', 'bit_width': data['bit_width'], 'instructions': rows}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--holdout', action='store_true'); parser.add_argument('--budget-ms', type=float, default=30000)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    if options.holdout:
        cases = []
        for size in (32, 128):
            for bits in (2, 3, 4, 5):
                for sample in range(3):
                    seed = 8350001 + size * 31 + bits * 3 + sample
                    data = transformed(generate_workload(seed, 'matrix_product_tile', size, bits), seed)
                    cases.append({'family': 'matrix_product_tile_new_permutation', 'seed': seed, 'input': data})
    else:
        cases = [json.loads(line) for line in (ROOT / 'experiments/r110-retention-failures/inputs.jsonl').read_text().splitlines()]
        cases = [case for case in cases if (len(case['input']['instructions']), case['input']['bit_width']) in ((160, 4), (784, 5))]
        assert len(cases) == 2
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    baseline_path = ROOT / 'experiments/r119-cpsat-sources/isa_scheduler/retention_cpsat.py'
    spec = importlib.util.spec_from_file_location('isa_scheduler.retention_cpsat_r119', baseline_path)
    baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)
    records = []; violations = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = fingerprint(data); block = parse_block(data)
        plan = propose_matrix_symmetry(block)
        if plan is None: raise AssertionError('Declared strict matrix did not match')
        raw_symmetry = check_matrix_symmetry(data, plan)
        (folder / f'{key[:16]}-symmetry.json').write_text(json.dumps(plan, indent=2) + '\n')
        pair = []
        for name, function, kwargs in [('plain_r119', baseline.solve_retention_cpsat, {}),
                                      ('symmetry', solve_retention_cpsat, {'symmetry_plan': plan})]:
            model_path = folder / f'{key[:16]}-{name}.pbtxt'; tick = perf_counter()
            order, info = function(block, time_budget_ms=options.budget_ms, workers=1, seed=8320001, export_model=model_path, **kwargs)
            item = {'sha256': key, 'variant': name, 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
                    'cpsat': info, 'raw_symmetry': raw_symmetry, 'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest()}
            if order is not None:
                output = emit_order(block, order, deadline=perf_counter() + 5)
                if output is None: raise AssertionError('Valid order failed bridge')
                verify(data, output); check_identity_witness(data, output, order)
                initial = {row['reg']: 51 - 19 * i for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
                for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                    assert interpret(data['instructions'], initial, semantics) == interpret(output['optimized_instructions'], initial, semantics)
                if name == 'symmetry':
                    positions = {original: offset for offset, original in enumerate(order)}
                    for axis in ('row_groups', 'column_groups'):
                        births = [min(positions[root] for root in group) for group in plan[axis]]
                        assert births == sorted(births)
                item['copies'] = output['stats']['inserted_copy_count']
                core = {'block_id': data['block_id'], 'optimized_instructions': output['optimized_instructions']}
                (folder / f'{key[:16]}-{name}-output.json').write_text(json.dumps({'input_sha256': key, 'output': core, 'original_order': order}, indent=2) + '\n')
            item['full_seconds'] = perf_counter() - tick; records.append(item); pair.append(item)
            print(json.dumps(item), flush=True)
            (folder / 'partial-records.json').write_text(json.dumps(records, indent=2) + '\n')
        states = {item['cpsat']['outcome'] for item in pair}
        if 'constructive_original_order' in states and 'solver_proved_infeasible_stated_model' in states: violations.append(pair)
    report = {'count': len(cases), 'comparisons': len(records), 'violations': violations,
        'statuses': {variant: dict(Counter(item['cpsat']['outcome'] for item in records if item['variant'] == variant)) for variant in ('plain_r119', 'symmetry')},
        'elapsed_seconds': perf_counter() - started, 'records': records,
        'parameters': {'workers': 1, 'seed': 8320001, 'budget_ms': options.budget_ms},
        'scope': 'Resource automorphism root-group first-birth sorting only; all internal original operations free; '
                 'real original IDs, ordered operands, regs emitted unchanged; backend negatives scoped; UNKNOWN remains unknown; no COPY optimality',
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (Path(__file__), ROOT / 'isa_scheduler/retention_cpsat.py', ROOT / 'isa_scheduler/matrix_symmetry.py', baseline_path)},
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest()}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'})); return int(bool(violations))


if __name__ == '__main__': raise SystemExit(main())
