"""Resource-gated full N10000 VM tests; explicit1e10 is not default success."""
import argparse,ctypes,hashlib,json,shutil,subprocess,time
from pathlib import Path
from evaluate_source import exact_compare
from windows_resource_probe import monitored_run,HostMemory
def sha(x):
    h=hashlib.sha256()
    with Path(x).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def available():
    m=HostMemory();m.dwLength=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise ctypes.WinError()
    return m.ullAvailPhys
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    assert not(a.prepare and a.resume)
    p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-default-integration';root=stage/'maximum-shape';old=p/'artifacts/stage2-prepared-vm-phase1/maximum-shape'
    if a.prepare:
        accepted=json.loads((stage/'acceptance-manifest.json').read_text());assert accepted['passed']
        history=json.loads((old/'report.json').read_text());root.mkdir(exist_ok=False)
        shutil.copyfile(Path(__file__),root/'test-script.py');shutil.copyfile(p/'tools/windows_resource_probe.py',root/'windows_resource_probe.py')
        binaries={'GNUauto':stage/'candidate.exe','GNUdecoded':stage/'candidate.exe','portableauto':stage/'portable-candidate.exe'}
        expected={'source.c':history['source_sha256'],'program.meta':history['metadata_sha256'],'oracle.exe':history['oracle_binary_sha256'],'oracle.c':history['oracle_harness_sha256'],'input.bin':history['input_sha256'],'oracle.bin':history['oracle_output_sha256']}
        for name in expected:assert (old/name).is_file(),name
        for name in ['source.c','program.meta','oracle.exe','oracle.c']:assert sha(old/name)==expected[name]
        plan={'status':'predeclared; no maximum shape run','n':10000,'original_steps':1700000012,'default_limit':1000000000,'explicit_limit':10000000000,'default_must_reject':True,'full_output_bytes':800000008,'input':str(old/'input.bin'),'historical_C_output':str(old/'oracle.bin'),'oracle':str(old/'oracle.exe'),'metadata':str(old/'program.meta'),'historical_sha256':expected,'minimum_free_ram_bytes':2684354560,'minimum_free_disk_bytes':4294967296,'strict_sequential':True,'backend_order':['GNUauto','GNUdecoded','portableauto'],'binaries':{name:{'path':str(exe),'sha256':sha(exe)}for name,exe in binaries.items()},'script_sha256':sha(root/'test-script.py'),'resource_probe_sha256':sha(root/'windows_resource_probe.py'),'acceptance_manifest_sha256':sha(stage/'acceptance-manifest.json'),'large_SHA_verified':False,'functional_resources_only':True,'prepare_available_ram_bytes':available(),'prepare_free_disk_bytes':shutil.disk_usage(root).free}
        (root/'run-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'plan_sha256':sha(root/'run-plan.json'),'available_ram_bytes':plan['prepare_available_ram_bytes'],'free_disk_bytes':plan['prepare_free_disk_bytes'],'execution_started':False}));return
    plan=json.loads((root/'run-plan.json').read_text());assert sha(Path(__file__))==plan['script_sha256']and sha(p/'tools/windows_resource_probe.py')==plan['resource_probe_sha256'];assert sha(stage/'acceptance-manifest.json')==plan['acceptance_manifest_sha256']
    report_path=root/'report.json'
    if a.resume:
        report=json.loads(report_path.read_text());assert report['status']=='resource-gate-blocked'and not report['passed'];report['status']='running'
    else:
        assert not report_path.exists(),'never restart an observed run';report={'passed':False,'status':'running','plan_sha256':sha(root/'run-plan.json'),'runs':[],'default_failure':None,'oracle':None,'resource_gates':[]}
    def save():report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    def gate(label):
        ram=available();disk=shutil.disk_usage(root).free;ok=ram>=plan['minimum_free_ram_bytes']and disk>=(plan['minimum_free_disk_bytes']if not report['oracle']else plan['full_output_bytes']*(3-len(report['runs'])))
        report['resource_gates'].append({'before':label,'available_ram_bytes':ram,'free_disk_bytes':disk,'passed':ok});save()
        if not ok:report.update(status='resource-gate-blocked',pending=label);save();raise SystemExit(75)
        return ram
    gate('initial validation')
    begin=time.perf_counter()
    for name,digest in plan['historical_sha256'].items():assert sha(old/name)==digest,name
    for binary in plan['binaries'].values():assert sha(Path(binary['path']))==binary['sha256']
    report['initial_sha_validation_ms']=(time.perf_counter()-begin)*1000;report['large_SHA_verified']=True;save()
    ip=Path(plan['input']);metadata=Path(plan['metadata']);ref=root/'oracle.bin'
    if report['oracle']:
        assert sha(ref)==plan['historical_sha256']['oracle.bin']
        for r in report['runs']:assert sha(Path(r['output']))==r['sha256']
    else:
        ram=gate('originalC');begin=time.perf_counter();proc,resources=monitored_run([plan['oracle'],str(ip),str(ref),'7']);wall=(time.perf_counter()-begin)*1000
        compare=time.perf_counter();match=exact_compare(Path(plan['historical_C_output']),ref);external=(time.perf_counter()-compare)*1000;assert match['bytes']==plan['full_output_bytes']
        report['oracle']={'actual_exit_code':proc.returncode,'available_ram_before_bytes':ram,'wall_ms':wall,'whole_file_comparison_ms':external,**resources,**match};save();print(json.dumps({'original_C_complete':True,'bytes':match['bytes']}),flush=True)
    if report['default_failure']is None:
        ram=gate('GNUauto default1e9 rejection');exe=plan['binaries']['GNUauto']['path'];output=root/'default-budget-rejected.bin'
        cmd=[exe,'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto']
        begin=time.perf_counter();proc,resources=monitored_run(cmd,check=False);wall=(time.perf_counter()-begin)*1000
        assert proc.returncode==1 and proc.stderr=='error: VM instruction limit exceeded\n'and not output.exists()and not Path(str(output)+'.partial').exists()
        report['default_failure']={'actual_exit_code':proc.returncode,'stderr':proc.stderr,'command':cmd,'available_ram_before_bytes':ram,'wall_ms':wall,'default_budget':plan['default_limit'],'unpublished_output':True,**resources};save();print(json.dumps({'default_budget_rejected':True,'actual_exit_code':proc.returncode}),flush=True)
    for backend in plan['backend_order']:
        if any(r['backend']==backend for r in report['runs']):continue
        ram=gate(backend);binary=plan['binaries'][backend];start=time.perf_counter();assert sha(Path(binary['path']))==binary['sha256']and sha(ip)==plan['historical_sha256']['input.bin']and sha(ref)==plan['historical_sha256']['oracle.bin']and sha(metadata)==plan['historical_sha256']['program.meta'];check_ms=(time.perf_counter()-start)*1000
        ram=gate(backend+' launch after SHA');output=root/(backend+'.bin');cmd=[binary['path'],'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--vm-step-limit',str(plan['explicit_limit'])]
        if backend=='GNUdecoded':cmd+=['--vm-backend','decoded']
        start=time.perf_counter();proc,resources=monitored_run(cmd);wall=(time.perf_counter()-start)*1000;metrics=json.loads(proc.stdout)
        effective={'GNUauto':'decoded-threaded','GNUdecoded':'decoded','portableauto':'decoded-fallback'}[backend];assert metrics['selected_engine']=='vm'and metrics['vm_backend']==effective and metrics['vm_steps']==plan['original_steps']
        start=time.perf_counter();match=exact_compare(ref,output);comparison_ms=(time.perf_counter()-start)*1000;assert match['bytes']==plan['full_output_bytes']
        row={'backend':backend,'output':str(output),'actual_exit_code':proc.returncode,'command':cmd,'explicit_budget':plan['explicit_limit'],'available_ram_before_bytes':ram,'sha_validation_ms':check_ms,'whole_file_comparison_ms':comparison_ms,'wall_ms':wall,**resources,**metrics,**match};report['runs'].append(row);save();print(json.dumps({'backend':backend,'bytes':match['bytes'],'actual_exit_code':proc.returncode,'effective':effective,'steps':metrics['vm_steps']}),flush=True)
    assert len(report['runs'])==3;report.update(passed=True,status='complete',default_budget_passed=False,explicit_budget_passed=True);save();print(json.dumps({'passed':True,'default_budget_passed':False,'explicit_budget_passed':True,'backends':3}),flush=True)
if __name__=='__main__':main()
