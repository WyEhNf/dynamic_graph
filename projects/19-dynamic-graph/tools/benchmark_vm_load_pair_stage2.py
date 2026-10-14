"""Prepare source only; an independently authorized run compares exact a95 CLI."""
import argparse,ctypes,hashlib,json,math,os,shutil,statistics,struct,time,traceback
from pathlib import Path
from windows_file_resource_probe_stage2 import HostMemory,monitored_run

R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
PLAN=R/'performance-plan'
OUT=R/'performance-evidence'
ONE=1073741824
BACKENDS=['decoded-threaded','decoded-threaded-load-pair']
FUNCTIONAL_PLAN_SHA='bfbbf8634dcad7e6afb49ecf455f5783d916d3d6b71bdc7c3a88c292b21eb981'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def fresh():
    m=HostMemory();m.dwLength=ctypes.sizeof(m)
    if not ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx(ctypes.byref(m)):raise ctypes.WinError(ctypes.get_last_error())
    return {'available_RAM_bytes':m.ullAvailPhys,'free_G_bytes':shutil.disk_usage(R).free,
            'required_RAM_and_disk_bytes':ONE}

def headers(path):
    sizes=[]
    with Path(path).open('rb')as f:
        count=struct.unpack('<I',f.read(4))[0]
        for _ in range(count):
            n=struct.unpack('<I',f.read(4))[0];assert 3<=n<=10000;sizes.append(n);f.seek(n*n*8,1)
        assert f.tell()==Path(path).stat().st_size and f.read()==b''
    return sizes

def whole_compare(candidate,oracle):
    a=hashlib.sha256();b=hashlib.sha256();count=0
    with Path(candidate).open('rb')as x,Path(oracle).open('rb')as y:
        while True:
            left=x.read(1048576);right=y.read(1048576)
            assert left==right,('whole originalC byte mismatch',count)
            a.update(left);b.update(right);count+=len(left)
            if not left:break
    return {'bytes_compared':count,'candidate_sha256':a.hexdigest(),'original_C_sha256':b.hexdigest()}

