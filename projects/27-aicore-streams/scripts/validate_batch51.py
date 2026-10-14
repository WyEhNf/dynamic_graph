"""Full functional only after true isolated restoration; no cost comparison."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
started=time.perf_counter();statuses=[]
for label,data in [('hard','data/hard-corpus-resumed.json'),('heldout','data/projection-retention-heldout-batch45.json')]:
    output=f'reports/{label}-functional-batch51.json';begin=time.perf_counter();r=subprocess.run(['research/batch51/aicore_bench.exe','--input',data,'--output',output,'--csv',output.replace('.json','.csv')],capture_output=True,text=True);Path(f'reports/{label}-functional-status-batch51.txt').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode in (0,1)
    statuses.append(dict(label=label,input_sha=sha(data),actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-begin));print(label,r.returncode,flush=True)
comparisons={}
for label,before in [('hard','reports/hard-functional-batch48.json'),('heldout','reports/heldout-functional-batch48.json')]:
    after=f'reports/{label}-functional-batch51.json';a=json.loads(Path(before).read_text())['cases'];b=json.loads(Path(after).read_text())['cases'];assert len(a)==len(b) and all(x['name']==y['name'] for x,y in zip(a,b))
    lost=[x['name'] for x,y in zip(a,b) if x['pass'] and not y['pass']];common=[(x,y) for x,y in zip(a,b) if x['pass'] and y['pass']];assert not lost and all(x['models_equal'] for x in b)
    changes=[dict(name=x['name'],before_T=x['T'],after_T=y['T'],before_peak=x['peak_memory'],after_peak=y['peak_memory']) for x,y in common if (x['T'],x['peak_memory'])!=(y['T'],y['peak_memory'])]
    comparisons[label]=dict(records=len(a),before_legal=sum(x['pass'] for x in a),after_legal=sum(x['pass'] for x in b),recovered=[x['name'] for x,y in zip(a,b) if not x['pass'] and y['pass']],lost=lost,common_T_peak_changes=changes,common_all_T_peak_identical=not changes,before_sha=sha(before),after_sha=sha(after),all_failure_wall_us=sum(x['solve_us'] for x in b if not x['pass']),all_failure_thread_cpu_us=sum(x['solve_thread_cpu_us'] for x in b if not x['pass']))
manifest=dict(status='isolated full functional;not default',source_sha=sha('research/batch51/solution.cpp'),benchmark_sha=sha('research/batch51/aicore_bench.exe'),default_source_sha=sha('solution/solution.cpp'),diagnostic_freeze_sha=sha('research/batch51/functional-checkpoint.json'),independent_simulator_sha=sha('src/simulator.cpp'),shared_functional_seconds=time.perf_counter()-started,jobs=statuses,comparisons=comparisons,timing='Shared functional O2, no paired performance/speed claim')
Path('reports/functional-summary-batch51.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(comparisons,indent=2),flush=True)
