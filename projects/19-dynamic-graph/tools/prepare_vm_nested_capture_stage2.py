"""Freeze file-stdio capture only; no second compiler or VM attempt."""
import difflib,hashlib,json,shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
INITIAL=STAGE/'initial-freeze'
ACCOUNT=STAGE/'accounting-supplement'
FAILED=STAGE/'component-gate'
OUT=STAGE/'capture-supplement'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def replace(text,before,after):
    assert text.count(before)==1,(before,text.count(before));return text.replace(before,after)

def main():
    initial=read(INITIAL/'plan.json');account=read(ACCOUNT/'plan.json');failed=read(FAILED/'report.json')
    assert sha(ACCOUNT/'plan.json')=='039db32ba2c7a2abe7aaf82c9fc006a81a7382d74b0f44eae92401dbb736e690'
    assert failed['status']=='compile-failed' and failed['actual_exit_code']==4294967295 and len(failed['runs'])==1
    assert not failed['passed'] and not (FAILED/'contracts.stdout').exists()
    OUT.mkdir(exist_ok=False)
    probe_before=(FAILED/'source/tools/windows_resource_probe.py').read_text(encoding='utf-8')
    helper=replace(probe_before,'import ctypes,os,subprocess,time','import ctypes,os,subprocess,time\nfrom pathlib import Path')
    helper=replace(helper,'def monitored_run(command,interval=0.02,*,check=True,timeout=None):','def monitored_run(command,stdout_path,stderr_path,interval=0.02,*,check=True,timeout=None):')
    helper=replace(helper,'with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)as process:',"with Path(stdout_path).open('wb')as out_file,Path(stderr_path).open('wb')as err_file,subprocess.Popen(command,stdout=out_file,stderr=err_file)as process:")
    helper=replace(helper,'sample();stdout,stderr=process.communicate()',"sample();process.wait();out_file.flush();err_file.flush()\n        stdout=Path(stdout_path).read_text(encoding='utf-8',errors='replace')\n        stderr=Path(stderr_path).read_text(encoding='utf-8',errors='replace')")
    helper_path=P/'tools/windows_file_resource_probe_stage2.py';assert not helper_path.exists();helper_path.write_text(helper,encoding='utf-8')
    runner_before=(FAILED/'source/tools/test_vm_nested_component_stage2.py').read_text(encoding='utf-8')
    runner=replace(runner_before,'from windows_resource_probe import HostMemory,monitored_run','from windows_file_resource_probe_stage2 import HostMemory,monitored_run')
    runner=replace(runner,"OUT=STAGE/'component-gate'","OUT=STAGE/'component-gate-capture'\nCAPTURE=STAGE/'capture-supplement'")
    runner=replace(runner,"assert sha(SUPPLEMENT/'plan.json')=='039db32ba2c7a2abe7aaf82c9fc006a81a7382d74b0f44eae92401dbb736e690'", "assert sha(SUPPLEMENT/'plan.json')=='039db32ba2c7a2abe7aaf82c9fc006a81a7382d74b0f44eae92401dbb736e690'\n    capture=read(CAPTURE/'plan.json');assert capture['accounting_plan_sha256']==sha(SUPPLEMENT/'plan.json')\n    for relative,digest in capture['capture_source_sha256'].items():assert sha(CAPTURE/relative)==digest\n    for relative in ['tools/test_vm_nested_component_capture_stage2.py','tools/windows_file_resource_probe_stage2.py']:assert sha(P/relative)==capture['capture_source_sha256']['source/'+relative]\n    plan['compile_command']=capture['compile_command']")
    runner=replace(runner,"[Path(__file__),P/'tools/windows_resource_probe.py']", "[Path(__file__),P/'tools/windows_file_resource_probe_stage2.py']")
    runner=replace(runner,"'accounting_supplement_sha256':sha(SUPPLEMENT/'plan.json')", "'accounting_supplement_sha256':sha(SUPPLEMENT/'plan.json'),'capture_plan_sha256':sha(CAPTURE/'plan.json'),'stdio_capture':'direct raw binary files; no PIPE buffer; counter method unchanged'")
    runner=replace(runner,'process,resources=monitored_run(command,check=False)',"process,resources=monitored_run(command,OUT/(phase+'.stdout'),OUT/(phase+'.stderr'),check=False)")
    runner=replace(runner,"        (OUT/(phase+'.stdout')).write_text(process.stdout,encoding='utf-8');(OUT/(phase+'.stderr')).write_text(process.stderr,encoding='utf-8')\n",'')
    runner_path=P/'tools/test_vm_nested_component_capture_stage2.py';assert not runner_path.exists();runner_path.write_text(runner,encoding='utf-8')
    files={}
    for source in [helper_path,runner_path,Path(__file__)]:
        target=OUT/'source'/source.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);files[target.relative_to(OUT).as_posix()]=sha(target)
    for name,before,after in [('resource-probe',probe_before,helper),('runner',runner_before,runner)]:
        (OUT/(name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='previous-'+name,tofile='capture-'+name)),encoding='utf-8')
    inherited={}
    for name,record in initial['frozen_files'].items():assert sha(INITIAL/name)==record['sha256'];inherited['initial-freeze/'+name]=record['sha256']
    for name,record in account['candidate_files'].items():assert sha(ACCOUNT/name)==record['sha256'];inherited['accounting-supplement/'+name]=record['sha256']
    failed_files={}
    for name in ['report.json','compile.stdout','compile.stderr','controlled-termination.json']:
        target=OUT/'failed-attempt'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(FAILED/name,target);failed_files[name]=sha(target)
    command=list(account['compile_command']);command[-1]=str(STAGE/'component-gate-capture/vm-nested-bound-tests.exe')
    data={'schema':'isolated-nested-VM-file-capture-supplement-v1','status':'static capture-only revision; second attempt not started','accounting_plan_sha256':sha(ACCOUNT/'plan.json'),'initial_plan_sha256':sha(INITIAL/'plan.json'),'capture_source_sha256':files,'retained_immutable_source_sha256':inherited,'compiler':account['compiler'],'compile_command':command,'compile_flags':account['compile_flags'],'ABI':account['ABI'],'work_limit':250000,'golden_plan':account['golden_plan'],'minimum_launch_RAM_bytes':account['minimum_launch_RAM_bytes'],'minimum_F_free_bytes':account['minimum_F_free_bytes'],'future_compile_environment':account['future_compile_environment'],'failed_attempt_files_sha256':failed_files,'failed_attempt_actual_tool_session':71641,'failed_attempt_tool_exit_code':1,'failed_attempt_compiler_actual_exit_code':4294967295,'failed_attempt_note':'Only owned compiler and child were terminated after repeated unchanged child CPU0.578125s and wait state, no PIPE drainage, stderr3846B ending partway through warning. Captured all already-written bytes, not a natural complete compiler diagnostic. No EXE/contract result is claimed.','capture_changes':['stdout/stderr passed to ordinary binary file descriptors, never PIPE','flush/read text after process terminal, retaining original raw file bytes','same Win32 counters/sampling and resource gates','independent new output folder; no prior gate overwrite','sole compile command change is new output filename; all source/header/core/flags unchanged'],'candidate_changed':False,'ABI_changed':False,'gold_or_algorithm_changed':False,'default_changed':False,'compiler_started':False,'VM_started':False,'large_input_started':False,'root_second_compile_authorization_required':True,'ordinary_sha256':account['ordinary_sha256'],'memory_sha256':account['memory_sha256']}
    (OUT/'plan.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':True,'capture_plan_sha256':sha(OUT/'plan.json'),'runner_sha256':sha(runner_path),'helper_sha256':sha(helper_path),'new_compile_or_VM_execution':False,'old_gate_retained':True}))

if __name__=='__main__':main()