def prepare():
    assert not PLAN.exists();PLAN.mkdir()
    prior=read(R/'next-static-plan/plan.json')
    cases=prior['cost']['cases'];assert len(cases)==19
    assert len({c['identity']for c in cases})==19
    assert sum(c['default_path_scope']=='native-control'for c in cases)==1
    assert all(c['default_path_scope']in ['genuine-default-VM','native-control']for c in cases)
    assert sha(R/'functional-plan-resource-supplement/plan.json')==FUNCTIONAL_PLAN_SHA
    shutil.copyfile(Path(__file__),PLAN/'runner.py')
    shutil.copyfile(Path(__file__).with_name('windows_file_resource_probe_stage2.py'),PLAN/'windows_file_resource_probe_stage2.py')
    shutil.copyfile(R/'next-static-plan/plan.json',PLAN/'parent-plan.json')
    shutil.copyfile(R/'functional-plan-resource-supplement/plan.json',PLAN/'functional-plan.json')
    accepted=R/'build-gate-acceptance/build-gnu'
    # No large input/oracle payload is read during source-only preparation.
    for name in ['cholesky_runtime.exe','CMakeFiles/cholesky_core.dir/flags.make',
                 'CMakeFiles/cholesky_runtime.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt',
                 'CMakeFiles/cholesky_runtime.dir/linkLibs.rsp']:
        dest=PLAN/'accepted-build'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(accepted/name,dest)
    assert sha(PLAN/'accepted-build/cholesky_runtime.exe')==prior['runtime']['sha256']
    assert sha(PLAN/'accepted-build/CMakeFiles/cholesky_core.dir/flags.make')==prior['runtime']['core_flags_sha256']
    schedule=[]
    for case in cases:
        for round_index in range(5):
            order=BACKENDS if round_index%2==0 else list(reversed(BACKENDS))
            for backend in order:
                schedule.append({'identity':case['identity'],'round':round_index,'backend':backend})
    files={p.relative_to(PLAN).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(PLAN.rglob('*'))if p.is_file()}
    plan={'schema':'load-pair-same-a95-cost-plan-v1','status':'source-only; no performance executed',
          'parent_plan_sha256':sha(R/'next-static-plan/plan.json'),'runtime':prior['runtime'],
          'functional_gate_required':{'path':str(R/'functional-evidence/report.json'),'plan_sha256':FUNCTIONAL_PLAN_SHA,
                                      'passed':True,'records':54,'pairs':27},
          'cases':cases,'rounds':5,'records':190,'pairs':95,'genuine_VM_pairs':90,'native_bypass_pairs':5,
          'backends':BACKENDS,'schedule':schedule,'order':'case-major; plain/fused even rounds, fused/plain odd rounds; original19 order',
          'sole_variation':'--vm-backend on exact same immutable a95 executable; fixed1e9, no explicit step limit, same original input/meta/engine/scheduler/threads/block',
          'compile_new_C_or_oracle':False,'amplify_or_select_sources':False,'observer_used_for_perf':False,
          'a95_last_pc':'not exported by original a95 CLI; explicitly unavailable/null, never inferred. Actual per-matrix PC contract is covered by separate54 observer functionality, whose wall/compute is excluded here.',
          'compute_scope':'real a95 main.cpp times execute_owned; includes decode+per-execution LOAD-pair discovery+dispatch+graph/kernel/export and input validation; Metadata/input/output IO separately exported',
          'comparison_scope':'all19 sources including short unamplified6 holdouts and native bypass control; all95 positive/negative/tie ratios retained; VM90 and native5 separate; no official85-point inference',
          'host_scope':'whole-host raw CPU/RAM counters include user programs and probe; do not close user applications or claim whole host idle',
          'fresh_reference_SHA_each_launch':True,'fresh_a95_SHA_each_launch':True,'complete_original_C_bytes_each_trial':True,
          'source_only_large_data_SHA':'inherited from root accepted parent; fresh payload streaming occurs only in later authorized --run',
          'output_bytes_predeclared':sum(c['reference_bytes']for c in cases)*10,
          'guard_RAM_and_G_each_launch_bytes':ONE,'resource_failure_exitcode':75,
          'failure_policy':'first failure, raw files, observed resources and partial outputs retained; no retry, overwrite, omitted case or automatic promotion',
          'child_environment':{**{k:str(R/'compiler-temp')for k in ['TEMP','TMP','TMPDIR']},'PATH_prefix':'E:/mingw64/bin'},
          'files':files,'prepare_resources':fresh()}
    write(PLAN/'plan.json',plan)
    print(json.dumps({'prepared':True,'plan':str(PLAN/'plan.json'),'sha256':sha(PLAN/'plan.json'),
                      'frozen_files':len(files),'records':190,'pairs':95,'performance_executed':False}),flush=True)

def validate_metric(metric,case,backend):
    assert metric['matrices']==case['matrices'] and metric['vm_budget_mode']=='fixed'
    assert metric['vm_budget_work']==metric['vm_budget_proof_ms']==0
    assert metric['vm_budget_proved_matrices']==metric['vm_budget_unknown_matrices']==0
    assert metric['vm_budget_not_run_matrices']==case['matrices']
    assert 'vm_last_pc'not in metric # Do not fabricate an unexported field.
    for key in ['compute_ms','input_validation_ms','input_recycle_ms','vm_prepare_ms','vm_fusion_plan_ms',
                'graph_ms','kernel_ms','export_ms','metadata_read_ms','input_read_ms','output_write_ms']:
        assert math.isfinite(metric[key])and metric[key]>=0,key
    # Default CLI prints six significant digits, so permit only rounding scale here.
    tolerance=max(.001,metric['compute_ms']*1e-5)
    assert metric['vm_fusion_plan_ms']<=metric['vm_prepare_ms']+tolerance<=metric['compute_ms']+2*tolerance
    assert metric['vm_steps']==case['expected_vm_steps']
    if case['default_path_scope']=='native-control':
        assert metric['selected_engine']!='vm'and metric['vm_steps']==0
        assert metric['vm_fusion_pairs_discovered']==metric['vm_fusion_pairs_executed']==metric['vm_fusion_plan_ms']==0
    else:
        assert metric['selected_engine']=='vm'and metric['vm_backend']==backend
        assert metric['vm_effective_step_limit_max']==1000000000
        if backend==BACKENDS[0]:
            assert metric['vm_fusion_pairs_discovered']==metric['vm_fusion_pairs_executed']==metric['vm_fusion_plan_ms']==0
        else:
            assert metric['vm_fusion_status_last']=='entry-safe-pairs'
            assert 0<=metric['vm_fusion_pairs_executed']<=metric['vm_steps']//2

