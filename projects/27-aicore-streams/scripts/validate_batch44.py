"""Functional comparisons only; shared CPU and O2/O3 timings are not paired."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
new=Path('research/batch44/aicore_bench.exe');old=Path('research/batch43/default-aicore_bench.exe');started=time.perf_counter()
jobs=[('hard','data/hard-corpus-resumed.json',new),('forkjoin','data/nested-forkjoin-new-batch38.json',new),('heldout-before','data/shallow-heldout-batch44.json',old),('heldout-after','data/shallow-heldout-batch44.json',new)]
statuses=[]
for label,data,bench in jobs:
    output=f'reports/{label}-functional-batch44.json';begin=time.perf_counter()
    run=subprocess.run([str(bench.resolve()),'--input',data,'--output',output,'--csv',output.replace('.json','.csv')])
    assert run.returncode in [0,1],(label,run.returncode)
    statuses.append(dict(suite=label,exit_code=run.returncode,wall_seconds=time.perf_counter()-begin,input_sha=sha(data),bench_sha=sha(bench)))
comparisons={}
for label,before,after in [('hard','reports/paired-hard-batch43-1-after.json','reports/hard-functional-batch44.json'),('forkjoin','reports/paired-forkjoin-batch43-1-after.json','reports/forkjoin-functional-batch44.json'),('heldout','reports/heldout-before-functional-batch44.json','reports/heldout-after-functional-batch44.json')]:
    a={x['name']:x for x in json.loads(Path(before).read_text())['cases']};b={x['name']:x for x in json.loads(Path(after).read_text())['cases']};assert a.keys()==b.keys()
    recovered=[k for k in a if not a[k]['pass'] and b[k]['pass']];lost=[k for k in a if a[k]['pass'] and not b[k]['pass']]
    common=[k for k in a if a[k]['pass'] and b[k]['pass']];regressed=[k for k in common if (b[k]['T'],b[k]['peak_memory'])>(a[k]['T'],a[k]['peak_memory'])]
    assert not lost and not regressed and all(x['models_equal'] for x in b.values())
    comparisons[label]=dict(records=len(a),before_legal=sum(x['pass'] for x in a.values()),after_legal=sum(x['pass'] for x in b.values()),recovered=recovered,lost=lost,common_quality_regression=regressed,common_all_T_peak_identical=all((a[k]['T'],a[k]['peak_memory'])==(b[k]['T'],b[k]['peak_memory']) for k in common),before_sha=sha(before),after_sha=sha(after),all_failure_wall_us=sum(x['solve_us'] for x in b.values() if not x['pass']),all_failure_thread_cpu_us=sum(x['solve_thread_cpu_us'] for x in b.values() if not x['pass']))
report=dict(status='functional_candidate_only',source_sha=sha('research/batch44/solution.cpp'),benchmark_sha=sha(new),independent_simulator_sha=sha('src/simulator.cpp'),timing='shared CPU functional run; old O3/default and new O2; no speed ratio or default promotion claim',wall_seconds=time.perf_counter()-started,jobs=statuses,comparisons=comparisons)
Path('reports/functional-summary-batch44.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(comparisons,indent=2))
