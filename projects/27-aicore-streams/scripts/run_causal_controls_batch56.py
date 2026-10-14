"""Prepared only: execute once AFTER root authorization; all compiler output owned G."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
freeze=json.loads((P/'compiler-controls-plan-freeze.json').read_text());plan=json.loads((P/'compiler-resource-plan.json').read_text())
assert Path.cwd().resolve()==Path(plan['project_root']).resolve()
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
owned=Path(plan['owned_root']);assert owned.is_absolute() and owned.drive.upper()=='G:'
assert not owned.exists(),'Do not reuse or overwrite an old/unrelated workspace'
assert not (P/'controls-execution-status.json').exists(),'No automatic restart'
assert shutil.disk_usage('G:/').free>=plan['minimum_G_free_bytes']
owned.mkdir(parents=True,exist_ok=False)
(owned/'owner.json').write_text(json.dumps(dict(owner='/root/project27/R56',project_root=plan['project_root'],source_sha256=sha(P/'solution.cpp'),plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json')),indent=2)+'\n')
for name in ('compiler-temp','bin','outputs','logs'):(owned/name).mkdir()
env=os.environ.copy();env.update(plan['process_environment_overrides']);states=[];began=time.perf_counter()
status_path=P/'controls-execution-status.json'
def save(status):
    status_path.write_text(json.dumps(dict(status=status,owner_pid=os.getpid(),statuses=states,plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json'),owned_root=str(owned),process_environment_overrides=plan['process_environment_overrides'],shared_functional_wall_seconds=time.perf_counter()-began,same12_solver_executed=False,default_changed=False),indent=2)+'\n',encoding='utf-8')
save('STARTED_ACTUAL_OWNER_NO_COMPILER_LAUNCHED_YET');print('R56 controls owner PID',os.getpid(),flush=True)
for command in plan['commands']:
    label=command['label'];space=shutil.disk_usage('G:/')
    assert space.free>=plan['minimum_G_free_bytes'],('G free preflight',label,space.free)
    stdout=owned/'logs'/f'{label}.stdout.txt';stderr=owned/'logs'/f'{label}.stderr.txt'
    assert not stdout.exists() and not stderr.exists()
    before=time.perf_counter()
    with stdout.open('xb') as out,stderr.open('xb') as err:
        process=subprocess.Popen(command['argv'],stdout=out,stderr=err,env=env)
        state=dict(label=label,command=command['argv'],actual_child_pid=process.pid,actual_exit_code=None,G_free_before_bytes=space.free,stdout_path=str(stdout),stderr_path=str(stderr))
        states.append(state);save('ACTUAL_CHILD_RUNNING');print(label,'actual child PID',process.pid,flush=True)
        code=process.wait()
    state.update(actual_exit_code=code,shared_functional_wall_seconds=time.perf_counter()-before,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr));save('ACTUAL_CHILD_TERMINAL')
    print(label,'actual exit',code,flush=True)
    if code:
        save('FIRST_ACTUAL_FAILURE_PRESERVED_NO_RETRY');raise SystemExit(code)
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
save('ALL_COMMANDS_ACTUAL_TERMINAL_EXIT0')
files=[f for folder in ('bin','outputs','logs') for f in (owned/folder).iterdir() if f.is_file()]+[owned/'owner.json',status_path]
doc=dict(status='ACTUAL_TERMINAL_EXIT0_GCC_CLANG_CONTROLS_GATE',owner_pid=os.getpid(),statuses=states,plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json'),candidate_source_sha256=sha(P/'solution.cpp'),files=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files],same12_driver_compiled=True,same12_solver_executed=False,scope=plan['scope'],performance_unmeasured=True,default_changed=False,old_open_tex_changed=False)
target=P/'controls-completion-freeze.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print('R56 control gate actual terminal; same12 NOT run',flush=True)
