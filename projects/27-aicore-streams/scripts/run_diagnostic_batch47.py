import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
commands=[('profile',['research/batch47/test_projection.exe','data/projection-gold-batch45.json']),('bigint',['C:/Users/admin/miniconda3/python.exe','scripts/review_projection_search_batch47.py']),('hard',['research/batch47/diagnostic.exe','data/unresolved-r44-input-only-batch45.json','reports/projection-unresolved-diagnostic-batch47.json']),('heldout',['research/batch47/diagnostic.exe','data/projection-heldout-unresolved-input-only-batch45.json','reports/projection-heldout-unresolved-diagnostic-batch47.json'])]
statuses=[]
for label,cmd in commands:
    begin=time.perf_counter();run=subprocess.run(cmd,capture_output=True,text=True)
    Path(f'reports/projection-{label}-status-batch47.txt').write_text(run.stdout+run.stderr,encoding='utf-8');print(label,run.returncode,run.stdout.strip())
    statuses.append(dict(label=label,command=cmd,actual_exit_code=run.returncode,shared_functional_wall_seconds=time.perf_counter()-begin))
    assert run.returncode==0
paths=['research/batch47/solution.cpp','research/batch47/projection.cpp.inc','research/batch47/diagnostic.cpp','research/batch47/test_projection.cpp','research/batch47/diagnostic.exe','research/batch47/test_projection.exe','include/problem.h','include/local_json.h','src/benchmark.cpp','src/simulator.cpp','include/simulator.h','include/solver_metrics.h','data/projection-gold-batch45.json','data/unresolved-r44-input-only-batch45.json','data/projection-heldout-unresolved-input-only-batch45.json','reports/projection-search-bigint-batch47.json','reports/projection-unresolved-diagnostic-batch47.json','reports/projection-heldout-unresolved-diagnostic-batch47.json']
summary={}
for label in ['unresolved','heldout-unresolved']:
    before=json.loads(Path(f'reports/projection-{label}-diagnostic-batch45.json').read_text());after=json.loads(Path(f'reports/projection-{label}-diagnostic-batch47.json').read_text());a={x['name']:x for x in before['cases']};b={x['name']:x for x in after['cases']};assert a.keys()==b.keys()
    summary[label]=dict(before=before['summary'],after=after['summary'],newly_recovered=[k for k in a if not a[k]['pass'] and b[k]['pass']],lost=[k for k in a if a[k]['pass'] and not b[k]['pass']],after_exhausted=sum(x['exhausted'] for x in b.values()))
report=dict(status='isolated functional only',source_sha=sha('research/batch47/solution.cpp'),seed_change='R45 threshold/profile/search cap retained; 12 dependency-ready affinity constructors instead of unconstrained affinity then normalize',statuses=statuses,sha256={p:sha(p) for p in paths},summary=summary,timing='Shared functional costs; no timing pairs or performance inference',default44_source_sha=sha('solution/solution.cpp'))
Path('research/batch47/functional-checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
