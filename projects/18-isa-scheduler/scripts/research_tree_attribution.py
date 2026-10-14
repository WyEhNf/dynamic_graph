"""Read all frozen336/72 inputs and saved incumbents; no scheduling search."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.tree_age import match_forest


def rows(path):
    with path.open() as stream:
        for line in stream: yield json.loads(line)


def main():
    folder = ROOT / 'experiments/r144-tree-attribution'; folder.mkdir(exist_ok=False)
    stages = {}; hashes = {}
    for stage, floor_stage in [('r107-age-portfolio-336', 'r143-root-lifetime-summary'),
                               ('r108-age-portfolio-heldout', 'r123-age-holdout-floor')]:
        source = ROOT / 'experiments' / stage
        report = json.loads((source / 'report.json').read_text()); variant = report['paired_variants']['after']
        measured = {row['sha256']: row for row in report['records'] if row['variant'] == variant}
        cases = list(rows(source / 'inputs.jsonl'))
        # Corpus case SHA uses sorted-key compact JSON, independently rebuilt.
        input_map = {hashlib.sha256(json.dumps(c['input'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(): c for c in cases}
        assert input_map.keys() == measured.keys()
        orders = {r['input_sha256']: r['original_order'] for r in rows(source / 'original_orders.jsonl') if r['variant'] == variant}
        floor_path = ROOT / 'experiments' / floor_stage / 'report.json'
        floors = {r['sha256']: r.get('joint_lower', r.get('copy_lower_bound')) for r in json.loads(floor_path.read_text())['records']}
        results = {}; groups = defaultdict(list)
        for key, case in input_map.items():
            block = parse_block(case['input']); row = measured[key]
            item = {'sha256': key, 'family': case['family'], 'node_count': len(block.instructions),
                    'bit_width': block.bit_width, 'status': row['status'], 'necessary_lower': floors[key]}
            try:
                forest = match_forest(block)
                item.update(tree_match=True, tree_depth=forest['depth'], components=len(forest['roots']), unused_GET=len(forest['unused']))
            except ValueError as error:
                item.update(tree_match=False, matcher_reason=str(error))
            if row['status'] == 'verified':
                item.update(copies=row['inserted_copies'], gap_upper=row['inserted_copies'] - floors[key])
            results[key] = item
        # Physical identity provenance only, retaining genuine original SET
        # non-results. This is attribution; earlier full replay is separate.
        for saved in rows(source / 'optimized_outputs.jsonl'):
            if saved['variant'] != variant: continue
            key = saved['input_sha256']; originals = input_map[key]['input']['instructions']; order = orders[key]
            history = []; cursor = 0; copied = Counter()
            for position, row in enumerate(saved['output']['optimized_instructions']):
                if row['op'] == 'COPY':
                    d = int(row['source'][2:]); assert 1 <= d <= 2 ** results[key]['bit_width'] and d <= position
                    identity = history[position - d]; assert identity is not None
                    copied[identity] += 1
                else:
                    identity = order[cursor]; cursor += 1
                    assert row['op'] == originals[identity]['op']
                    if row['op'] == 'SET': identity = None
                history.append(identity)
            assert cursor == len(originals) and sum(copied.values()) == results[key]['copies']
            by_op = Counter()
            for identity, count in copied.items(): by_op[originals[identity]['op']] += count
            results[key]['copy_original_op'] = dict(by_op)
            results[key]['top_copy_identities'] = [{'original_index': i, 'op': originals[i]['op'], 'copies': c}
                                                    for i, c in copied.most_common(8)]
        for item in results.values(): groups[item['family']].append(item)
        summaries = {}
        for family, items in groups.items():
            legal = [r for r in items if r['status'] == 'verified']; carriers = Counter()
            for r in legal: carriers.update(r['copy_original_op'])
            summaries[family] = {'count': len(items), 'statuses': dict(Counter(r['status'] for r in items)),
                'tree_match': sum(r['tree_match'] for r in items), 'copies': sum(r['copies'] for r in legal),
                'necessary_lower_successes': sum(r['necessary_lower'] for r in legal),
                'gap_upper': sum(r['gap_upper'] for r in legal), 'copy_original_op': dict(carriers)}
        stages[stage] = {'count': len(results), 'statuses': dict(Counter(r['status'] for r in results.values())),
                         'families': summaries, 'records': list(results.values())}
        for name in ('report.json', 'inputs.jsonl', 'optimized_outputs.jsonl', 'original_orders.jsonl'):
            path = source / name; hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(floor_path.relative_to(ROOT))] = hashlib.sha256(floor_path.read_bytes()).hexdigest()
        print(json.dumps({'stage': stage, 'families': summaries}))
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'stages': stages, 'sources_sha256': hashes,
              'scope': 'Frozen original336/72 statuses and incumbents preserved. Pure-tree input matcher and physical original COPY attribution only, no solver/score changes. C-L is upper remaining opportunity, not attainable promise.'}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
