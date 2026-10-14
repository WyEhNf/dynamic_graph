"""Prepare, then separately authorize one sequential true-C N10000 triangle gate.

There is no resume/retry mode and no large Gram/decoded/portable extension.
"""
import argparse, ast, json, os, re, shutil, struct, time
from pathlib import Path
from benchmark_vm_nested_policy_stage2 import available, copy_checked, exact_compare, read, sha, write
from windows_file_resource_probe_stage2 import monitored_run

P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-nested-budget'
ROOT=STAGE/'triangular-maximum';COST=STAGE/'policy-cost';ACCEPT=STAGE/'runtime-integration/acceptance'
DESIGN=STAGE/'next-static-design/plan.json'
FULL_BYTES=800000008;RESERVE=536870912;MIN_RAM=2684354560

def large_header(path):
    assert Path(path).stat().st_size==FULL_BYTES
    with Path(path).open('rb')as stream:assert struct.unpack('<II',stream.read(8))==(1,10000)

def prepare():
    assert not ROOT.exists(),'immutable preparation directory already exists'
    design=read(DESIGN);cost=read(COST/'run-plan.json');accepted=read(ACCEPT/'manifest.json')
    analysis=read(STAGE/'analysis-only/report.json');assert accepted['passed']and analysis['passed']
    assert sha(ACCEPT/'manifest.json')==design['accepted_manifest_sha256']
    case=next(c for c in cost['cases']if c['source']=='nested-triangular-dense')
    prediction=next(p for p in design['predictions']['nested-triangular']['points']if p['N']==10000)
    probe=next(r for r in analysis['records']if r['source']=='nested-triangular'and r['N']==10000)
    assert probe['bound']==prediction['predicted_conservative_bound']==2799890009
    assert prediction['predicted_actual_steps_from_complete_instruction_layout']==1400030009
    assert probe['proved']and probe['selected_stage']=='nested'and probe['shared_work']==24161
    ROOT.mkdir();frozen={}
    def copy(source,relative,expected=None):
        digest=copy_checked(source,ROOT/relative,expected)
        frozen[relative]={'origin':str(source),'sha256':digest,'bytes':Path(source).stat().st_size}
    for name in ['source.c','program.meta','oracle.c','oracle.exe']:
        copy(case['paths'][name],name,case['hashes'][name])
    copy(cost['binary']['path'],'runtime.exe',design['same_binary']['sha256'])
    for folder in ['implementation-source','implementation-build']:
        for source in sorted((COST/folder).rglob('*')):
            if source.is_file():copy(source,source.relative_to(COST).as_posix())
    actual_source=P/'artifacts/stage2-vm-nested-budget/runtime-integration/functional-evidence/nested-triangular'
    for name in ['program.analysis.json','program.ll']:
        if (actual_source/name).is_file():copy(actual_source/name,'C-frontend-lineage/'+name)
    harness=(ROOT/'oracle.c').read_text()
    included=Path(re.search(r'^#include "([^"]+)"',harness,re.MULTILINE)[1])
    assert sha(included)==case['hashes']['source.c']
    # Complete local Python import closure; no frontend/compiler function executes.
    pending=[Path(__file__)];seen=set()
    while pending:
        source=pending.pop()
        if source in seen:continue
        seen.add(source);tree=ast.parse(source.read_text(encoding='utf-8'))
        copy(source,'runner-source/'+source.relative_to(P).as_posix())
        for node in ast.walk(tree):
            modules=([node.module]if isinstance(node,ast.ImportFrom)and node.level==0 else
                     [a.name for a in node.names]if isinstance(node,ast.Import)else[])
            for module in modules:
                if module:
                    local=P/'tools'/(module.split('.')[0]+'.py')
                    if local.exists():pending.append(local)
    for name in ['next-static-design/plan.json','analysis-only/report.json','analysis-only-acceptance/manifest.json',
                 'policy-cost-acceptance/manifest.json','runtime-integration/acceptance/manifest.json']:
        copy(STAGE/name,'lineage/'+name)
    inp=Path(design['large_functional_design']['input_reuse']['path']);large_header(inp)
    gate={'available_RAM_bytes':available(),'free_F_bytes':shutil.disk_usage(ROOT).free,
          'minimum_RAM_bytes':MIN_RAM,'minimum_F_bytes':2*FULL_BYTES+RESERVE}
    gate['passed']=gate['available_RAM_bytes']>=MIN_RAM and gate['free_F_bytes']>=gate['minimum_F_bytes']
    write(ROOT/'prepare-resource-gate.json',gate)
    if not gate['passed']:
        write(ROOT/'prepare-failure.json',{'status':'resource-gate-blocked','pending':'fresh input SHA preparation',
                                         'actual_exit_code':75,'no_C_or_VM_executed':True})
        raise SystemExit(75)
    checked=time.perf_counter();input_sha=sha(inp);sha_ms=(time.perf_counter()-checked)*1000
    assert input_sha==design['large_functional_design']['input_reuse']['historical_sha256']
    text=(ROOT/'program.meta').read_text();assert text.startswith('DYNCHOL 2\n')and'optimized=none\n'in text
    plan={'schema':'optional-nested-VM-triangular-maximum-plan-v1',
          'status':'prepared; root review and sole resource window required before run',
          'n':10000,'matrices':1,'input':str(inp),'input_sha256':input_sha,'input_bytes':FULL_BYTES,
          'fresh_prepare_input_SHA_verified':True,'fresh_prepare_input_SHA_ms':sha_ms,'prepare_resource_gate':gate,
          'frozen_files':frozen,'source_sha256':case['hashes']['source.c'],'metadata_sha256':case['hashes']['program.meta'],
          'harness_sha256':case['hashes']['oracle.c'],'oracle_EXE_sha256':case['hashes']['oracle.exe'],
          'runtime_EXE_sha256':cost['binary']['sha256'],'original_harness_include_path':str(included),
          'original_true_C_GCC_lineage':'unchanged independently compiled accepted C oracle; original GCC O2 -fno-fast-math -ffp-contract=off; full source/harness/EXE linked to accepted functional+cost manifests; no new compilation',
          'metadata_contract':{'schema':2,'symbolic_encoding':'expr_dag_v1','complete_original_PROGRAM_and_symbolic_graph':True,
                               'program_instructions':48,'optimized':'none','frontend_changed':False},
          'new_original_C_reference':str(ROOT/'NEW-triangle-oracle.bin'),
          'fixed_rejection_output':str(ROOT/'fixed-rejected.bin'),'proved_output':str(ROOT/'GNUauto-proved.bin'),
          'launch_order':['actual-original-C-oracle','GNUauto-fixed1e9-rejection','GNUauto-proved-full-output'],
          'expected_original_VM_steps':1400030009,'expected_proved_bound':2799890009,
          'fixed_limit':1000000000,'explicit_vm_step_limit':False,'expected_selected_stage':'nested',
          'expected_shared_work':24161,'shared_work_limit':250000,
          'threads':4,'scheduler':'parallel','block':32,'engine':'auto','backend_override':None,
          'full_output_bytes':FULL_BYTES,'minimum_fresh_RAM_bytes':MIN_RAM,'disk_reserve_bytes':RESERVE,
          'resource_budget_algorithm':'before each launch free_F >= ungenerated retained complete outputs *800000008 +536870912; generated files remain and are never deleted/overwritten; RAM fresh >=2684354560',
          'disk_gate_schedule':{'original_C_launch':2136870928,'fixed_rejection_launch':1336870920,
                                'proved_launch':1336870920,'after_candidate_reserve':536870912},
          'fixed_partial_output_policy':'unexpected complete or .partial is actual first failure, preserved and accounted by actual free disk; never removed by runner',
          'fresh_input_SHA_per_stage_and_gate_after_SHA':True,'C_reference_once_new_output_not_old_copy':True,
          'strict_sequential':True,'compiler_temp':str(STAGE/'compiler-temp'),
          'first_failure_exit75_for_resource_no_autorestart_or_resume':True,
          'large_Gram_decoded_portable_scope':False,'performance_claim':False,'ordinary_or_default_change':False,
          'ordinary_sha256':cost['ordinary_sha256'],'memory_sha256':cost['memory_sha256'],
          'probe_report_sha256':sha(STAGE/'analysis-only/report.json'),'design_sha256':sha(DESIGN),
          'process_environment':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']}}
    write(ROOT/'run-plan.json',plan)
    print(json.dumps({'prepared':True,'plan_sha256':sha(ROOT/'run-plan.json'),'fresh_input_sha256':input_sha,
                      'fresh_input_SHA_ms':sha_ms,'resource_gate':gate,'new_C_or_VM_executions':0,'frozen_files':len(frozen)}),flush=True)

def run():
    plan=read(ROOT/'run-plan.json');report_path=ROOT/'report.json'
    assert not report_path.exists(),'single batch: observation timeout must never restart the job'
    for relative,row in plan['frozen_files'].items():assert sha(ROOT/relative)==row['sha256']
    for relative,row in plan['frozen_files'].items():
        if relative.startswith('runner-source/'):
            assert sha(P/relative.removeprefix('runner-source/'))==row['sha256']
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    report={'schema':'optional-nested-VM-triangular-maximum-report-v1','passed':False,'status':'running',
            'plan_sha256':sha(ROOT/'run-plan.json'),'resource_gates':[],'runs':[],
            'actual_C_reference':None,'actual_fixed_rejection':None,'actual_proved_output':None,
            'ordinary_changed':False,'performance_claim':False,'explicit_limit_used':False,
            'process_environment':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']}}
    began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;write(report_path,report)
    def gate(label,remaining):
        value={'stage':label,'available_RAM_bytes':available(),'free_F_bytes':shutil.disk_usage(ROOT).free,
               'ungenerated_retained_outputs':remaining,'minimum_free_F_bytes':remaining*FULL_BYTES+RESERVE,
               'minimum_RAM_bytes':MIN_RAM}
        value['passed']=value['available_RAM_bytes']>=MIN_RAM and value['free_F_bytes']>=value['minimum_free_F_bytes']
        report['resource_gates'].append(value);save()
        if not value['passed']:
            report.update(status='resource-gate-blocked',pending=label);save();raise SystemExit(75)
        return value
    def validate(label,remaining):
        gate(label+' before SHA',remaining);checked=time.perf_counter();large_header(plan['input'])
        assert sha(plan['input'])==plan['input_sha256']
        for name,digest in [('runtime.exe',plan['runtime_EXE_sha256']),('source.c',plan['source_sha256']),
                            ('program.meta',plan['metadata_sha256']),('oracle.c',plan['harness_sha256']),
                            ('oracle.exe',plan['oracle_EXE_sha256'])]:assert sha(ROOT/name)==digest
        sha_ms=(time.perf_counter()-checked)*1000
        launch_gate=gate(label+' actual launch after SHA',remaining)
        return sha_ms,launch_gate
    def process(label,command,target,remaining):
        sha_ms,launch_gate=validate(label,remaining);assert not target.exists()and not Path(str(target)+'.partial').exists()
        stdout=ROOT/(label+'.stdout');stderr=ROOT/(label+'.stderr')
        print(json.dumps({'starting':label,'available_RAM_bytes':launch_gate['available_RAM_bytes'],
                          'free_F_bytes':launch_gate['free_F_bytes'],'explicit_step_limit':False}),flush=True)
        start=time.perf_counter();proc,resource=monitored_run(command,stdout,stderr,check=False)
        row={'stage':label,'command':command,'actual_exit_code':proc.returncode,'output':str(target),
             'output_exists':target.exists(),'output_bytes':target.stat().st_size if target.exists() else 0,
             'partial_exists':Path(str(target)+'.partial').exists(),
             'partial_bytes':Path(str(target)+'.partial').stat().st_size if Path(str(target)+'.partial').exists() else 0,
             'raw_stdout':str(stdout),'raw_stderr':str(stderr),'raw_stdout_sha256':sha(stdout),'raw_stderr_sha256':sha(stderr),
             'sha_validation_ms':sha_ms,'process_wall_ms':(time.perf_counter()-start)*1000,
             'available_RAM_before_bytes':launch_gate['available_RAM_bytes'],**resource}
        report['runs'].append(row);save()
        return proc,row
    save()
    try:
        inp=plan['input'];ref=Path(plan['new_original_C_reference'])
        proc,row=process('original-C',[str(ROOT/'oracle.exe'),inp,str(ref),str(plan['block'])],ref,2)
        assert proc.returncode==0,proc.stderr;large_header(ref)
        start=time.perf_counter();ref_sha=sha(ref);row.update(sha256=ref_sha,output_SHA_ms=(time.perf_counter()-start)*1000,
                                                           true_original_C_reference=True)
        report['actual_C_reference']=row;save();print(json.dumps({'terminal':'original-C','exit_code':0,'bytes':FULL_BYTES,'sha256':ref_sha}),flush=True)
        common=[str(ROOT/'runtime.exe'),'--metadata',str(ROOT/'program.meta'),'--input',inp,
                '--engine',plan['engine'],'--threads',str(plan['threads']),'--scheduler',plan['scheduler'],'--block-size',str(plan['block'])]
        target=Path(plan['fixed_rejection_output'])
        proc,row=process('fixed-default-rejection',common+['--output',str(target),'--vm-budget','fixed'],target,1)
        assert proc.returncode==1 and proc.stderr=='error: VM instruction limit exceeded\n'and proc.stdout==''
        assert not target.exists()and not Path(str(target)+'.partial').exists()
        row.update(expected_fixed_limit=1000000000,no_published_or_partial_output=True)
        report['actual_fixed_rejection']=row;save();print(json.dumps({'terminal':'fixed-default-rejection','actual_exit_code':1,'expected_rejection':True}),flush=True)
        target=Path(plan['proved_output'])
        proc,row=process('GNUauto-proved',common+['--output',str(target),'--vm-budget','proved'],target,1)
        assert proc.returncode==0,proc.stderr;metric=json.loads(proc.stdout);row.update(metric);save()
        assert metric['matrices']==1 and metric['selected_engine']=='vm'and metric['vm_backend']=='decoded-threaded'
        assert metric['vm_steps']==1400030009 and metric['vm_budget_mode']=='proved'
        assert metric['vm_budget_bound_peak']==metric['vm_effective_step_limit_max']==2799890009
        assert metric['vm_budget_first_proved_matrices']==0 and metric['vm_budget_first_unknown_matrices']==1
        assert metric['vm_budget_nested_attempted_matrices']==metric['vm_budget_nested_proved_matrices']==1
        assert metric['vm_budget_nested_unknown_matrices']==0 and metric['vm_budget_selected_stage_last']=='nested'
        assert metric['vm_budget_proved_matrices']==1 and metric['vm_budget_unknown_matrices']==metric['vm_budget_not_run_matrices']==0
        assert metric['vm_budget_work']==metric['vm_budget_first_work']+metric['vm_budget_nested_work']==24161
        for key in ['vm_budget_proof_ms','vm_budget_first_ms','vm_budget_nested_ms','vm_prepare_ms']:
            assert 0<=metric[key]<=metric['compute_ms']
        large_header(target);start=time.perf_counter();comparison=exact_compare(ref,target)
        assert comparison['bytes']==FULL_BYTES and comparison['sha256']==ref_sha
        row.update(comparison,whole_file_comparison_ms=(time.perf_counter()-start)*1000,
                   explicit_step_limit=False)
        report['actual_proved_output']=row
        free=shutil.disk_usage(ROOT).free;report['after_candidate_disk_reserve']={'free_F_bytes':free,'minimum_free_F_bytes':RESERVE,'passed':free>=RESERVE}
        assert free>=RESERVE
        report.update(passed=True,status='complete',optin_proved_full_originalC_passed=True,
                      ordinary_fixed_default_full_shape_passed=False,original_C_executions=1,VM_executions=2)
        save();print(json.dumps({'passed':True,'fullbytes':FULL_BYTES,'report_sha256':sha(report_path),'ordinary_changed':False}),flush=True)
    except BaseException as error:
        if report['status']!='resource-gate-blocked':report.update(status='first-failure',failure=str(error))
        save();raise

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true');group.add_argument('--run',action='store_true');args=parser.parse_args()
    temp=STAGE/'compiler-temp';temp.mkdir(exist_ok=True);os.environ.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
    if args.prepare:prepare()
    else:run()

if __name__=='__main__':main()
