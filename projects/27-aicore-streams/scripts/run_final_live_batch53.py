"""Authorized 176 controls and original R52 twelve only; no default/full/perf."""
from pathlib import Path
import hashlib,json,os,subprocess,time
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
P=Path('research/batch53');plan=json.loads((P/'execution-plan.json').read_text())
for f in plan['files']:assert sha(f['path'])==f['sha256'],f['path']
temp=(P/'compiler-temp').resolve();temp.mkdir(exist_ok=True);env=os.environ.copy()
for key in ('TEMP','TMP','TMPDIR'):env[key]=str(temp)
statuses=[];started=time.perf_counter()
def run(label,cmd,allowed=(0,)):
    before=time.perf_counter();r=subprocess.run(cmd,capture_output=True,text=True,env=env)
    Path(f'reports/final-live-{label}-batch53.stdout.txt').write_text(r.stdout,encoding='utf-8');Path(f'reports/final-live-{label}-batch53.stderr.txt').write_text(r.stderr,encoding='utf-8')
    statuses.append(dict(label=label,command=cmd,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-before))
    (P/'execution-status.json').write_text(json.dumps(dict(statuses=statuses,execution_plan_sha256=sha(P/'execution-plan.json'),env_process_overrides={k:env[k] for k in ('TEMP','TMP','TMPDIR')},shared_functional_wall_seconds=time.perf_counter()-started),indent=2)+'\n',encoding='utf-8')
    print(label,'actual exit',r.returncode,flush=True);assert r.returncode in allowed,label
for name,source in [('gold','gold-driver.cpp'),('selected12','selected12-driver.cpp')]:
    run('build-gcc-'+name,['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude',str(P/source),'src/simulator.cpp','-o',str(P/(name+'-gcc.exe'))])
run('gcc',[str(P/'gold-gcc.exe'),str(P/'gold-driver-input.json'),'reports/final-live-gcc-batch53.json'])
run('build-ubsan',['cmd.exe','/c',str(P/'build-ubsan.cmd')])
run('ubsan',[str(P/'gold-ubsan.exe'),str(P/'gold-driver-input.json'),'reports/final-live-ubsan-batch53.json'])
run('fixed-ubsan',[str(P/'fixed-ubsan.exe'),'data/final-live-fixed-gold-batch53.json','reports/final-live-fixed-ubsan-batch53.json'])
run('selected12',[str(P/'selected12-gcc.exe'),'research/batch52/observer-selected12-input-only.json','reports/final-live-selected12-batch53.json'])
run('verify',['C:/Users/admin/miniconda3/python.exe','scripts/verify_final_live_batch53.py'])
for f in plan['files']:assert sha(f['path'])==f['sha256'],f['path']
out=dict(status='ACTUAL_TERMINAL_EXIT0',statuses=statuses,execution_plan_sha256=sha(P/'execution-plan.json'),files=[dict(path=f,sha256=sha(f)) for f in ['reports/final-live-generation-batch53.json','reports/final-live-summary-batch53.json','reports/final-live-gcc-batch53.json','reports/final-live-ubsan-batch53.json','reports/final-live-fixed-ubsan-batch53.json','reports/final-live-selected12-batch53.json','research/batch53/gold-gcc.exe','research/batch53/gold-ubsan.exe','research/batch53/fixed-ubsan.exe','research/batch53/selected12-gcc.exe']],default_changed=False,old_open_tex_changed=False,scope=plan['scope'])
(P/'completion.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print('R53 authorized small gate terminal; default51 unchanged',flush=True)
