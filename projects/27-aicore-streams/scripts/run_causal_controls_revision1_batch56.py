"""Source-only prepared supplement; actual execution needs root authorization."""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,shutil,subprocess,time
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
prior=json.loads((P/'compiler-controls-plan-freeze.json').read_text())
freeze=json.loads((P/'compiler-controls-plan-freeze-revision1.json').read_text())
plan=json.loads((P/'compiler-resource-plan-revision1.json').read_text())
assert Path.cwd().resolve()==Path(plan['project_root']).resolve()
for manifest in (prior,freeze):
    for f in manifest['files']:assert sha(f['path'])==f['sha256'],f['path']
owned=Path(plan['owned_root']);assert owned.is_absolute() and owned.drive.upper()=='G:'
status_path=P/'controls-execution-status-revision1.json'
assert not owned.exists(),'Never reuse/overwrite old or unrelated owned directory'
assert not status_path.exists() and not (P/'controls-execution-status.json').exists(),'Never restart an initial preflight or child failure'
states=[];preflights=[];began=time.perf_counter();current_child=None
def save(status):
    doc=dict(status=status,owner_pid=os.getpid(),current_child_pid=current_child,statuses=states,preflights=preflights,plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze-revision1.json'),prior_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json'),owned_root=str(owned),process_environment_overrides=plan['process_environment_overrides'],shared_functional_wall_seconds=time.perf_counter()-began,same12_solver_executed=False,default_changed=False)
    status_path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_=[('dwLength',ctypes.c_uint32),('dwMemoryLoad',ctypes.c_uint32),('ullTotalPhys',ctypes.c_uint64),('ullAvailPhys',ctypes.c_uint64),('ullTotalPageFile',ctypes.c_uint64),('ullAvailPageFile',ctypes.c_uint64),('ullTotalVirtual',ctypes.c_uint64),('ullAvailVirtual',ctypes.c_uint64),('ullAvailExtendedVirtual',ctypes.c_uint64)]
def preflight(label):
    row=dict(label=label,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),owner_pid=os.getpid(),new_child_started=False)
    failure=None
    try:
        api=ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx
        api.argtypes=[ctypes.POINTER(MEMORYSTATUSEX)];api.restype=ctypes.c_int
        memory=MEMORYSTATUSEX();memory.dwLength=ctypes.sizeof(memory)
        returned=api(ctypes.byref(memory))
        row['GlobalMemoryStatusEx']=dict(actual_return=int(returned),structure_bytes=memory.dwLength,last_error=ctypes.get_last_error() if not returned else None,fields={name:int(getattr(memory,name)) for name,_ in MEMORYSTATUSEX._fields_})
        if not returned:failure='GlobalMemoryStatusEx failed; available RAM unknown'
        row['G_disk_usage']=shutil.disk_usage('G:/')._asdict();row['F_disk_usage']=shutil.disk_usage('F:/')._asdict()
        row['thresholds']=dict(available_physical_RAM_bytes=plan['minimum_available_RAM_bytes'],G_free_bytes=plan['minimum_G_free_bytes'],F_free_small_state_bytes=plan['minimum_F_free_small_state_bytes'])
        checks=dict(memory_API_succeeded=bool(returned),available_RAM_at_least_1GiB=bool(returned) and memory.ullAvailPhys>=plan['minimum_available_RAM_bytes'],G_free_at_least_1GiB=row['G_disk_usage']['free']>=plan['minimum_G_free_bytes'],F_state_free_at_least_64MiB=row['F_disk_usage']['free']>=plan['minimum_F_free_small_state_bytes'])
        row['checks']=checks
        if not all(checks.values()):failure=failure or 'Resource threshold failed: '+','.join(k for k,v in checks.items() if not v)
    except Exception as error:
        failure=repr(error);row['resource_API_exception']=failure
    row.update(passed=failure is None,failure=failure);preflights.append(row)
    # Small raw JSON is retained on F even when the 64MiB reserve check fails.
    # Writing status does not authorize launching any child below the reserve.
    raw=P/f'controls-preflight-revision1-{len(preflights):02d}.json';assert not raw.exists()
    raw.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    row['raw_path']=str(raw);row['raw_sha256']=sha(raw)
    save('PREFLIGHT_PASSED_NO_NEW_CHILD' if failure is None else 'FIRST_PREFLIGHT_FAILURE_PRESERVED_NO_CHILD_NO_RETRY')
    print(label,'preflight',json.dumps(row),flush=True)
    if failure:raise SystemExit(1)
save('ACTUAL_OWNER_STARTED_NO_CHILD');print('R56 revision1 owner PID',os.getpid(),flush=True)
preflight('initial-owned-directory')
owned.mkdir(parents=True,exist_ok=False)
(owned/'owner.json').write_text(json.dumps(dict(owner='/root/project27/R56',project_root=plan['project_root'],source_sha256=sha(P/'solution.cpp'),plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze-revision1.json'),prior_plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json')),indent=2)+'\n')
for name in ('compiler-temp','bin','outputs','logs'):(owned/name).mkdir()
env=os.environ.copy();env.update(plan['process_environment_overrides'])
for command in plan['commands']:
    label=command['label'];preflight(label)
    stdout=owned/'logs'/f'{label}.stdout.txt';stderr=owned/'logs'/f'{label}.stderr.txt'
    assert not stdout.exists() and not stderr.exists();before=time.perf_counter()
    with stdout.open('xb') as out,stderr.open('xb') as err:
        process=subprocess.Popen(command['argv'],stdout=out,stderr=err,env=env)
        current_child=process.pid
        state=dict(label=label,command=command['argv'],actual_child_pid=process.pid,actual_exit_code=None,preflight_raw_path=preflights[-1]['raw_path'],preflight_raw_sha256=preflights[-1]['raw_sha256'],stdout_path=str(stdout),stderr_path=str(stderr))
        states.append(state);save('ACTUAL_CHILD_RUNNING');print(label,'actual child PID',process.pid,flush=True);code=process.wait()
    current_child=None
    state.update(actual_exit_code=code,shared_functional_wall_seconds=time.perf_counter()-before,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr));save('ACTUAL_CHILD_TERMINAL')
    print(label,'actual exit',code,flush=True)
    if code:save('FIRST_ACTUAL_CHILD_FAILURE_PRESERVED_NO_RETRY');raise SystemExit(code)
for manifest in (prior,freeze):
    for f in manifest['files']:assert sha(f['path'])==f['sha256'],f['path']
save('ALL_COMMANDS_ACTUAL_TERMINAL_EXIT0')
files=[f for folder in ('bin','outputs','logs') for f in (owned/folder).iterdir() if f.is_file()]+[owned/'owner.json',status_path]+[Path(r['raw_path']) for r in preflights]
doc=dict(status='ACTUAL_TERMINAL_EXIT0_REVISION1_GCC_CLANG_CONTROLS_GATE',owner_pid=os.getpid(),statuses=states,preflights=preflights,plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze-revision1.json'),prior_plan_freeze_sha256=sha(P/'compiler-controls-plan-freeze.json'),candidate_source_sha256=sha(P/'solution.cpp'),files=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files],same12_driver_compiled=True,same12_solver_executed=False,scope=plan['scope'],performance_unmeasured=True,default_changed=False,old_open_tex_changed=False)
target=P/'controls-completion-freeze-revision1.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print('R56 revision1 control gate actual terminal; same12 NOT run',flush=True)
