"""Deferred runner; execute ONLY after parent authorization of frozen67plan."""
from pathlib import Path
import hashlib,json,os,subprocess,time
P=Path('research/batch54');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
plan=json.loads((P/'functional-plan.json').read_text())
for f in plan['files']:assert sha(f['path'])==f['sha256'],f['path']
env=os.environ.copy();temp=Path('research/batch53/compiler-temp').resolve()
for k in ('TEMP','TMP','TMPDIR'):env[k]=str(temp)
t=time.perf_counter();r=subprocess.run(plan['command'],capture_output=True,text=True,env=env)
Path('reports/final-live-remaining67-batch54.stdout.txt').write_text(r.stdout,encoding='utf-8');Path('reports/final-live-remaining67-batch54.stderr.txt').write_text(r.stderr,encoding='utf-8')
status=dict(command=plan['command'],actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-t,plan_sha256=sha(P/'functional-plan.json'),process_environment_overrides={k:env[k] for k in ('TEMP','TMP','TMPDIR')},driver_exit0_is_not67_feasible=True)
(P/'execution-status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8');print('Actual67driver terminal exit',r.returncode,flush=True);assert r.returncode==0
v=subprocess.run(['C:/Users/admin/miniconda3/python.exe','scripts/verify_remaining67_batch54.py'],capture_output=True,text=True,env=env)
Path('reports/final-live-remaining67-verify-batch54.stdout.txt').write_text(v.stdout,encoding='utf-8');Path('reports/final-live-remaining67-verify-batch54.stderr.txt').write_text(v.stderr,encoding='utf-8');status['verifier_actual_exit_code']=v.returncode
(P/'execution-status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8');print('Actual67verify terminal exit',v.returncode,flush=True);assert v.returncode==0
for f in plan['files']:assert sha(f['path'])==f['sha256'],f['path']
paths=['reports/final-live-remaining67-batch54.json','reports/final-live-remaining67-batch54.stdout.txt','reports/final-live-remaining67-batch54.stderr.txt','reports/final-live-remaining67-verify-batch54.stdout.txt','reports/final-live-remaining67-verify-batch54.stderr.txt','reports/final-live-remaining67-summary-batch54.json',str(P/'execution-status.json')]
(P/'completion.json').write_text(json.dumps(dict(status='ACTUAL_SINGLE67_RUN_TERMINAL_EXIT0',files=[dict(path=f,sha256=sha(f)) for f in paths],plan_sha256=sha(P/'functional-plan.json'),default_changed=False,performance_measured=False),indent=2)+'\n',encoding='utf-8');print('R54 actual single67 run complete',flush=True)
