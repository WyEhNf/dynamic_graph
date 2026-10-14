"""Root checks pure resource-graph automorphisms and actual materialized outputs."""
import copy
import json
import time
from collections import Counter
from pathlib import Path
from review_stage2_cpsat_r118 import check, fingerprint, sha, distance

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/18-isa-scheduler'


def automorphism(data,plan):
    nodes = data['instructions'];n=len(nodes);d=plan['dimension']
    assert plan['kind']=='resource_matrix_adjacent_symmetries' and d>=2
    parents = [[i-distance(t) for t in row.get('inputs',[])] for i,row in enumerate(nodes)]
    reads = [r['reg'] for r in nodes if r['op']=='GET']
    writes = [r['reg'] for r in nodes if r['op']=='SET']
    assert len(reads)==len(set(reads)) and len(writes)==len(set(writes)) and not set(reads)&set(writes)
    axes = [plan['row_groups'],plan['column_groups']]
    flat = [u for groups in axes for group in groups for u in group]
    assert len(flat)==len(set(flat)) and set(flat)=={i for i,r in enumerate(nodes) if r['op']=='GET'}
    for groups in axes:
        assert len(groups)==d and all(len(g)==d for g in groups)
    count = 0
    for axis,name in enumerate(('row_generators','column_generators')):
        assert len(plan[name])==d-1
        for pivot,mapping in enumerate(plan[name]):
            assert sorted(mapping)==list(range(n))
            for u,v in enumerate(mapping):
                assert nodes[u]['op']==nodes[v]['op']
                assert Counter(mapping[x] for x in parents[u])==Counter(parents[v])
            for partition,groups in enumerate(axes):
                for i,group in enumerate(groups):
                    j = pivot+1 if i==pivot else pivot if i==pivot+1 else i
                    if partition!=axis:j=i
                    assert {mapping[u] for u in group}==set(groups[j])
            count+=1
    return count


def main():
    base = PROJECT/'experiments/r120-cpsat-symmetry-holdout'
    report = json.loads((base/'report.json').read_text())
    data = {fingerprint(r['input']):r['input'] for r in map(json.loads,(base/'inputs.jsonl').read_text().splitlines())}
    assert len(data)==24 and len(report['records'])==48 and not report['violations']
    generators=outputs=rejected=0
    evidence = {}
    for key,value in data.items():
        path = base/f'{key[:16]}-symmetry.json'
        plan=json.loads(path.read_text());generators+=automorphism(value,plan)
        bad=copy.deepcopy(plan);bad['row_generators'][0][0]=bad['row_generators'][0][1]
        try:automorphism(value,bad)
        except AssertionError:rejected+=1
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
    for r in report['records']:
        if r['cpsat']['outcome']=='constructive_original_order':
            path=base/f"{r['sha256'][:16]}-{r['variant']}-output.json"
            saved=json.loads(path.read_text());saved['fixed']=False
            copies=check(data[r['sha256']],saved)
            assert copies==r['copies']
            if r['variant']=='symmetry':
                plan=json.loads((base/f"{r['sha256'][:16]}-symmetry.json").read_text())
                position={u:i for i,u in enumerate(saved['original_order'])}
                for axis in ('row_groups','column_groups'):
                    births=[min(position[u] for u in g) for g in plan[axis]]
                    assert births==sorted(births)
            outputs+=1;evidence[path.relative_to(ROOT).as_posix()]=sha(path)
    assert outputs==18 and rejected==24
    matrix_path=PROJECT/'experiments/r121-cpsat-symmetry-matrix/report.json'
    matrix=json.loads(matrix_path.read_text())
    assert len(matrix['records'])==4 and all(r['cpsat']['outcome']=='unknown_budget' for r in matrix['records'])
    for path in (base/'report.json',base/'inputs.jsonl',matrix_path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
    result=dict(reviewed_unix=time.time(),passed=True,raw_graphs=24,automorphism_generators=generators,
                root_replayed_outputs=18,tamper_rejections=24,original_matrix_unknown_attempts=4,evidence=evidence,
                scope='Root raw resourcegraph automorphisms preserve all original data multisets and pure unique/disjoint registers. Actual emission still preserves every original ordered argument/identity/physical window. Both originalmatrix variants returnUNKNOWN, no new large output, COPYoptimum or Levelclaim.')
    (ROOT/'outputs/stage2-root-symmetry-r121.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))


if __name__=='__main__':
    main()
