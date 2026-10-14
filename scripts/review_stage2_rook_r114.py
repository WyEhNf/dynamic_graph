"""Root checks branch-set minor certificates using only original JSON data edges."""
import copy
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'projects/18-isa-scheduler/experiments/r114-rook-failures'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def check(data, cert):
    nodes = data['instructions']
    assert all(n['op'] in ('GET', 'SET', 'ADD', 'MULW') for n in nodes)
    graph = [set() for _ in nodes]
    for child, node in enumerate(nodes):
        for token in node.get('inputs', []):
            assert re.fullmatch(r't#[1-9][0-9]*', token)
            parent = child-int(token[2:])
            assert 0 <= parent < child and nodes[parent]['op'] != 'SET'
            graph[parent].add(child); graph[child].add(parent)
    # k=2 in Harvey/Wood v2 Theorem3: both parity cases simplify to this.
    d = cert['dimension']
    assert type(d) is int and d >= 2
    lower = d*(d+1)//2-1
    assert cert['kind'] == 'rook_branch_sets_treewidth'
    assert cert['treewidth_lower_bound'] == lower and cert['window'] == 2**data['bit_width']
    assert len(cert['branch_sets']) == d*d
    owner = {}
    for group, members in enumerate(cert['branch_sets']):
        assert members and len(set(members)) == len(members)
        for v in members:
            assert type(v) is int and 0 <= v < len(nodes) and v not in owner
            owner[v] = group
        selected = set(members)
        visited = {members[0]}; stack = [members[0]]
        while stack:
            neighbors = (graph[stack.pop()] & selected)-visited
            visited.update(neighbors); stack.extend(neighbors)
        assert visited == selected
    # A general minor need not cover every node; these saved certificates do.
    assert len(owner) == len(nodes)
    edges = {tuple(sorted((owner[u], owner[v]))) for u in owner for v in graph[u]
             if v in owner and owner[u] != owner[v]}
    required = {(u,v) for u in range(d*d) for v in range(u+1,d*d)
                if u//d == v//d or u%d == v%d}
    assert required <= edges and len(required) == d*d*(d-1)
    return dict(nodes=len(nodes), dimension=d, window=cert['window'], lower=lower,
                required_edges=len(required), minor_edges=len(edges), infeasible=lower>cert['window'])


def main():
    data = {fingerprint(r['input']): r['input'] for r in map(json.loads, (DIRECTORY/'inputs.jsonl').read_text().splitlines())}
    report = json.loads((DIRECTORY/'report.json').read_text())
    results = []
    tampered = 0
    for row in report['records']:
        if row['certificate'] is None:
            assert row['status'] == 'matcher_no_certificate'
            continue
        actual = check(data[row['sha256']], row['certificate'])
        assert actual['infeasible'] == (row['status'] == 'proved_infeasible_identity_model')
        results.append(dict(input_sha256=row['sha256'], **actual))
        bad = copy.deepcopy(row['certificate'])
        bad['branch_sets'][1].append(bad['branch_sets'][0][0])
        try:
            check(data[row['sha256']], bad)
        except AssertionError:
            tampered += 1
    assert len(results) == 8 and sum(r['infeasible'] for r in results) == 6 and tampered == 8
    result = dict(reviewed_unix=time.time(), passed=True, audited_minor_certificates=8,
                  new_identity_model_infeasible=6, necessary_bound_only=2,
                  overlap_tamper_rejections=tampered, results=results,
                  source_theorem='https://arxiv.org/html/1210.8205#S1.Thm3',
                  evidence={name: hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()
                            for name in ('inputs.jsonl','report.json')},
                  scope='Original data edges only; no project imports. Live-before plus current-node bags give treewidth<=W for any strict identity COPY-only schedule. Minor bound>W proves scoped infeasibility; bound<=W does not prove feasibility. No new emitted output or official Level claim.')
    (ROOT/'outputs/stage2-root-rook-r114.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','evidence')}))


if __name__ == '__main__':
    main()
