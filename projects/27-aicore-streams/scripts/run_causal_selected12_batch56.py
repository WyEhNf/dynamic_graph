"""Prepared single original12 run; requires separate root authorization."""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,shutil,subprocess,time
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
plan=json.loads((P/'selected12-resource-plan.json').read_text());freeze=json.loads((P/'selected12-plan-freeze.json').read_text())
assert Path.cwd().resolve()==Path(plan['project_root']).resolve()
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
status_path=P/'selected12-execution-status.json';owned=Path(plan['owned_root'])
assert owned.is_absolute() and owned.drive.upper()=='G:'
assert not owned.exists() and not status_path.exists(),'No automatic restart or overwrite'
began=time.perf_counter();states=[];preflights=[];current=None
def save(status):
    status_path.write_text(json.dumps(dict(status=status,owner_pid=os.getpid(),current_child_pid=current,statuses=states,preflights=preflights,plan_freeze_sha256=sha(P/'selected12-plan-freeze.json'),owned_root=str(owned),shared_functional_wall_seconds=time.perf_counter()-began,process_environment_overrides=plan['process_environment_overrides'],default_changed=False),indent=2)+'\n',encoding='utf-8')
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_=[('dwLength',ctypes.c_uint32),('dwMemoryLoad',ctypes.c_uint32),('ullTotalPhys',ctypes.c_uint64),('ullAvailPhys',ctypes.c_uint64),('ullTotalPageFile',ctypes.c_uint64),('ullAvailPageFile',ctypes.c_uint64),('ullTotalVirtual',ctypes.c_uint64),('ullAvailVirtual',ctypes.c_uint64),('ullAvailExtendedVirtual',ctypes.c_uint64)]
def preflight(label):
    row=dict(label=label,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_child_started=False);error=None
    try:
        api=ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx;api.argtypes=[ctypes.POINTER(MEMORYSTATUSEX)];api.restype=ctypes.c_int
        memory=MEMORYSTATUSEX();memory.dwLength=ctypes.sizeof(memory);returned=api(ctypes.byref(memory))
        row['GlobalMemoryStatusEx']=dict(actual_return=int(returned),structure_bytes=memory.dwLength,last_error=ctypes.get_last_error() if not returned else None,fields={name:int(getattr(memory,name)) for name,_ in MEMORYSTATUSEX._fields_})
        row['G_disk_usage']=shutil.disk_usage('G:/')._asdict();row['F_disk_usage']=shutil.disk_usage('F:/')._asdict()
        row['thresholds']=dict(available_physical_RAM_bytes=plan['minimum_available_RAM_bytes'],G_free_bytes=plan['minimum_G_free_bytes'],F_free_small_state_bytes=plan['minimum_F_free_small_state_bytes'])
        row['checks']=dict(memory_API_succeeded=bool(returned),available_RAM_at_least_1GiB=bool(returned) and memory.ullAvailPhys>=plan['minimum_available_RAM_bytes'],G_free_at_least_1GiB=row['G_disk_usage']['free']>=plan['minimum_G_free_bytes'],F_state_free_at_least_64MiB=row['F_disk_usage']['free']>=plan['minimum_F_free_small_state_bytes'])
        if not all(row['checks'].values()):error='Resource threshold/API failure'
    except Exception as e:error=repr(e);row['resource_API_exception']=error
    row.update(passed=error is None,failure=error);preflights.append(row)
    raw=P/f'selected12-preflight-{len(preflights):02d}.json';assert not raw.exists();raw.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    row.update(raw_path=str(raw),raw_sha256=sha(raw));save('PREFLIGHT_PASSED_NO_CHILD' if error is None else 'FIRST_PREFLIGHT_FAILURE_NO_CHILD_NO_RETRY')
    print(label,'preflight',json.dumps(row),flush=True)
    if error:raise SystemExit(1)
save('OWNER_STARTED_NO_CHILD');print('R56 original12 owner PID',os.getpid(),flush=True);preflight('initial-owned-directory')
owned.mkdir(parents=True,exist_ok=False)
(owned/'owner.json').write_text(json.dumps(dict(owner='/root/project27/R56-selected12',project_root=plan['project_root'],plan_freeze_sha256=sha(P/'selected12-plan-freeze.json'),exe_path=plan['exe_path'],exe_sha256=sha(plan['exe_path'])),indent=2)+'\n')
for folder in ('process-temp','outputs','logs'):(owned/folder).mkdir()
env=os.environ.copy();env.update(plan['process_environment_overrides'])
for command in plan['commands']:
    label=command['label'];preflight(label);stdout=owned/'logs'/f'{label}.stdout.txt';stderr=owned/'logs'/f'{label}.stderr.txt'
    assert not stdout.exists() and not stderr.exists();start=time.perf_counter()
    with stdout.open('xb') as out,stderr.open('xb') as err:
        process=subprocess.Popen(command['argv'],stdout=out,stderr=err,env=env);current=process.pid
        state=dict(label=label,command=command['argv'],actual_child_pid=process.pid,actual_exit_code=None,preflight_raw_path=preflights[-1]['raw_path'],stdout_path=str(stdout),stderr_path=str(stderr));states.append(state);save('ACTUAL_CHILD_RUNNING');print(label,'actual child PID',current,flush=True);code=process.wait()
    current=None;state.update(actual_exit_code=code,shared_functional_wall_seconds=time.perf_counter()-start,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr));save('ACTUAL_CHILD_TERMINAL');print(label,'actual exit',code,flush=True)
    if code:save('FIRST_ACTUAL_FAILURE_PRESERVED_NO_RETRY');raise SystemExit(code)
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
save('ALL_CHILDREN_ACTUAL_TERMINAL_EXIT0')
files=[owned/'owner.json',status_path]+[f for folder in ('outputs','logs') for f in (owned/folder).iterdir() if f.is_file()]+[Path(r['raw_path']) for r in preflights]
doc=dict(status='ACTUAL_TERMINAL_EXIT0_ORIGINAL12_NO_PROMOTION',owner_pid=os.getpid(),statuses=states,preflights=preflights,exe_sha256=sha(plan['exe_path']),source_sha256=sha(P/'solution.cpp'),input_sha256=sha(plan['input_path']),plan_freeze_sha256=sha(P/'selected12-plan-freeze.json'),files=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files],performance_unmeasured=True,default_changed=False,scope=plan['scope'])
target=P/'selected12-completion-freeze.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print('R56 original12 actual terminal no63/full/perf/default',flush=True)