def summarize(report,plan):
    for case in plan['cases']:
        ratios=[];wall_ratios=[]
        for round_index in range(5):
            rows=[r for r in report['records']if r['identity']==case['identity']and r['round']==round_index]
            assert len(rows)==2
            a=next(r for r in rows if r['backend']==BACKENDS[0]);b=next(r for r in rows if r['backend']==BACKENDS[1])
            assert a['metric']['vm_steps']==b['metric']['vm_steps']
            assert a['wholeC']['candidate_sha256']==b['wholeC']['candidate_sha256']
            assert a['metric']['compute_ms']>0 and a['process_wall_ms']>0
            ratio=b['metric']['compute_ms']/a['metric']['compute_ms'];wall_ratio=b['process_wall_ms']/a['process_wall_ms']
            outcome='win'if ratio<1 else'negative'if ratio>1 else'tie'
            report['pairs'].append({'identity':case['identity'],'round':round_index,'scope':case['default_path_scope'],
                                   'compute_ratio_fused_over_plain':ratio,'process_wall_ratio_fused_over_plain':wall_ratio,'outcome':outcome})
            ratios.append(ratio);wall_ratios.append(wall_ratio)
        report['summary'].append({'identity':case['identity'],'scope':case['default_path_scope'],
                                  'all_five_compute_ratios':ratios,'all_five_wall_ratios':wall_ratios,
                                  'median_paired_compute_ratio':statistics.median(ratios),'median_paired_wall_ratio':statistics.median(wall_ratios),
                                  'wins':sum(x<1 for x in ratios),'negative':sum(x>1 for x in ratios),'ties':sum(x==1 for x in ratios)})
    for scope,denominator in [('genuine-default-VM',90),('native-control',5)]:
        pairs=[p for p in report['pairs']if p['scope']==scope];assert len(pairs)==denominator
        report['cohort_counts'][scope]={'pairs':len(pairs),'wins':sum(p['outcome']=='win'for p in pairs),
                                      'negative':sum(p['outcome']=='negative'for p in pairs),'ties':sum(p['outcome']=='tie'for p in pairs)}

