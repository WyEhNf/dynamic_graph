"""Compare strict structure helper against independently enumerated profiles."""
import copy,hashlib,json,subprocess
from pathlib import Path

base=Path('research/batch38')
probe=Path('src/frontier_probe.cpp').read_text(encoding='utf-8').replace('#include "../solution/solution.cpp"','#include "solution.cpp"')
probe=probe.replace('auto r=aicore_detail::serial_frontier_search(h,g,limit,true,true);','aicore_detail::SerialFrontierResult r;r.order=aicore_detail::strict_fork_join_order(g);(void)limit;')
(base/'fork_join_probe.cpp').write_text(probe,encoding='utf-8')
d=json.loads(Path('data/nested-forkjoin-new-batch38.json').read_text());orig=d['cases'][0]
negative=copy.deepcopy(orig);negative['name']='negative_external_branch_edge'
v={x['id']:x for x in negative['nodes']};root=next(x for x in v.values() if not x['inputs']);leaves=[x for x in v.values() if len(x['inputs'])==1]
leaves[1]['inputs'].append(leaves[0]['id']);negative.pop('witness_plan')
negative2=copy.deepcopy(orig);negative2['name']='negative_missing_fork_retention_edge'
join=next(x for x in negative2['nodes'] if len(x['inputs'])==3);join['inputs'].remove(root['id']);negative2.pop('witness_plan')
negative3=copy.deepcopy(orig);negative3['name']='negative_extra_source'
negative3['nodes'].append(dict(id=1999999,core_type='AIC',core_num=1,exec_time=1,workspace_memory=1,output_memory=1,inputs=[]));negative3.pop('witness_plan')
d['cases'] += [negative,negative2,negative3]
Path('data/nested-forkjoin-probe-batch38.json').write_text(json.dumps(d),encoding='utf-8')
subprocess.run([r'E:\mingw64\bin\g++.exe','-std=c++17','-O2','-Iinclude',str(base/'fork_join_probe.cpp'),'src/simulator.cpp','-o',str(base/'fork_join_probe.exe')],check=True)
subprocess.run([str(base/'fork_join_probe.exe'),'data/nested-forkjoin-probe-batch38.json','reports/nested-forkjoin-probe-batch38.json','0'],check=True)
p=json.loads(Path('reports/nested-forkjoin-probe-batch38.json').read_text())['cases'];ref={x['name']:x for x in json.loads(Path('reports/nested-forkjoin-new-batch38-oracle.json').read_text())['records']}
for x in p:
    if x['name'].startswith('negative_'):assert not x['found'],x;continue
    assert x['valid'] and x['deadline'],x
    assert x['peak']<=ref[x['name']]['restricted_peak'],(x,ref[x['name']])
    if ref[x['name']]['k']<=3:
        assert x['peak']==ref[x['name']]['restricted_peak'],(x,ref[x['name']])
        assert x['peak']>=ref[x['name']]['serial_optimum'],(x,ref[x['name']])
result=dict(passed=True,positive=36,boundary_negative=3,small_exhaustive_restricted_peak_equal=12,unrestricted_small_serial_optimum=12,
    source_sha256=hashlib.sha256((base/'solution.cpp').read_bytes()).hexdigest(),probe_sha256=hashlib.sha256((base/'fork_join_probe.cpp').read_bytes()).hexdigest(),
    note='Contiguous-block profile optimality only; no arbitrary-interleaving/dominance claim. Actual original-edge Event simulator establishes returned peak.')
Path('reports/nested-forkjoin-check-batch38.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
