"""Prepare-only by default; separately authorized single observer compile +54 runs."""
import argparse,ctypes,hashlib,json,math,os,shutil,struct,time,traceback
from pathlib import Path
from windows_file_resource_probe_stage2 import HostMemory,monitored_run
P=Path(__file__).resolve().parents[1]
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
PLAN=R/'functional-plan'
EVIDENCE=R/'functional-evidence'
ONE=1073741824
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def fresh():
    m=HostMemory();m.dwLength=ctypes.sizeof(m)
    if not ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx(ctypes.byref(m)):raise ctypes.WinError(ctypes.get_last_error())
    return {'available_RAM_bytes':m.ullAvailPhys,'free_G_bytes':shutil.disk_usage(R).free,'required_RAM_and_disk_bytes':ONE}
def headers(path):
    result=[]
    with Path(path).open('rb')as f:
        count=struct.unpack('<I',f.read(4))[0]
        for _ in range(count):
            n=struct.unpack('<I',f.read(4))[0];assert 3<=n<=10000;result.append(n);f.seek(n*n*8,1)
        assert f.tell()==Path(path).stat().st_size
    return result
def whole_compare(a,b):
    ha=hashlib.sha256();hb=hashlib.sha256();count=0
    with Path(a).open('rb')as x,Path(b).open('rb')as y:
        while True:
            left=x.read(1048576);right=y.read(1048576);ha.update(left);hb.update(right)
            assert left==right,('whole originalC byte mismatch',count)
            count+=len(left)
            if not left:break
    return {'bytes_compared':count,'candidate_sha256':ha.hexdigest(),'original_C_sha256':hb.hexdigest()}
def prepare():
    assert not PLAN.exists();PLAN.mkdir()
    next_plan=read(R/'next-static-plan/plan.json')
    assert len(next_plan['functional']['cases'])==25 and len(next_plan['functional']['forced_cases'])==2
    observer=Path(__file__).with_name('vm_load_pair_functional_observer_stage2.cpp')
    shutil.copyfile(observer,PLAN/observer.name);shutil.copyfile(Path(__file__),PLAN/'runner.py')
    shutil.copyfile(Path(__file__).with_name('windows_file_resource_probe_stage2.py'),PLAN/'windows_file_resource_probe_stage2.py')
    shutil.copytree(R/'workspace/include/cholesky',PLAN/'include/cholesky')
    accepted=R/'build-gate-acceptance/build-gnu'
    for path in ['libcholesky_core.a','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/flags.make',
                 'CMakeFiles/cholesky_runtime.dir/link.txt','CMakeFiles/cholesky_runtime.dir/linkLibs.rsp']:
        dest=PLAN/'accepted-build'/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(accepted/path,dest)
    public=['CHOL_HAVE_THREADED_DISPATCH=1','CHOL_LOAD_PAIR_VM=1','CHOL_PREPARED_VM=1','CHOL_THREADED_VM=1']
    compile_command=['E:/mingw64/bin/g++.exe','-O3','-DNDEBUG','-std=gnu++20','-Wall','-Wextra','-Wpedantic','-fno-fast-math','-ffp-contract=off',
                     *('-D'+d for d in public),'-I'+str(PLAN/'include'),str(PLAN/observer.name),
                     str(PLAN/'accepted-build/libcholesky_core.a'),'-lpthread','-lkernel32','-luser32','-lgdi32','-lwinspool','-lshell32',
                     '-lole32','-loleaut32','-luuid','-lcomdlg32','-ladvapi32','-o',str(EVIDENCE/'functional-observer.exe')]
    cases=next_plan['functional']['cases']+next_plan['functional']['forced_cases']
    files={p.relative_to(PLAN).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(PLAN.rglob('*'))if p.is_file()}
    plan={'schema':'load-pair-functional-observer-plan-v1','status':'source-only prepared; not compiled/run',
          'next_plan_sha256':sha(R/'next-static-plan/plan.json'),'accepted_a95_SHA':next_plan['runtime']['sha256'],
          'accepted_core_SHA':sha(PLAN/'accepted-build/libcholesky_core.a'),'matching_ABI_header_SHA':sha(PLAN/'include/cholesky/runtime.hpp'),
          'compile_command':compile_command,'compile_attempts_authorized_later':1,'proof_and_nested_features':'acceptedcoreOFF unchanged',
          'observer_path':'same public ABI/core as a95; same Metadata/input parsing/Options/execute_owned; output from core only, no expected data read in observer',
          'a95_lastpc_absence':'canonical CLI does not expose lastpc; observer directly records finalized RunMetrics at each matrix. Native lastpc actual value marked not applicable. No inferred PC is recorded.',
          'observer_time_scope':'functional diagnostics only; not production/performance compute. Future95 paired cost uses exacta95 executable.',
          'cases':cases,'unique_C_sources':19,'streams':27,'records':54,'backends':['decoded-threaded','decoded-threaded-load-pair'],
          'original_C_refs':'actual previously independently compiled GCC source/harness/executable/output; reuse exact refs without newC/oracle generation',
          'fresh_all_six_reference_SHA_each_launch':True,'whole_file_bytes_each_result':True,
          'compare_permatrix':['index','n','error','engine','vm_steps','vm_last_pc','lastpc_applicable'],
          'guard_RAM_G_each_launch_bytes':ONE,'resource_failure_exitcode':75,'file_stdio':True,
          'child_environment':{**{k:str(R/'compiler-temp')for k in ['TEMP','TMP','TMPDIR']},'PATH_prefix':'E:/mingw64/bin'},
          'failure_policy':'firstactualfailure/raw/report/partialoutputs preserved; no retry or missing-case deletion',
          'source_files':files,'no_compile_C_VM_performance_or_default_changes_at_prepare':True,'prepare_resources':fresh()}
    write(PLAN/'plan.json',plan)
    print(json.dumps({'prepared':True,'plan':str(PLAN/'plan.json'),'sha256':sha(PLAN/'plan.json'),'frozen_files':len(files),'actual_runs':0}),flush=True)
