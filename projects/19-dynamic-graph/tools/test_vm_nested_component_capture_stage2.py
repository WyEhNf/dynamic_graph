"""Execute one authorized frozen component compile and small original-VM gate."""
import ctypes,hashlib,json,os,shutil,time
from pathlib import Path
from windows_file_resource_probe_stage2 import HostMemory,monitored_run

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
INITIAL=STAGE/'initial-freeze'
SUPPLEMENT=STAGE/'accounting-supplement'
OUT=STAGE/'component-gate-capture'
CAPTURE=STAGE/'capture-supplement'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def available():
    memory=HostMemory();memory.dwLength=ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):raise ctypes.WinError()
    return memory.ullAvailPhys

def main():
    initial=read(INITIAL/'plan.json');plan=read(SUPPLEMENT/'plan.json')
    assert sha(INITIAL/'plan.json')==plan['initial_plan_sha256']=='cd048c2e441f3d07e8198be5d9a466d753ad0add2b4e5a144565407493b5898a'
    assert sha(SUPPLEMENT/'plan.json')=='039db32ba2c7a2abe7aaf82c9fc006a81a7382d74b0f44eae92401dbb736e690'
    capture=read(CAPTURE/'plan.json');assert capture['accounting_plan_sha256']==sha(SUPPLEMENT/'plan.json')
    for relative,digest in capture['capture_source_sha256'].items():assert sha(CAPTURE/relative)==digest
    for relative in ['tools/test_vm_nested_component_capture_stage2.py','tools/windows_file_resource_probe_stage2.py']:assert sha(P/relative)==capture['capture_source_sha256']['source/'+relative]
    plan['compile_command']=capture['compile_command']
    for relative,record in initial['frozen_files'].items():assert sha(INITIAL/relative)==record['sha256']
    for relative,record in plan['candidate_files'].items():assert sha(SUPPLEMENT/relative)==record['sha256']
    assert sha(plan['compiler']['path'])==plan['compiler']['sha256']
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    assert sha(P/'src/vm_step_bound.cpp')=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    OUT.mkdir(exist_ok=False);temp=STAGE/'compiler-temp';temp.mkdir(exist_ok=True)
    os.environ.update({key:str(temp)for key in ['TEMP','TMP','TMPDIR']});os.environ['PATH']='E:/mingw64/bin'+os.pathsep+os.environ['PATH']
    frozen={}
    for source in [Path(__file__),P/'tools/windows_file_resource_probe_stage2.py']:
        target=OUT/'source'/source.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);frozen[target.relative_to(OUT).as_posix()]=sha(target)
    report={'schema':'isolated-nested-VM-component-execution-v1','passed':False,'status':'starting','initial_plan_sha256':sha(INITIAL/'plan.json'),'accounting_supplement_sha256':sha(SUPPLEMENT/'plan.json'),'capture_plan_sha256':sha(CAPTURE/'plan.json'),'stdio_capture':'direct raw binary files; no PIPE buffer; counter method unchanged','source_snapshot_sha256':frozen,'candidate_source_sha256':{name:record['sha256']for name,record in plan['candidate_files'].items()},'compiler':plan['compiler'],'compile_flags':plan['compile_flags'],'ABI':plan['ABI'],'environment':{key:os.environ[key]for key in ['TEMP','TMP','TMPDIR']},'resource_gates':[],'runs':[],'Runtime_integrated':False,'large_N_execution':False,'performance_started':False,'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256']}
    began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    def gate(phase):
        ram=available();disk=shutil.disk_usage(STAGE).free;good=ram>=plan['minimum_launch_RAM_bytes']and disk>=plan['minimum_F_free_bytes']
        report['resource_gates'].append({'phase':phase,'available_RAM_bytes':ram,'free_F_bytes':disk,'minimum_RAM_bytes':plan['minimum_launch_RAM_bytes'],'minimum_F_bytes':plan['minimum_F_free_bytes'],'passed':good});save()
        if not good:report['status']='resource-gate-blocked';report['actual_exit_code']=75;save();raise SystemExit(75)
    def execute(phase,command):
        gate(phase);report['status']=phase+'-running';save();started=time.perf_counter();process,resources=monitored_run(command,OUT/(phase+'.stdout'),OUT/(phase+'.stderr'),check=False);wall=time.perf_counter()-started
        row={'phase':phase,'command':command,'actual_exit_code':process.returncode,'wall_seconds':wall,'stdout_sha256':sha(OUT/(phase+'.stdout')),'stderr_sha256':sha(OUT/(phase+'.stderr')),**resources};report['runs'].append(row);save()
        print(json.dumps({'phase':phase,'actual_exit_code':process.returncode,'wall_seconds':wall,'PeakWS_bytes':resources['process_peak_working_set_bytes']}),flush=True)
        if process.returncode:report['status']=phase+'-failed';report['actual_exit_code']=process.returncode;save();raise SystemExit(process.returncode)
        return process
    execute('compile',plan['compile_command']);exe=Path(plan['compile_command'][-1]);report['EXE_sha256']=sha(exe);save()
    proc=execute('contracts',[str(exe)]);stats=json.loads(proc.stdout)
    expected={'rectangular_goldens':576,'triangular_goldens':217,'three_level_goldens':288,'exact_actual_and_one_short_boundaries':2162,'early_or_pre_error_cases':4,'single_position_mutations':16320}
    assert stats['passed'] and all(stats[key]==value for key,value in expected.items()),stats
    assert stats['newRuntimeIntegration']==stats['N10000_execution']==False
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    report.update(passed=True,status='complete',actual_exit_code=0,contract_stats=stats);save()
    print(json.dumps({'passed':True,'EXE_sha256':report['EXE_sha256'],'report_sha256':sha(OUT/'report.json'),'stats':stats}),flush=True)

if __name__=='__main__':main()
