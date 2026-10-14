"""Serial actual-plan audit using prefix/future live sets and Python bigint."""
import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=json.loads(Path('data/unresolved-r44-input-only-batch45.json').read_text())['cases'];results=json.loads(Path('reports/projection-unresolved-diagnostic-batch48.json').read_text())['cases'];assert len(inputs)==len(results)
records=[]
for c,r in zip(inputs,results):
    assert c['name']==r['name']
    if not r['pass']:continue
    assert len(r['plan']['streams'])==1;tasks=r['plan']['streams'][0]['tasks'];nodes={v['id']:v for v in c['nodes']};children={i:set() for i in nodes}
    for v in nodes.values():
        for p in v['inputs']:children[p].add(v['id'])
    assert len(tasks)==len(nodes) and {t['op_id'] for t in tasks}==set(nodes)
    done=set();peak=elapsed=0;allocations=[]
    for task in tasks:
        assert not task['wait_before'] and task['record_after']==-1
        i=task['op_id'];v=nodes[i];assert i not in done and set(v['inputs'])<=done
        pool=c['hardware']['aic_core_num' if v['core_type']=='AIC' else 'aiv_core_num'];assert 1<=v['core_num']<=pool
        live=sum(nodes[p]['output_memory'] for p in done if not children[p] or children[p]-done)
        allocated=live+v['workspace_memory']+v['output_memory'];peak=max(peak,allocated);elapsed+=v['exec_time'];done.add(i);allocations.append(allocated)
    assert elapsed==r['T']<=c['deadline_us'] and peak==r['peak_memory']<=c['hardware']['memory_limit']
    records.append(dict(name=c['name'],n=len(nodes),T=elapsed,peak_memory=peak,capacity=c['hardware']['memory_limit'],begin_allocations=allocations,original_ids_once=True,exact_prefix_future_live=True,integer_bits='Python arbitrary precision'))
assert len(records)==3
report=dict(status='PASS',cases=records,source_sha=sha('research/batch48/solution.cpp'),input_sha=sha('data/unresolved-r44-input-only-batch45.json'),diagnostic_sha=sha('reports/projection-unresolved-diagnostic-batch48.json'),method='Original direct users, per-BEGIN W+O, every END last-direct successor release, sink hold, sparse IDs/DAG and both core pools; actual serial no-event plans only',scope='Only3 actually returned serial plans, not oracle/witness, not general parallel/event proof')
Path('reports/projection-actual-plan-bigint-batch48.json').write_text(json.dumps(report,indent=2));print([(r['name'],r['n'],r['T'],r['peak_memory']) for r in records],flush=True)
