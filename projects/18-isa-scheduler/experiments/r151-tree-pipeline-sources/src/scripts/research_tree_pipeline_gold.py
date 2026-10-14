"""Independent complete interleaving gold for two raw unary chains."""
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
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check


def generated(left, right, bits):
    rows = []; chains = []
    for role, length in enumerate((left, right)):
        chain = []; index = len(rows); rows.append({'id': index, 'op': 'GET', 'reg': f'input-{role}'})
        chain.append(index)
        for offset in range(length - 1):
            index = len(rows); rows.append({'id': index, 'op': 'ADD' if (role + offset) % 2 else 'MULW', 'inputs': ['t#1', 't#1']}); chain.append(index)
        chains.append(chain)
    parent = len(rows); args = (chains[0][-1], chains[1][-1]) if (left + right) % 2 else (chains[1][-1], chains[0][-1])
    rows.append({'id': parent, 'op': 'MULW', 'inputs': [f't#{parent - s}' for s in args]})
    rows.append({'id': parent + 1, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']})
    return {'block_id': f'pipeline-gold-{left}-{right}-{bits}', 'bit_width': bits, 'instructions': rows}, chains


def orders(chains):
    def walk(left, right, prefix):
        if left == len(chains[0]) and right == len(chains[1]): yield prefix; return
        if left < len(chains[0]): yield from walk(left + 1, right, prefix + [chains[0][left]])
        if right < len(chains[1]): yield from walk(left, right + 1, prefix + [chains[1][right]])
    yield from walk(0, 0, [])


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = []; records = []; started = perf_counter()
    for left in range(1, 6):
        for right in range(1, 6):
            for bits in (2, 3, 4, 5):
                data, chains = generated(left, right, bits); cases.append(data)
                key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                optimum = None; tested = 0; witness = None
                for prefix in orders(chains):
                    order = prefix + [left + right, left + right + 1]
                    output = materialize(data, order); cost = sum(r['op'] == 'COPY' for r in output['optimized_instructions']); tested += 1
                    if optimum is None or cost < optimum: optimum = cost; witness = (output, order)
                candidate = schedule_tree_pipeline(parse_block(data), time_budget_ms=500, max_states=20000, max_outcomes=1024)
                check(data, candidate, candidate['stats']['original_order'])
                assert candidate['stats']['inserted_copy_count'] == optimum
                assert not candidate['stats']['tree_age']['truncated_outcomes']
                records.append({'sha256': key, 'lengths': [left, right], 'bit_width': bits, 'all_interleavings': tested,
                                'gold_copy_count': optimum, 'candidate_copy_count': candidate['stats']['inserted_copy_count'],
                                'candidate_stats': candidate['stats']})
                (folder / f'{key[:16]}-output.json').write_text(json.dumps({'input_sha256': key, 'output': candidate, 'original_order': candidate['stats']['original_order']}) + '\n')
                (folder / f'{key[:16]}-gold-output.json').write_text(json.dumps({'input_sha256': key, 'output': witness[0], 'original_order': witness[1]}) + '\n')
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in cases))
    report = {'count': len(records), 'elapsed_seconds': perf_counter() - started, 'total_interleavings': sum(r['all_interleavings'] for r in records),
              'all_candidate_match': True, 'records': records,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (Path(__file__), ROOT / 'isa_scheduler/tree_pipeline.py', ROOT / 'scripts/diagnose_tree_dfs_gap.py')},
              'scope': 'Full interleavings of only two isolated unary chains, no external identities; neither arbitrary tree nor global Level optimum claimed'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
