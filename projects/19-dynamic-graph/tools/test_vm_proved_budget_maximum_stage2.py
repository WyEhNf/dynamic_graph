"""Frozen sequential max-shape plan; --prepare does not run or hash large files."""
import argparse,ctypes,hashlib,json,os,shutil,struct,time
from pathlib import Path
from evaluate_source import exact_compare
from windows_resource_probe import HostMemory,monitored_run

P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-proved-budget';ROOT=STAGE/'maximum-shape';OLD=P/'artifacts/stage2-prepared-vm-phase1/maximum-shape';ACCEPT=STAGE/'runtime-integration/acceptance'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def ram():
    value=HostMemory();value.dwLength=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):raise ctypes.WinError()
    return value.ullAvailPhys
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--resume',action='store_true');args=ap.parse_args();assert not(args.prepare and args.resume)
    temp=STAGE/'compiler-temp';temp.mkdir(exist_ok=True);os.environ.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
    if args.prepare:
        acceptance=read(ACCEPT/'manifest.json');assert acceptance['passed']and acceptance['whole_C_comparisons']==469 and not acceptance['maximum_execution_started']
        history=read(OLD/'report.json');assert history['passed'];ROOT.mkdir(exist_ok=False)
        expected={'source.c':history['source_sha256'],'program.meta':history['metadata_sha256'],'oracle.exe':history['oracle_binary_sha256'],'oracle.c':history['oracle_harness_sha256'],'input.bin':history['input_sha256'],'oracle.bin':history['oracle_output_sha256']}
        for name in expected:assert(OLD/name).is_file()
        for name in ['source.c','program.meta','oracle.exe','oracle.c']:assert sha(OLD/name)==expected[name]
        for name in ['input.bin','oracle.bin']:
            assert(OLD/name).stat().st_size==800000008
            with(OLD/name).open('rb')as f:assert struct.unpack('<II',f.read(8))==(1,10000)
        files=[Path(__file__),P/'tools/windows_resource_probe.py',P/'tools/evaluate_source.py']
        scripts={}
        for x in files:shutil.copyfile(x,ROOT/x.name);scripts[x.name]=sha(ROOT/x.name)
        binaries={'GNUauto':ACCEPT/'gnu/cholesky_runtime.exe','GNUdecoded':ACCEPT/'gnu/cholesky_runtime.exe','portableauto':ACCEPT/'portable/cholesky_runtime.exe'}
        for mode,x in binaries.items():assert sha(x)==acceptance['binaries']['portable'if mode=='portableauto'else'gnu']['cholesky_runtime.exe']['sha256']
        plan={'status':'predeclared; no maximum execution','n':10000,'matrices':1,'original_steps':1700000012,'expected_proved_bound':1700000012,'expected_proved_work_max':250000,'fixed_default_limit':1000000000,'effective_proved_limit':1700000012,'default_must_reject':True,'explicit_vm_step_limit_used':False,'full_output_bytes':800000008,'input':str(OLD/'input.bin'),'original_C_reference':str(OLD/'oracle.bin'),'metadata':str(OLD/'program.meta'),'historical_sha256':expected,'C_reference_note':'Actual independently compiled/executed frozen original C. No new C execution or candidate-generated reference.','minimum_free_ram_bytes':2684354560,'minimum_remaining_disk_overhead_bytes':536870912,'strict_sequential':True,'default_failure_first':True,'backend_order':['GNUauto','GNUdecoded','portableauto'],'binaries':{mode:{'path':str(x),'sha256':sha(x)}for mode,x in binaries.items()},'script_sha256':scripts,'acceptance_manifest_sha256':sha(ACCEPT/'manifest.json'),'process_env':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']},'large_SHA_verified':False,'prepare_available_ram_bytes':ram(),'prepare_free_F_bytes':shutil.disk_usage(ROOT).free,'functional_resource_only':True,'performance_claim':False,'default_ordinary_installation_changed':False,'user_apps_untouched':True,'unknown_analysis_policy':'retains fixed1e9; already verified in small contracts/C gate, not a raised cap','conflict_policy':'proved+any explicit literal limit rejected; disabled build rejects proved; small gates passed'}
        (ROOT/'run-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'plan_sha256':sha(ROOT/'run-plan.json'),'available_ram_bytes':plan['prepare_available_ram_bytes'],'free_F_bytes':plan['prepare_free_F_bytes'],'large_SHA_verified':False,'execution_started':False}),flush=True);return
    plan=read(ROOT/'run-plan.json');assert sha(ACCEPT/'manifest.json')==plan['acceptance_manifest_sha256']
    for name,digest in plan['script_sha256'].items():assert sha(P/'tools'/name)==digest and sha(ROOT/name)==digest
    report_path=ROOT/'report.json'
    if args.resume:
        report=read(report_path);assert report['status']=='resource-gate-blocked'and not report['passed'];report['status']='running';report['explicit_resumes']=report.get('explicit_resumes',0)+1
    else:
        assert not report_path.exists(),'Do not restart after an observation timeout; inspect the actual process/report.'
        report={'passed':False,'status':'running','plan_sha256':sha(ROOT/'run-plan.json'),'default_failure':None,'runs':[],'resource_gates':[],'large_SHA_verified':False,'process_env':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']}}
    def save():report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    def gate(label):
        available=ram();disk=shutil.disk_usage(ROOT).free;remaining=plan['full_output_bytes']*(3-len(report['runs']))+plan['minimum_remaining_disk_overhead_bytes'];ok=available>=plan['minimum_free_ram_bytes']and disk>=remaining
        report['resource_gates'].append({'before':label,'available_ram_bytes':available,'free_F_bytes':disk,'minimum_remaining_disk_bytes':remaining,'passed':ok});save()
        if not ok:report.update(status='resource-gate-blocked',pending=label);save();raise SystemExit(75)
        return available
    gate('initial SHA validation')
    began=time.perf_counter()
    for name,digest in plan['historical_sha256'].items():assert sha(OLD/name)==digest,name
    for mode,binary in plan['binaries'].items():assert sha(binary['path'])==binary['sha256']
    report.update(large_SHA_verified=True,initial_sha_validation_ms=(time.perf_counter()-began)*1000);save()
    for row in report['runs']:assert sha(row['output'])==row['sha256']
    ip=Path(plan['input']);metadata=Path(plan['metadata']);ref=Path(plan['original_C_reference'])
    if report['default_failure']is None:
        available=gate('GNUauto default1e9 refusal launch');target=ROOT/'fixed-default-rejected.bin';assert not target.exists()and not Path(str(target)+'.partial').exists()
        command=[plan['binaries']['GNUauto']['path'],'--metadata',str(metadata),'--input',str(ip),'--output',str(target),'--engine','auto']
        began=time.perf_counter();proc,resources=monitored_run(command,check=False);wall=(time.perf_counter()-began)*1000
        (ROOT/'fixed-default.stdout').write_text(proc.stdout,encoding='utf-8');(ROOT/'fixed-default.stderr').write_text(proc.stderr,encoding='utf-8')
        assert proc.returncode==1 and proc.stderr=='error: VM instruction limit exceeded\n'and not target.exists()and not Path(str(target)+'.partial').exists()
        report['default_failure']={'actual_exit_code':proc.returncode,'command':command,'stdout':proc.stdout,'stderr':proc.stderr,'available_ram_before_bytes':available,'wall_ms':wall,'effective_fixed_limit':plan['fixed_default_limit'],'unpublished_output':True,**resources};save();print(json.dumps({'default_budget_rejected':True,'actual_exit_code':proc.returncode}),flush=True)
    for backend in plan['backend_order']:
        if any(row['backend']==backend for row in report['runs']):continue
        gate(backend+' before SHA');binary=plan['binaries'][backend];began=time.perf_counter()
        for path,digest in [(Path(binary['path']),binary['sha256']),(ip,plan['historical_sha256']['input.bin']),(ref,plan['historical_sha256']['oracle.bin']),(metadata,plan['historical_sha256']['program.meta'])]:assert sha(path)==digest
        sha_ms=(time.perf_counter()-began)*1000;available=gate(backend+' launch after SHA');target=ROOT/(backend+'.bin');assert not target.exists()and not Path(str(target)+'.partial').exists()
        command=[binary['path'],'--metadata',str(metadata),'--input',str(ip),'--output',str(target),'--engine','auto','--vm-budget','proved']
        if backend=='GNUdecoded':command.extend(['--vm-backend','decoded'])
        print(json.dumps({'starting':backend,'available_ram_bytes':available,'effective_cap_expected':plan['effective_proved_limit'],'explicit_vm_step_limit':False}),flush=True)
        began=time.perf_counter();proc,resources=monitored_run(command,check=False);wall=(time.perf_counter()-began)*1000
        (ROOT/(backend+'.stdout')).write_text(proc.stdout,encoding='utf-8');(ROOT/(backend+'.stderr')).write_text(proc.stderr,encoding='utf-8')
        if proc.returncode:
            report.update(status='backend-failed',failed={'backend':backend,'actual_exit_code':proc.returncode,'command':command,'stdout':proc.stdout,'stderr':proc.stderr,**resources});save();raise SystemExit(proc.returncode)
        metrics=json.loads(proc.stdout);expected_backend={'GNUauto':'decoded-threaded','GNUdecoded':'decoded','portableauto':'decoded-fallback'}[backend]
        assert metrics['selected_engine']=='vm'and metrics['vm_backend']==expected_backend and metrics['vm_steps']==plan['original_steps']
        assert metrics['vm_budget_mode']=='proved'and metrics['vm_budget_proved_matrices']==1 and metrics['vm_budget_unknown_matrices']==0 and metrics['vm_budget_not_run_matrices']==0
        assert metrics['vm_budget_bound_peak']==plan['expected_proved_bound']and metrics['vm_effective_step_limit_max']==plan['effective_proved_limit']and metrics['vm_budget_work']<=plan['expected_proved_work_max']and 0<=metrics['vm_budget_proof_ms']<=metrics['compute_ms']
        began=time.perf_counter();match=exact_compare(ref,target);comparison_ms=(time.perf_counter()-began)*1000;assert match['bytes']==plan['full_output_bytes']and match['sha256']==plan['historical_sha256']['oracle.bin']
        row={'backend':backend,'output':str(target),'actual_exit_code':proc.returncode,'command':command,'available_ram_before_bytes':available,'sha_validation_ms':sha_ms,'whole_file_comparison_ms':comparison_ms,'wall_ms':wall,'explicit_vm_step_limit':False,**metrics,**resources,**match};report['runs'].append(row);save();print(json.dumps({'terminal':backend,'actual_exit_code':proc.returncode,'bytes':match['bytes'],'proved_bound':metrics['vm_budget_bound_peak'],'original_steps':metrics['vm_steps']}),flush=True)
    assert len(report['runs'])==3;report.update(passed=True,status='complete',ordinary_fixed_default_maximum_passed=False,optin_proved_policy_maximum_passed=True,C_reference_reexecuted=False,performance_claim=False);save();print(json.dumps({'passed':True,'backend_count':3,'ordinary_fixed_default_maximum_passed':False,'optin_proved_policy_maximum_passed':True,'report_sha256':sha(report_path)}),flush=True)
if __name__=='__main__':main()
