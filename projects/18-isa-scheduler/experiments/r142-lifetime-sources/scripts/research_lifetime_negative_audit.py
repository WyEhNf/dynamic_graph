"""Fresh pure-clique and register-barrier strata; all negative/unknowns kept."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.research_lifetime_state_audit import audit


def generated(seed, family, roots):
    rng = random.Random(seed); rows = []
    def emit(op, args=(), reg=None):
        index = len(rows); row = {'id': f'negative-{seed}-{index}', 'op': op}
        if reg is not None: row['reg'] = reg
        if args: row['inputs'] = [f't#{index - source}' for source in args]
        rows.append(row); return index
    values = [emit('GET', reg='epoch' if family == 'hazard_barrier' else f'r{i}') for i in range(roots)]
    if family == 'hazard_barrier':
        emit('SET', (values[0],), 'epoch'); fresh = emit('GET', reg='epoch')
        for index, source in enumerate(values):
            output = emit('ADD', (fresh, source) if rng.randrange(2) else (source, fresh))
            emit('SET', (output,), f'out{index}')
    else:
        pairs = list(itertools.combinations(values, 2)); rng.shuffle(pairs)
        for index, pair in enumerate(pairs):
            output = emit('MULW', pair if rng.randrange(2) else tuple(reversed(pair)))
            emit('SET', (output,), f'out{index}')
    emit('GET', reg='unused')
    return {'block_id': f'lifetime-negative-{seed}', 'bit_width': 2, 'instructions': rows}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True)
    parser.add_argument('--budget-ms', type=float, default=500); parser.add_argument('--max-states', type=int, default=20000)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = []
    for family in ('pure_clique', 'hazard_barrier'):
        for roots in (4, 5):
            for sample in range(4):
                seed = 8420001 + len(cases)
                cases.append({'family': family, 'root_count': roots, 'seed': seed, 'input': generated(seed, family, roots)})
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases))
    records = []; started = perf_counter()
    for case in cases:
        row = audit(case['input'], budget_ms=options.budget_ms, max_states=options.max_states)
        row.update(family=case['family'], root_count=case['root_count'], seed=case['seed']); records.append(row)
    report = {'count': len(cases), 'elapsed_seconds': perf_counter() - started,
              'statuses': dict(Counter(row['status'] for row in records)),
              'finite_states_checked': sum(row.get('finite_remaining_states', 0) for row in records),
              'positive_floor_states': sum(row.get('positive_floor_states', 0) for row in records),
              'dead_remaining_states': sum(row.get('dead_remaining_states', 0) for row in records),
              'violations': [row for row in records if row.get('violations')], 'records': records,
              'parameters': vars(options),
              'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (Path(__file__), ROOT / 'scripts/research_lifetime_state_audit.py', ROOT / 'isa_scheduler/spine_lifetime.py')},
              'scope': 'Fresh negative mechanisms and feasible graphs with dead prefixes; completed graphs only exact; unknowns not negated'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))
    return int(bool(report['violations']))


if __name__ == '__main__': raise SystemExit(main())
