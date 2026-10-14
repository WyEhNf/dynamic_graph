"""Read frozen R164 evidence only; never run a scheduler or oracle."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / 'experiments/r164-tree-pair-warmstart-84'
    folder = ROOT / 'experiments/r166-tree-pair-static-budget'
    folder.mkdir(exist_ok=False)
    shutil.copy2(__file__, folder / 'analysis-source.py')
    report = json.loads((source / 'report.json').read_text())
    cases = {}
    for line in (source / 'inputs.jsonl').read_text().splitlines():
        case = json.loads(line)
        data = case['input']
        key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        cases[key] = case
    rows = []
    for record in report['records']:
        stats = record['attempt'].get('stats', {})
        attempts = stats.get('attempts', [])
        if record['attempt']['outcome'] != 'partial_budget':
            continue
        data = cases[record['sha256']]['input']
        original = data['instructions']; args = []; users = [set() for _ in original]; cones = []
        for index, row in enumerate(original):
            operands = tuple(index-int(ref[2:]) for ref in row.get('inputs', []))
            args.append(operands)
            cone = {index}
            for source_index in set(operands):
                users[source_index].add(index); cone.update(cones[source_index])
            cones.append(cone)
        saved_path = source / (record['sha256'][:16] + '-baseline-output.json')
        saved = json.loads(saved_path.read_text()); order = saved['original_order']; ranks = {v:i for i,v in enumerate(order)}
        attempt = attempts[-1]; parent = attempt['parent']; members = cones[parent]
        start = min(ranks[v] for v in members); stop = max(ranks[v] for v in members)
        child_roots = tuple(dict.fromkeys(args[parent]))
        sides = [tuple(v for v in order[start:stop] if v in cones[child]) for child in child_roots]
        prefix = []; latest = {}; done = set(); cursor = 0
        for physical in saved['output']['optimized_instructions']:
            if cursor == start: break
            if physical['op'] == 'COPY':
                identity = prefix[len(prefix)-int(physical['source'][2:])]
            else:
                identity = order[cursor]; cursor += 1; done.add(identity)
                if physical['op'] == 'SET': identity = None
            prefix.append(identity)
            if identity is not None: latest[identity] = len(prefix)-1
        external = sorted(v for v in done if users[v]-done)
        depths = []
        for progress in range(sum(map(len, sides))+1):
            live_counts = []
            for i in range(len(sides[0])+1):
                j = progress-i
                if not 0 <= j <= len(sides[1]): continue
                born = set(sides[0][:i]) | set(sides[1][:j])
                live_counts.append(len(external) + sum(bool(users[v]-born) for v in born))
            depths.append({'progress': progress, 'prefix_pairs': len(live_counts),
                           'structural_live_min': min(live_counts), 'structural_live_max': max(live_counts)})
        rows.append({'sha256': record['sha256'], 'group': record['group'], 'family': record['family'],
                     'node_count': len(original), 'window': 2**data['bit_width'], 'before_copies': record['before_copies'],
                     'attempt_index': len(attempts)-1, 'attempt_count': len(attempts), 'parent': parent,
                     'actual_processed_states': attempt['processed_states'], 'actual_completed_outputs': attempt['complete_outputs'],
                     'actual_message': attempt['message'], 'actual_frontier_ages': None,
                     'actual_frontier_note': 'R164 did not serialize unfinished frontier/depth/ages. Cannot reconstruct the actual frontier without rerunning; no rerun here.',
                     'side_lengths': list(map(len, sides)), 'rank_interval': [start, stop],
                     'external_roles': external, 'external_ages': [len(prefix)-latest[v] for v in external],
                     'all_order_interleaving_count_upper_bound': math.comb(sum(map(len, sides)), len(sides[0])),
                     'structural_prefix_live_profile_not_actual_frontier': depths,
                     'saved_baseline_path': str(saved_path.relative_to(ROOT)), 'saved_baseline_sha256': digest(saved_path)})
    result = {'scope': 'Static frozen-input/saved-output analysis, no candidate/oracle/performance run. Structural live profile is not actual physical-age frontier.',
              'partial_count': len(rows), 'first_pair_state_exhaustions': sum(r['attempt_index']==0 and 'state budget' in r['actual_message'] for r in rows),
              'state_exhaustions': sum('state budget' in r['actual_message'] for r in rows),
              'zero_completed_outputs': sum(r['actual_completed_outputs']==0 for r in rows),
              'partial_groups': dict(Counter((r['family'] + '/W' + str(r['window'])) for r in rows)), 'records': rows}
    (folder / 'report.json').write_text(json.dumps(result, indent=2)+'\n')
    evidence = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), source/'report.json', source/'inputs.jsonl', source/'src/isa_scheduler/tree_subtree_interleave.py']}
    (folder / 'provenance.json').write_text(json.dumps({'frozen_utc': datetime.now(timezone.utc).isoformat(), 'inputs_source_sha256': evidence, 'report_sha256': digest(folder/'report.json')}, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))


if __name__ == '__main__': main()
