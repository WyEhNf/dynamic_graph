"""Static original-input envelopes only, never a solver/prefix simulation.

Past pass flags select57+6; witness, generation and saved plans are not read.
The upper envelope holds for any completed producer prefix. The lower envelope
refers only to the instant just AFTER producer completion. Neither >128 envelope
by itself classifies the final runtime failure or infeasibility.
"""
import collections
import hashlib
import json
import statistics
import time
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def features(case):
    nodes = case['nodes']
    n = len(nodes)
    index = {node['id']:i for i,node in enumerate(nodes)}
    parents = [[index[p] for p in node['inputs']] for node in nodes]
    children = [[] for _ in nodes]
    for i, ps in enumerate(parents):
        for p in ps:
            children[p].append(i)
    degrees = list(map(len,parents))
    topo = [i for i,count in enumerate(degrees) if count == 0]
    for i in topo:
        for child in children[i]:
            degrees[child] -= 1
            if degrees[child] == 0:
                topo.append(child)
    assert len(topo) == n and len(index) == n
    ancestors, descendants = [0]*n, [0]*n
    for i in topo:
        for p in parents[i]:
            ancestors[i] |= ancestors[p] | (1 << p)
    for i in reversed(topo):
        for child in children[i]:
            descendants[i] |= descendants[child] | (1 << child)
    held = []
    for p, users in enumerate(children):
        if not users or nodes[p]['output_memory'] == 0:
            continue
        closure = 0
        for user in users:
            closure |= ancestors[user] | (1 << user)
        closure &= ~(ancestors[p] | (1 << p))
        # Nodes descending from p cannot be completed before p. Other closure
        # nodes could be earlier, subject to original DAG and resource capacity.
        forced = closure & descendants[p]
        held.append(dict(producer_id=nodes[p]['id'], output=nodes[p]['output_memory'],
                         original_direct_users=len(users),
                         initial_closure_lower=forced.bit_count(),
                         initial_closure_upper=closure.bit_count()))
    positive = sorted(node['workspace_memory'] for node in nodes if node['workspace_memory'] > 0)
    threshold = min(2**63-1,4*positive[(len(positive)-1)//2]) if positive else 0
    targets = [i for i,node in enumerate(nodes) if positive and len(parents[i]) >= 2
               and node['workspace_memory'] >= threshold
               and all(node['workspace_memory'] > nodes[p]['workspace_memory'] for p in parents[i])]
    projection = n <= 4096 and 2 <= len(targets) <= 512
    serial = sum(node['exec_time'] for node in nodes)
    cap = case['hardware']['memory_limit']
    return dict(name=case['name'],input_sha=hashlib.sha256(json.dumps(
        {key:case[key] for key in ('hardware','nodes','deadline_us')},sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        n=n,edges=sum(map(len,parents)),roots=sum(not ps for ps in parents),
        sinks=sum(not cs for cs in children),sink_output=sum(nodes[i]['output_memory'] for i,cs in enumerate(children) if not cs),
        cap=cap,serial_time=serial,deadline=case['deadline_us'],serial_meets_deadline=serial<=case['deadline_us'],
        core_types=dict(collections.Counter(node['core_type'] for node in nodes)),
        workspace_zero=sum(node['workspace_memory']==0 for node in nodes),
        output_zero=sum(node['output_memory']==0 for node in nodes),
        chain_internal=sum(len(parents[i])==1 and len(children[i])==1 for i in range(n)),
        individual_begin_max=max((node['workspace_memory']+node['output_memory'] for node in nodes),default=0),
        original_direct_parent_overlap_max=max((node['workspace_memory']+node['output_memory']+
            sum(nodes[p]['output_memory'] for p in parents[i]) for i,node in enumerate(nodes)),default=0),
        projection=dict(applicable=projection,targets=len(targets),threshold=threshold,
                        reason=None if projection else ('n>4096' if n>4096 else ('targets>512' if len(targets)>512 else 'targets<2'))),
        release_cut_static=dict(graph_admitted=n<=4096,eligible_producers=len(held),
            initial_upper_over128=sum(row['initial_closure_upper']>128 for row in held),
            initial_lower_over128=sum(row['initial_closure_lower']>128 for row in held),
            initial_upper_all_fit=bool(held) and all(row['initial_closure_upper']<=128 for row in held),
            initial_lower_all_exceed=bool(held) and all(row['initial_closure_lower']>128 for row in held),
            max_direct_users=max((row['original_direct_users'] for row in held),default=0),
            upper_median=statistics.median(row['initial_closure_upper'] for row in held) if held else None,
            producers=held),
        runtime_failure='unmeasured:cannot infer greedy/remaining prefix/cap/budget outcome from static envelopes')


def main():
    start = time.perf_counter()
    p = Path('research/batch52')
    p.mkdir(exist_ok=True)
    records, selected = [], []
    sources = [('hard','data/hard-corpus-resumed.json','reports/hard-functional-batch51.json'),
               ('heldout','data/projection-retention-heldout-batch45.json','reports/heldout-functional-batch51.json')]
    for family,input_path,result_path in sources:
        inputs=json.loads(Path(input_path).read_text())['cases']
        results=json.loads(Path(result_path).read_text())['cases']
        assert len(inputs)==len(results)
        for case,result in zip(inputs,results):
            assert case['name']==result['name']
            if result['pass']:
                continue
            # Read ONLY these original problem fields. No witness/gen/plan.
            stripped={key:case[key] for key in ('name','hardware','nodes','deadline_us','expected_feasible')}
            assert stripped['expected_feasible'] is True
            selected.append(stripped)
            record=features(stripped)
            record['audit_partition']=family
            records.append(record)
    assert len(records)==63
    path=p/'remaining63-input-only.json'
    path.write_text(json.dumps(dict(format='aicore-local-v1',cases=selected),indent=2)+'\n',encoding='utf-8')
    summary=dict(total=63,original=sum(row['audit_partition']=='hard' for row in records),
                 heldout=sum(row['audit_partition']=='heldout' for row in records),
                 serial_meets_deadline=sum(row['serial_meets_deadline'] for row in records),
                 cut_graph_admitted=sum(row['release_cut_static']['graph_admitted'] for row in records),
                 projection_applicable=sum(row['projection']['applicable'] for row in records),
                 projection_reasons=dict(collections.Counter(row['projection']['reason'] for row in records if not row['projection']['applicable'])),
                 initial_all_upper_fit128=sum(row['release_cut_static']['initial_upper_all_fit'] for row in records),
                 initial_any_lower_over128=sum(row['release_cut_static']['initial_lower_over128']>0 for row in records),
                 initial_all_lower_over128=sum(row['release_cut_static']['initial_lower_all_exceed'] for row in records),
                 chain_internal_total=sum(row['chain_internal'] for row in records))
    paths=[__file__,'solution/solution.cpp',str(path)] + [v for _,i,r in sources for v in (i,r)]
    report=dict(status='Static original-input analysis only;no solving/prefix replay/performance/default changes',
                summary=summary,cases=records,sha256={name:sha(name) for name in paths},
                limits='Upper closure is a global upper bound at any completed-producer prefix:remaining users are a subset and all producer ancestors are already done. Thus all upper<=128 excludes cap as a cause, but upper>128 does not prove actual rejection. Lower closure applies only immediately after producer completion, before any descendants execute;it may shrink later. No static envelope proves graph infeasibility or greedy/budget attribution.',
                shared_static_analysis_seconds=time.perf_counter()-start)
    Path('reports/remaining-static-classification-batch52.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
