"""Static saved-order attribution; no new scheduler, DP, or oracle run."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'experiments/r155-tree-pipeline-old48'
    report = json.loads((source / 'report.json').read_text())
    cases = {r['input']['block_id']: r for r in map(json.loads, (source / 'inputs.jsonl').read_text().splitlines())}
    results = []
    for item in report['records']:
        if item['family'] not in ('padded_tree', 'ragged_tree') or not item['after_copies']: continue
        saved = json.loads((source / (item['sha256'][:16] + '-output.json')).read_text())
        data = cases[saved['output']['block_id']]['input']; rows = data['instructions']
        args = [tuple(dict.fromkeys(i - int(v[2:]) for v in row.get('inputs', []))) for i, row in enumerate(rows)]
        subtrees = []
        for i, sources in enumerate(args):
            subtree = {i}
            for s in sources: subtree.update(subtrees[s])
            subtrees.append(subtree)
        order = saved['original_order']; ranks = {n: i for i, n in enumerate(order)}
        for parent, kids in enumerate(args):
            if len(kids) != 2 or not any(any(len(args[n]) == 2 for n in subtrees[k]) for k in kids): continue
            members = subtrees[parent]; start = min(ranks[n] for n in members); stop = max(ranks[n] for n in members)
            if stop - start + 1 != len(members): continue
            a, b = (subtrees[k] for k in kids)
            roles = [0 if n in a else 1 for n in order[start:stop] if n != parent]
            switches = sum(x != y for x, y in zip(roles, roles[1:]))
            if switches <= 1: continue
            results.append({'input_sha256': item['sha256'], 'family': item['family'], 'original_nodes': len(rows),
                            'window': 2 ** data['bit_width'], 'parent': parent, 'subtree_nodes': len(members),
                            'children_sizes': [len(a), len(b)], 'rank_interval': [start, stop],
                            'order': order[start:stop + 1], 'roles': roles, 'switches': switches})
    results.sort(key=lambda r: (r['subtree_nodes'], r['window'], r['original_nodes']))
    print(json.dumps(results[:25], indent=2))


if __name__ == '__main__': main()
