"""Input-only structural audit; contractions never modify submitted graphs."""
import hashlib
import json
from collections import deque
from pathlib import Path
from audit_memory_overlap_stage2 import graph


def ttsp(incoming, outgoing):
    """Series/parallel reduction after zero-size virtual source/terminal addition.

    Internal vertices with one incoming and one outgoing edge are eliminated.
    Sets merge parallel structural edges. This is recognition only: removing
    data-dependency edges in the actual lifetime model is not authorized.
    """
    n = len(incoming)
    source, terminal = n, n+1
    before = [set(v) for v in incoming] + [set(), set()]
    after = [set(v) for v in outgoing] + [set(), set()]
    for i in range(n):
        if not incoming[i]:
            before[i].add(source)
            after[source].add(i)
        if not outgoing[i]:
            after[i].add(terminal)
            before[terminal].add(i)
    active = set(range(n+2))
    queue = deque(range(n))
    eliminated = []
    while queue:
        i = queue.popleft()
        if i not in active or len(before[i]) != 1 or len(after[i]) != 1:
            continue
        p = next(iter(before[i]))
        c = next(iter(after[i]))
        assert p != c
        after[p].remove(i)
        before[c].remove(i)
        after[p].add(c)
        before[c].add(p)
        active.remove(i)
        eliminated.append(i)
        for v in (p,c):
            if v < n:
                queue.append(v)
    recognized = active == {source,terminal} and after[source] == {terminal}
    return recognized, len(active), len(eliminated)


def classify(nodes):
    incoming,outgoing,_ = graph(nodes)
    recognized,remaining,eliminated = ttsp(incoming,outgoing)
    # Acyclic directed edges are undirected edges too; union-find detects
    # undirected tree/forest structure without deleting any actual dependency.
    parents = list(range(len(nodes)))
    def find(v):
        while parents[v] != v:
            parents[v] = parents[parents[v]]
            v = parents[v]
        return v
    undirected_forest = True
    for i,pred in enumerate(incoming):
        for p in pred:
            a,b = find(i),find(p)
            if a == b:
                undirected_forest = False
            else:
                parents[a] = b
    return dict(augmented_ttsp=recognized,structural_reduction_remaining=remaining,
                eliminated_structural_nodes=eliminated,undirected_forest=undirected_forest,
                chain_internal_nodes=sum(len(incoming[i])==len(outgoing[i])==1 for i in range(len(nodes))),
                max_outdegree=max(map(len,outgoing),default=0))


def main():
    root = Path(__file__).resolve().parents[1]
    project = root/'projects/27-aicore-streams'
    output = root/'outputs/stage2-memory-structure/sp-classification.json'
    if output.exists():
        raise SystemExit('Refusing to overwrite previous audit')
    def nodes(edges,n):
        return [dict(id=i,inputs=[p for p,c in edges if c==i]) for i in range(n)]
    assert classify(nodes([(0,1),(1,2)],3))['augmented_ttsp']
    assert classify(nodes([(0,1),(0,2),(1,3),(2,3)],4))['augmented_ttsp']
    assert not classify(nodes([(0,1),(0,2),(1,2),(1,3),(2,3)],4))['augmented_ttsp']
    assert classify(nodes([],3))['augmented_ttsp']
    assert classify(nodes([(0,1),(0,2)],3))['undirected_forest']
    suite = project/'data/hard-corpus-resumed.json'
    result = project/'reports/paired-hard-batch36-1-after.json'
    outcomes = {r['name']: r['pass'] for r in json.loads(result.read_text())['cases']}
    rows = [dict(name=case['name'],n=len(case['nodes']),passed=outcomes[case['name']],**classify(case['nodes']))
            for case in json.loads(suite.read_text())['cases']]
    failed = [r for r in rows if not r['passed']]
    report = dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  suite_sha256=hashlib.sha256(suite.read_bytes()).hexdigest(),
                  scope='Structural recognition only. Original edges, producer output sizes/lifetimes and plans are untouched; no witness order read.',
                  interpretation='An augmented TTSP label does not provide a polynomial peak-memory algorithm; weighted one-shot scheduling can remain NP-hard, and bounded-degree algorithms have exponential dependence on degree.',
                  reference='https://arxiv.org/html/2312.13526v1',
                  total=len(rows),failed=len(failed),ttsp_all=sum(r['augmented_ttsp'] for r in rows),
                  ttsp_failed=sum(r['augmented_ttsp'] for r in failed),
                  forest_failed=sum(r['undirected_forest'] for r in failed),
                  failed_degree_range=[min(r['max_outdegree'] for r in failed),max(r['max_outdegree'] for r in failed)],
                  failed_chain_nodes_total=sum(r['chain_internal_nodes'] for r in failed),cases=rows)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False))


if __name__ == '__main__':
    main()