def run():
    assert not EVIDENCE.exists();EVIDENCE.mkdir()
    plan=read(PLAN/'plan.json');assert sha(R/'next-static-plan/plan.json')==plan['next_plan_sha256']
    for path,item in plan['source_files'].items():assert sha(PLAN/path)==item['sha256'],path
    assert sha(PLAN/'include/cholesky/runtime.hpp')==plan['matching_ABI_header_SHA']
    assert sha(PLAN/'accepted-build/libcholesky_core.a')==plan['accepted_core_SHA']
    for key,value in plan['child_environment'].items():
        if key!='PATH_prefix':os.environ[key]=value
    os.environ['PATH']=plan['child_environment']['PATH_prefix']+os.pathsep+os.environ.get('PATH','')
    (R/'compiler-temp').mkdir(exist_ok=True)
    report={'schema':'load-pair-full-realC-functional-actual-v1','passed':False,'owner_PID':os.getpid(),'plan_sha256':sha(PLAN/'plan.json'),
            'compile':None,'records':[],'pairs':[],'performance_executed':False}
    write(EVIDENCE/'report.json',report)
    print(json.dumps({'actual_owner_PID':os.getpid(),'evidence':str(EVIDENCE)}),flush=True)
    def gate():
        value=fresh()
        if min(value['available_RAM_bytes'],value['free_G_bytes'])<ONE:raise SystemExit(75)
        return value
    def launch(label,command,target):
        target.update({'label':label,'command':command,'fresh_resources':gate(),'raw_stdout':str(EVIDENCE/(label+'.stdout')),'raw_stderr':str(EVIDENCE/(label+'.stderr'))})
        write(EVIDENCE/'report.json',report);print(json.dumps({'launch':label,'fresh':target['fresh_resources']}),flush=True)
        start=time.perf_counter();completed,resource=monitored_run(command,target['raw_stdout'],target['raw_stderr'],check=False)
        target.update({'actual_exitcode':completed.returncode,'wall_ms_functional_only':(time.perf_counter()-start)*1000,'resource':resource,
                       'raw_stdout_sha256':sha(target['raw_stdout']),'raw_stderr_sha256':sha(target['raw_stderr'])})
        write(EVIDENCE/'report.json',report);print(json.dumps({'terminal':label,'exitcode':completed.returncode}),flush=True)
        assert completed.returncode==0,(label,completed.returncode,completed.stderr)
        return completed
    try:
        report['compile']={};launch('observer-compile',plan['compile_command'],report['compile'])
        report['observer_EXE_sha256']=sha(EVIDENCE/'functional-observer.exe')
        for case in plan['cases']:
            actual=[]
            for backend in plan['backends']:
                identity=case['identity'];row={'identity':identity,'backend':backend,'case':case};report['records'].append(row)
                row['pre_reference_resources']=gate();start=time.perf_counter()
                row['actual_reference_sha256']={name:sha(path)for name,path in case['paths'].items()}
                assert row['actual_reference_sha256']==case['hashes'],identity
                row['reference_SHA_check_ms']=(time.perf_counter()-start)*1000
                assert headers(case['paths']['input.bin'])==headers(case['paths']['oracle.bin'])==case['input_matrix_headers']
                output=EVIDENCE/(identity+'-'+backend+'.bin');row['output']=str(output)
                assert not output.exists()and not Path(str(output)+'.partial').exists()
                command=[str(EVIDENCE/'functional-observer.exe'),case['paths']['program.meta'],case['paths']['input.bin'],str(output),backend,
                         case['engine_requested'],str(case['block']),'4','parallel']
                completed=launch(identity+'-'+backend,command,row)
                messages=[json.loads(line)for line in completed.stdout.splitlines()];matrices=messages[:-1];summary=messages[-1]
                row['matrices']=matrices;row['summary']=summary
                assert summary['kind']=='summary'and summary['matrices']==case['matrices']and len(matrices)==case['matrices']
                assert summary['step_limit_default']==1000000000 and summary['vm_budget_mode']=='fixed'and not summary['step_limit_explicit']
                assert summary['vm_steps']==sum(m['vm_steps']for m in matrices)
                if case['expected_vm_steps']is not None:assert summary['vm_steps']==case['expected_vm_steps'],identity
                for i,m in enumerate(matrices):
                    assert m['kind']=='matrix'and m['index']==i and m['n']==case['input_matrix_headers'][i]and not m['error']
                    assert m['vm_budget_work']==m['vm_budget_proof_ms']==0
                    for key in ['compute_ms_functional_only','vm_prepare_ms','vm_fusion_plan_ms']:
                        assert math.isfinite(m[key])and m[key]>=0
                    assert m['vm_fusion_plan_ms']<=m['vm_prepare_ms']+1e-8<=m['compute_ms_functional_only']+2e-8
                    if case['default_path_scope']=='native-control':
                        assert m['engine']!='vm'and m['vm_steps']==0 and not m['lastpc_applicable']
                        assert m['vm_fusion_pairs_discovered']==m['vm_fusion_pairs_executed']==0
                    else:
                        assert m['engine']=='vm'and m['backend']==backend and m['lastpc_applicable']and m['vm_effective_step_limit']==1000000000
                        if backend=='decoded-threaded':assert m['vm_fusion_pairs_discovered']==m['vm_fusion_pairs_executed']==m['vm_fusion_plan_ms']==0
                        else:
                            assert m['vm_fusion_status']=='entry-safe-pairs'
                            assert m['vm_fusion_pairs_executed']<=m['vm_steps']//2
                            assert m['vm_fusion_pairs_discovered']>0 or m['vm_fusion_pairs_executed']==0
                start=time.perf_counter();row['wholeC_comparison']=whole_compare(output,case['paths']['oracle.bin']);row['full_byte_check_ms']=(time.perf_counter()-start)*1000
                assert row['wholeC_comparison']['bytes_compared']==case['reference_bytes']
                assert row['wholeC_comparison']['original_C_sha256']==case['hashes']['oracle.bin']
                assert headers(output)==case['input_matrix_headers']
                actual.append(row);write(EVIDENCE/'report.json',report)
            a,b=actual
            for left,right in zip(a['matrices'],b['matrices']):
                assert all(left[key]==right[key]for key in plan['compare_permatrix']),(case['identity'],'permatrix steps/PC/error/engine changed')
            assert a['wholeC_comparison']['candidate_sha256']==b['wholeC_comparison']['candidate_sha256']
            report['pairs'].append({'identity':case['identity'],'passed':True,'matrices':case['matrices'],'both_complete_C_bytes_equal':True,
                                    'sum_steps':a['summary']['vm_steps'],'permatrix_steps_PC_engine_error_equal':True})
            write(EVIDENCE/'report.json',report)
        assert len(report['records'])==54 and len(report['pairs'])==27
        report['passed']=True
    except BaseException as error:
        report['first_failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        write(EVIDENCE/'report.json',report);raise
    write(EVIDENCE/'report.json',report)
    print(json.dumps({'passed':True,'records':54,'pairs':27,'report_sha256':sha(EVIDENCE/'report.json')}),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
    assert args.prepare!=args.run;prepare()if args.prepare else run()
