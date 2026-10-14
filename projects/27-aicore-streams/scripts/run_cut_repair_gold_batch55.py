"""Authorized ONLY compiler160 gold gate; no same12 solver execution yet."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
P=Path('research/batch55');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
freeze=json.loads((P/'pre-execution-freeze.json').read_text());plan=json.loads((P/'compiler-resource-plan.json').read_text())
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
temp=(P/'compiler-temp').resolve();temp.mkdir(exist_ok=True);env=os.environ.copy()
for k,v in plan['process_environment_overrides'].items():env[k]=v
states=[];began=time.perf_counter()
def run(label,command):
    space=shutil.disk_usage(Path.cwd().anchor);assert space.free>=plan['minimum_F_free_bytes']
    before=time.perf_counter();r=subprocess.run(command,capture_output=True,text=True,env=env)
    logbase=f'reports/cut-repair-{label}-batch55'
    Path(logbase+'.stdout.txt').write_text(r.stdout,encoding='utf-8');Path(logbase+'.stderr.txt').write_text(r.stderr,encoding='utf-8')
    states.append(dict(label=label,command=command,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-before,F_free_before_bytes=space.free,stdout_path=logbase+'.stdout.txt',stderr_path=logbase+'.stderr.txt'))
    (P/'gold-execution-status.json').write_text(json.dumps(dict(owner_pid=os.getpid(),statuses=states,preexecution_freeze_sha256=sha(P/'pre-execution-freeze.json'),process_environment_overrides=plan['process_environment_overrides'],shared_functional_wall_seconds=time.perf_counter()-began,same12_solver_executed=False),indent=2)+'\n',encoding='utf-8')
    print(label,'actual exit',r.returncode,flush=True)
    if r.returncode:raise SystemExit(r.returncode)
print('R55 gold owner PID',os.getpid(),flush=True)
run('gcc-version',['E:/mingw64/bin/g++.exe','--version']);run('clang-version',['C:/Program Files/LLVM/bin/clang++.exe','--version'])
for label,cmd in zip(('build-gcc-gold','build-gcc-selected12','build-gcc-standalone','build-ubsan-gold'),plan['commands']):run(label,cmd)
run('gcc',[str(P/'gold-gcc.exe'),str(P/'gold-driver-input.json'),'reports/cut-repair-gcc-batch55.json'])
run('ubsan',[str(P/'gold-ubsan.exe'),str(P/'gold-driver-input.json'),'reports/cut-repair-ubsan-batch55.json'])
run('verify',['C:/Users/admin/miniconda3/python.exe','scripts/verify_cut_repair_gold_batch55.py'])
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
paths=[str(P/f) for f in ('gold-gcc.exe','gold-ubsan.exe','selected12-gcc.exe','standalone.o','gold-execution-status.json')]+['reports/cut-repair-gcc-batch55.json','reports/cut-repair-ubsan-batch55.json','reports/cut-repair-gold-summary-batch55.json','scripts/run_cut_repair_gold_batch55.py','scripts/verify_cut_repair_gold_batch55.py']
paths += [s[k] for s in states for k in ('stdout_path','stderr_path')]
doc=dict(status='ACTUAL_TERMINAL_EXIT0_COMPILER160_GOLD_GATE',owner_pid=os.getpid(),statuses=states,preexecution_freeze_sha256=sha(P/'pre-execution-freeze.json'),candidate_source_sha256=sha(P/'solution.cpp'),files=[dict(path=f,sha256=sha(f)) for f in paths],same12_driver_compiled=True,same12_solver_executed=False,default_changed=False,old_open_tex_changed=False,scope='160normal+16direct+160fixed percompiler only; no63/67/full/perf/default',process_environment_overrides=plan['process_environment_overrides'])
(P/'gold-completion.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print('R55 gold actual terminal; same12 not executed',flush=True)
