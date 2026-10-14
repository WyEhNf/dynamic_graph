"""Raw identity timing/order attribution of two actual padded tree deficits."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.tree_raw_oracles import raw_graph, dfs_deadline_optimum
from scripts.research_spine_age_probe import check


def materialize(data, order):
    args, deps, users = raw_graph(data); originals = data['instructions']; window = 2 ** data['bit_width']
    rows = []; live = {}; done = 0
    for index in order:
        if deps[index] & done != deps[index]: raise ValueError('Illegal raw proposed order')
        rotations = 0
        while live:
            oldest = min(live, key=live.get); age = len(rows) - live[oldest]
            if age < window or oldest in args[index]: break
            if age > window or rotations >= window: raise ValueError('Restricted relay cannot progress')
            rows.append({'id': len(rows), 'op': 'COPY', 'source': f't#{age}'})
            live[oldest] = len(rows) - 1; rotations += 1
        row = {'id': len(rows), 'op': originals[index]['op']}
        if 'reg' in originals[index]: row['reg'] = originals[index]['reg']
        if args[index]: row['inputs'] = [f't#{len(rows) - live[source]}' for source in args[index]]
        rows.append(row)
        for source in set(args[index]): del live[source]
        done |= 1 << index
        if users[index] & ~done: live[index] = len(rows) - 1
    result = {'block_id': data['block_id'], 'optimized_instructions': rows}; check(data, result, order)
    return result


def describe(data, output, order):
    args, _, _ = raw_graph(data); ranks = {node: rank for rank, node in enumerate(order)}
    subtrees = []
    for node, sources in enumerate(args):
        descendants = {node}
        for source in set(sources): descendants |= subtrees[source]
        subtrees.append(descendants)
    gaps = []
    for root, subtree in enumerate(subtrees):
        start = min(ranks[node] for node in subtree); stop = max(ranks[node] for node in subtree)
        outsiders = [node for node in order[start:stop + 1] if node not in subtree]
        if outsiders: gaps.append({'subtree_root': root, 'subtree_size': len(subtree),
            'rank_interval': [start, stop], 'outsiders': outsiders[:16]})
    history = []; cursor = 0; traces = []; original_slot = {}
    for position, row in enumerate(output['optimized_instructions']):
        if row['op'] == 'COPY':
            distance = int(row['source'][2:]); identity = history[position - distance]
            traces.append({'physical_slot': position, 'original_identity': identity, 'source_distance': distance,
                           'original_birth_slot': original_slot[identity], 'original_prefix': cursor})
        else:
            identity = order[cursor]; cursor += 1; original_slot[identity] = position
            if row['op'] == 'SET': identity = None
        history.append(identity)
    return {'DFS_contiguous': not gaps, 'interleaving_subtrees': gaps[:12], 'copies': len(traces),
            'early_copy_count': sum(t['source_distance'] < 2 ** data['bit_width'] for t in traces),
            'copy_distances': dict(Counter(t['source_distance'] for t in traces)), 'copy_traces': traces}


def main():
    folder = ROOT / 'experiments/r150-tree-dfs-diagnosis'; folder.mkdir(exist_ok=False)
    source = ROOT / 'experiments/r148-tree-age-old48'; report = json.loads((source / 'report.json').read_text())
    bank = {r['sha256']: r for r in report['records']}; cases = list(map(json.loads, (source / 'inputs.jsonl').read_text().splitlines()))
    selected = [c for c in cases if c['family'] == 'padded_tree' and
                ((len(c['input']['instructions']), c['input']['bit_width']) in ((64, 2), (256, 3)))]
    (folder / 'inputs.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in selected))
    records = []
    for case in selected:
        data = case['input']; key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        saved = json.loads((source / f'{key[:16]}-baseline-output.json').read_text())
        dfs_order = bank[key]['attempt']['stats']['original_order']; dfs_output = materialize(data, dfs_order)
        assert sum(row['op'] == 'COPY' for row in dfs_output['optimized_instructions']) == bank[key]['attempt']['copies']
        check(data, saved['output'], saved['original_order'])
        (folder / f'{key[:16]}-DFS-output.json').write_text(json.dumps({'input_sha256': key, 'output': dfs_output, 'original_order': dfs_order}) + '\n')
        (folder / f'{key[:16]}-baseline-output.json').write_text(json.dumps(saved) + '\n')
        records.append({'sha256': key, 'node_count': len(data['instructions']), 'bit_width': data['bit_width'],
                        'baseline': describe(data, saved['output'], saved['original_order']),
                        'DFS': describe(data, dfs_output, dfs_order), 'outcomes_truncated': bank[key]['attempt']['stats']['tree_age']['truncated_outcomes']})
    # Complete10-row counterexample, not a changed member of the quality corpus.
    rows = [{'id': 0, 'op': 'GET', 'reg': 'a'}]
    for i in range(1, 4): rows.append({'id': i, 'op': 'ADD', 'inputs': ['t#1', 't#1']})
    rows.append({'id': 4, 'op': 'GET', 'reg': 'b'})
    for i in range(5, 8): rows.append({'id': i, 'op': 'MULW', 'inputs': ['t#1', 't#1']})
    rows += [{'id': 8, 'op': 'ADD', 'inputs': ['t#5', 't#1']}, {'id': 9, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]
    data = {'block_id': 'minimal-two-padded-chains', 'bit_width': 2, 'instructions': rows}
    dfs_order = list(range(10)); pipeline_order = [0, 4, 1, 5, 2, 6, 3, 7, 8, 9]
    dfs_output = materialize(data, dfs_order); pipeline_output = materialize(data, pipeline_order)
    proof = dfs_deadline_optimum(data); assert proof['copies'] == 1
    assert not any(row['op'] == 'COPY' for row in pipeline_output['optimized_instructions'])
    (folder / 'two-chains-input.json').write_text(json.dumps(data, indent=2) + '\n')
    for name, output, order in [('DFS', dfs_output, dfs_order), ('pipeline', pipeline_output, pipeline_order)]:
        (folder / f'two-chains-{name}-output.json').write_text(json.dumps({'output': output, 'original_order': order}, indent=2) + '\n')
    result = {'records': records, 'counterexample': {'nodes': 10, 'window': 4, 'DFS_family_copies': proof['copies'],
               'pipeline_copies': 0, 'DFS_family': proof,
               'scope': 'Minimal in the two independent equal-length unary-chain family: both subtrees need at leastW original rows for DFS waiting to exceedW; n>=2W+2=10. Not claimed universally minimal over all graphs.'},
              'sources_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 (Path(__file__), ROOT / 'scripts/tree_raw_oracles.py', source / 'report.json')},
              'conclusion': 'Actual old better orders interleave original subtrees; their COPYs are all deadlineW. DFS-only cannot express this, cache symmetry cannot remove the gap. All original rows/ordered args preserved; no old corpus input was reduced.'}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'actual': [{'n': r['node_count'], 'baseline': {k: r['baseline'][k] for k in ('copies','DFS_contiguous','early_copy_count')},
                                'DFS': {k: r['DFS'][k] for k in ('copies','DFS_contiguous','early_copy_count')}}for r in records],
                      'counterexample': result['counterexample'], 'conclusion': result['conclusion']}))


if __name__ == '__main__': main()
