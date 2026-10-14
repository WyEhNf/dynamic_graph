"""Phase1 only: specified original64 trees and fixed saved original orders."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_subtree_interleave import schedule_fixed_tree_pair
from scripts.research_spine_age_probe import check
from scripts.tree_raw_oracles import raw_graph


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def main():
    folder = ROOT / 'experiments/r158-tree-fixed-pair-diagnostic'; folder.mkdir(exist_ok=False)
    sources = [ROOT / 'isa_scheduler/tree_subtree_interleave.py', ROOT / 'isa_scheduler/tree_pipeline.py',
               ROOT / 'isa_scheduler/model.py', ROOT / 'scripts/research_spine_age_probe.py',
               ROOT / 'scripts/tree_raw_oracles.py', Path(__file__),
               ROOT / 'research/level-stage/tree-subtree-interleave-plan.md']
    manifest = {}
    for source in sources:
        target = folder / 'src' / source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target); manifest[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    frozen = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': manifest,
              'scope': 'Actual phase1 source frozen before any local DP runs; no default/global quality change'}
    (folder / 'source-provenance.json').write_text(json.dumps(frozen, indent=2) + '\n')
    source = ROOT / 'experiments/r155-tree-pipeline-old48'
    cases = [case for case in map(json.loads, (source / 'inputs.jsonl').read_text().splitlines())
             if case['family'] in ('padded_tree', 'ragged_tree') and len(case['input']['instructions']) == 64
             and case['input']['bit_width'] == 2]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(case) + '\n' for case in cases))
    records = []; started = perf_counter()
    for case in cases:
        data = case['input']; key = fingerprint(data)
        saved = json.loads((source / (key[:16] + '-output.json')).read_text())
        check(data, saved['output'], saved['original_order'])
        (folder / (key[:16] + '-baseline-output.json')).write_text(json.dumps(saved) + '\n')
        args, _, _ = raw_graph(data); children = [tuple(dict.fromkeys(v)) for v in args]; subtrees = []
        for node, kids in enumerate(children):
            subtree = {node}
            for child in kids: subtree.update(subtrees[child])
            subtrees.append(subtree)
        parents = [60] if case['family'] == 'padded_tree' else [i for i, kids in enumerate(children)
            if len(kids) == 2 and any(any(len(children[node]) == 2 for node in subtrees[k]) for k in kids)]
        before = sum(row['op'] == 'COPY' for row in saved['output']['optimized_instructions'])
        for parent in parents:
            phase = 'schedule'; tick = perf_counter()
            record = {'input_sha256': key, 'family': case['family'], 'parent': parent, 'before_copies': before}
            try:
                result = schedule_fixed_tree_pair(data, saved, parent, time_budget_ms=500, max_states=20000, max_outcomes=16)
                phase = 'independent_verify'
                for index, candidate in enumerate(result['completed_outlets']):
                    check(data, candidate['output'], candidate['original_order'])
                    (folder / (key[:16] + f'-parent{parent}-outlet{index}-output.json')).write_text(json.dumps(candidate) + '\n')
                record.update({'outcome': 'verified_complete_candidates', 'after_copies': result['best']['copies'],
                               'stats': result['stats'], 'completed_outlets': len(result['completed_outlets']),
                               'best_original_order': result['best']['original_order']})
            except (BudgetExceeded, InfeasibleSchedule, ValueError) as error:
                if phase == 'independent_verify': raise
                record.update({'outcome': 'unknown_budget' if isinstance(error, BudgetExceeded) else 'restricted_candidate_failure',
                               'message': str(error), 'after_copies': before})
            record['candidate_and_verify_seconds'] = perf_counter() - tick; records.append(record)
    report = {'count': len(records), 'input_count': len(cases), 'records': records,
              'outcomes': dict(Counter(r['outcome'] for r in records)),
              'improvements': sum(r['after_copies'] < r['before_copies'] for r in records),
              'elapsed_seconds': perf_counter() - started, 'parameters': {'time_budget_ms':500, 'max_states':20000, 'max_outcomes':16},
              'scope':'Phase1 only, every attempt compared to the same saved full-block incumbent; no compositional gains claimed. No stage2, whole336 or promotion.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    evidence = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*') if p.is_file()}
    (folder / 'evidence-provenance.json').write_text(json.dumps({'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_sha256': evidence}, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'records'}))
    print(json.dumps([{k:r[k] for k in ('family','parent','before_copies','after_copies','outcome')} for r in records]))


if __name__ == '__main__': main()