def run():
    assert not OUT.exists(),'never restart or overwrite actual evidence'
    plan=read(PLAN/'plan.json')
    for path,item in plan['files'].items():assert sha(PLAN/path)==item['sha256'],path
    assert sha(R/'next-static-plan/plan.json')==plan['parent_plan_sha256']
    functional=read(plan['functional_gate_required']['path']);required=plan['functional_gate_required']
    assert functional['passed']and functional['plan_sha256']==required['plan_sha256']
    assert len(functional['records'])==54 and len(functional['pairs'])==27
    assert all(r['actual_exitcode']==0 for r in functional['records'])
    OUT.mkdir();(R/'compiler-temp').mkdir(exist_ok=True)
    for key,value in plan['child_environment'].items():
        if key!='PATH_prefix':os.environ[key]=value
    os.environ['PATH']=plan['child_environment']['PATH_prefix']+os.pathsep+os.environ.get('PATH','')
    report={'schema':'load-pair-same-a95-cost-actual-v1','passed':False,'owner_PID':os.getpid(),'plan_sha256':sha(PLAN/'plan.json'),
            'functional_gate_actual_sha256':sha(required['path']),'records':[],'pairs':[],'summary':[],
            'resource_gate_observations':[],'cohort_counts':{},'observer_used':False,'runtime_or_default_changed':False}
    began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;write(OUT/'report.json',report)
    def gate(label):
        value=fresh();value.update(label=label,passed=min(value['available_RAM_bytes'],value['free_G_bytes'])>=ONE)
        report['resource_gate_observations'].append(value);save()
        if not value['passed']:raise SystemExit(75)
        return value
    save();print(json.dumps({'actual_owner_PID':os.getpid(),'evidence':str(OUT)}),flush=True)
    cases={c['identity']:c for c in plan['cases']}
    try:
        for trial in plan['schedule']:
            case=cases[trial['identity']];label=trial['identity']+'-r'+str(trial['round'])+'-'+trial['backend']
            row={**trial,'scope':case['default_path_scope'],'case':case,'vm_last_pc':None,
                 'vm_last_pc_status':'unavailable in exact a95 CLI; not inferred'}
            report['records'].append(row);row['before_reference_resources']=gate(label+'-before-SHA')
            start=time.perf_counter();row['actual_reference_sha256']={name:sha(path)for name,path in case['paths'].items()}
            assert row['actual_reference_sha256']==case['hashes'],label
            row['actual_exe_sha256']=sha(plan['runtime']['path']);assert row['actual_exe_sha256']==plan['runtime']['sha256']
            row['reference_and_EXE_SHA_ms']=(time.perf_counter()-start)*1000
            assert headers(case['paths']['input.bin'])==headers(case['paths']['oracle.bin'])==case['input_matrix_headers']
            output=OUT/(label+'.bin');assert not output.exists()and not Path(str(output)+'.partial').exists()
            common=case['runtime_command_common'];assert common[0]==plan['runtime']['path']
            command=common+['--output',str(output),'--vm-backend',trial['backend']]
            row.update(command=command,output=str(output),raw_stdout=str(OUT/(label+'.stdout')),raw_stderr=str(OUT/(label+'.stderr')))
            row['fresh_launch_resources']=gate(label+'-launch');save()
            start=time.perf_counter();proc,resource=monitored_run(command,row['raw_stdout'],row['raw_stderr'],check=False)
            row.update(actual_exitcode=proc.returncode,process_wall_ms=(time.perf_counter()-start)*1000,resource=resource)
            row['raw_stdout_sha256']=sha(row['raw_stdout']);row['raw_stderr_sha256']=sha(row['raw_stderr']);save()
            assert proc.returncode==0,(label,proc.returncode,proc.stderr)
            metric=json.loads(proc.stdout);row['metric']=metric;save();validate_metric(metric,case,trial['backend'])
            start=time.perf_counter();row['wholeC']=whole_compare(output,case['paths']['oracle.bin'])
            row['whole_file_compare_and_SHA_ms']=(time.perf_counter()-start)*1000
            assert row['wholeC']['bytes_compared']==case['reference_bytes']and row['wholeC']['original_C_sha256']==case['hashes']['oracle.bin']
            assert headers(output)==case['input_matrix_headers'];row['passed']=True;save()
            print(json.dumps({'terminal':label,'exitcode':proc.returncode,'compute_ms':metric['compute_ms'],'wholeC_passed':True}),flush=True)
        assert len(report['records'])==190;assert all(r['passed']for r in report['records'])
        summarize(report,plan);assert len(report['pairs'])==95
        report['passed']=True
    except BaseException as error:
        report['first_failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        save();raise
    save();print(json.dumps({'passed':True,'records':190,'pairs':95,'cohort_counts':report['cohort_counts'],
                           'report_sha256':sha(OUT/'report.json')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true');group.add_argument('--run',action='store_true');args=parser.parse_args()
    prepare()if args.prepare else run()
