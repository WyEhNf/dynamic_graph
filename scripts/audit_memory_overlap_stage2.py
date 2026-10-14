"""Independent forced-output overlap lower bound for project 27.

No submitted scheduling code or witness order is used. A producer p is forced
live at the start of v when p is a strict ancestor of v and one DIRECT consumer
of p is v or a descendant of v. This remains necessary for parallel schedules:
p has completed, whereas that direct consumer cannot have completed yet.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path


def graph(nodes):
    index = {node['id']: i for i, node in enumerate(nodes)}
    assert len(index) == len(nodes)
    incoming = [set(index[p] for p in node['inputs']) for node in nodes]
    outgoing = [set() for _ in nodes]
    for i, parents in enumerate(incoming):
        for p in parents:
            outgoing[p].add(i)
    degree = list(map(len, incoming))
    topo = [i for i, d in enumerate(degree) if not d]
    for i in topo:
        for c in outgoing[i]:
            degree[c] -= 1
            if not degree[c]:
                topo.append(c)
    assert len(topo) == len(nodes)
    return incoming, outgoing, topo


def bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def bound(nodes):
    incoming, outgoing, topo = graph(nodes)
    ancestor = [0] * len(nodes)
    descendant = [0] * len(nodes)
    for i in topo:
        for p in incoming[i]:
            ancestor[i] |= ancestor[p] | (1 << p)
    for i in reversed(topo):
        descendant[i] = 1 << i
        for c in outgoing[i]:
            descendant[i] |= descendant[c]
    child_bits = [sum(1 << c for c in children) for children in outgoing]
    weights = [n['output_memory'] for n in nodes]
    details = []
    for v, node in enumerate(nodes):
        held = [p for p in bits(ancestor[v]) if child_bits[p] & descendant[v]]
        direct = node['workspace_memory'] + weights[v] + sum(weights[p] for p in incoming[v])
        forced = node['workspace_memory'] + weights[v] + sum(weights[p] for p in held)
        assert forced >= direct
        details.append((forced, direct, v, len(held), len(incoming[v])))
    sinks = [i for i, children in enumerate(outgoing) if not children]
    terminal = sum(weights[i] for i in sinks)
    last_sink = min((nodes[i]['workspace_memory'] + sum(weights[p] for p in incoming[i]) for i in sinks), default=0)
    old = max([terminal + last_sink] + [r[1] for r in details])
    new = max([old] + [r[0] for r in details])
    strongest = max(details, default=(0, 0, -1, 0, 0))
    return old, new, strongest


def independent_serial_optimum(nodes):
    """Full subset DP; contains no ancestor/descendant or new-bound calculation."""
    incoming, outgoing, _ = graph(nodes)
    n = len(nodes)
    parents = [sum(1 << p for p in v) for v in incoming]
    children = [sum(1 << c for c in v) for v in outgoing]
    full = (1 << n) - 1
    dp = [10**100] * (full + 1)
    dp[0] = 0
    for mask in range(full + 1):
        if dp[mask] == 10**100:
            continue
        live = sum(node['output_memory'] for i, node in enumerate(nodes)
                   if mask & (1 << i) and (not children[i] or children[i] & ~mask))
        for i, node in enumerate(nodes):
            if mask & (1 << i) or parents[i] & ~mask:
                continue
            next_mask = mask | (1 << i)
            candidate = max(dp[mask], live + node['workspace_memory'] + node['output_memory'])
            dp[next_mask] = min(dp[next_mask], candidate)
    return dp[full]


def main():
    workspace = Path(__file__).resolve().parents[1]
    project = workspace / 'projects/27-aicore-streams'
    output = workspace / 'outputs/stage2-memory-structure'
    if output.exists():
        raise SystemExit('Refusing to overwrite previous audit')
    output.mkdir()
    started = time.perf_counter()
    rng = random.Random(270110)
    for trial in range(400):
        n = 4 + trial % 7
        nodes = [dict(id=17 + i * 137,
                      inputs=[17 + p * 137 for p in range(i) if rng.randrange(100) < trial % 81],
                      workspace_memory=rng.randrange(101), output_memory=rng.randrange(101)) for i in range(n)]
        rng.shuffle(nodes)
        old, new, _ = bound(nodes)
        optimum = independent_serial_optimum(nodes)
        assert old <= new <= optimum
    example = [dict(id=i, inputs=([i-1] if i else []) + ([0] if i == 3 else []),
                    workspace_memory=100 if i == 2 else 0, output_memory=[100,1,1,0][i]) for i in range(4)]
    old, new, _ = bound(example)
    assert (old, new, independent_serial_optimum(example)) == (102, 202, 202)
    suite = project / 'data/hard-corpus-resumed.json'
    results = project / 'reports/paired-hard-batch36-1-after.json'
    # Only outcome labels are read; neither file's witness/plan is inspected.
    outcomes = {r['name']: r['pass'] for r in json.loads(results.read_text())['cases']}
    cases = json.loads(suite.read_text())['cases']
    rows = []
    for case in cases:
        nodes = case['nodes']
        old, new, best = bound(nodes)
        capacity = case['hardware']['memory_limit']
        incoming, outgoing, _ = graph(nodes)
        rows.append(dict(name=case['name'], n=len(nodes), passed=outcomes[case['name']],
                         direct_and_terminal_bound=old, forced_ancestor_bound=new,
                         capacity=capacity, ratio=new/capacity if capacity else None,
                         improved=new>old, exceeds_capacity=new>capacity,
                         strongest_operator_id=nodes[best[2]]['id'],
                         forced_producers=best[3], direct_producers=best[4],
                         zero_output_nodes=sum(n['output_memory']==0 for n in nodes),
                         zero_workspace_nodes=sum(n['workspace_memory']==0 for n in nodes),
                         edges=sum(map(len,incoming)),
                         sources=sum(not p for p in incoming),sinks=sum(not c for c in outgoing)))
    report = dict(passed=True, scope='Input-only static necessary lower bound, including parallel schedules; not a solver, sufficient test, or infeasibility certificate below capacity',
                  proof='For p< v and direct p->c with v<=c: p has completed before v starts, c cannot complete before v ends. Its distinct output is necessarily live alongside W(v)+O(v). Sinks keep the existing terminal bound.',
                  source_reference='https://arxiv.org/html/2312.13526v1 (computation graph with scratch); this forced-overlap bound is our derived extension, not claimed as the paper algorithm',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  suite_sha256=hashlib.sha256(suite.read_bytes()).hexdigest(),
                  outcome_report_sha256=hashlib.sha256(results.read_bytes()).hexdigest(),
                  independent_subset_tests=400,example=dict(direct_bound=102,new_bound=202,serial_optimum=202),
                  total=len(rows),improved=sum(r['improved'] for r in rows),
                  failed_count=sum(not r['passed'] for r in rows),
                  improved_failed=sum(r['improved'] and not r['passed'] for r in rows),
                  excluded=sum(r['exceeds_capacity'] for r in rows),
                  failed_n_gt_768=sum(not r['passed'] and r['n']>768 for r in rows),
                  wall_seconds=time.perf_counter()-started,cases=rows)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
