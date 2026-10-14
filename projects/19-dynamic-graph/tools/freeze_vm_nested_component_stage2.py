"""Freeze two compiler attempts and one passed isolated original-VM gate."""
import hashlib,json,shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
INITIAL=STAGE/'initial-freeze';ACCOUNT=STAGE/'accounting-supplement';CAPTURE=STAGE/'capture-supplement'
FIRST=STAGE/'component-gate';GATE=STAGE/'component-gate-capture';OUT=STAGE/'component-acceptance'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    initial=read(INITIAL/'plan.json');account=read(ACCOUNT/'plan.json');capture=read(CAPTURE/'plan.json');first=read(FIRST/'report.json');passed=read(GATE/'report.json')
    assert sha(GATE/'report.json')=='36bc0c86837beddc57dc9d8c330c6c652a2c809841992f7e15911fa302c52ba8'
    assert passed['passed'] and passed['actual_exit_code']==0 and passed['status']=='complete'
    assert len(first['runs'])==1 and first['actual_exit_code']==4294967295 and not first['passed']
    assert len(passed['runs'])==2 and all(row['actual_exit_code']==0 for row in passed['runs'])
    assert sha(P/'build/cholesky_runtime.exe')==passed['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==passed['memory_sha256']
    assert sha(P/'src/vm_step_bound.cpp')=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    assert passed['initial_plan_sha256']==sha(INITIAL/'plan.json') and passed['accounting_supplement_sha256']==sha(ACCOUNT/'plan.json') and passed['capture_plan_sha256']==sha(CAPTURE/'plan.json')
    for name,row in initial['frozen_files'].items():assert sha(INITIAL/name)==row['sha256']
    for name,row in account['candidate_files'].items():assert sha(ACCOUNT/name)==row['sha256']
    for name,digest in capture['capture_source_sha256'].items():assert sha(CAPTURE/name)==digest
    OUT.mkdir(exist_ok=False);files={}
    def copy(source,relative,expected=None):
        if expected:assert sha(source)==expected
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        files[relative.as_posix()]={'sha256':sha(target),'origin':str(source),'bytes':target.stat().st_size}
    for name,row in account['candidate_files'].items():copy(ACCOUNT/name,Path('source')/Path(name).relative_to('candidate-source'),row['sha256'])
    for name,digest in capture['capture_source_sha256'].items():copy(CAPTURE/name,Path(name),digest)
    copy(Path(__file__),Path('source/tools')/Path(__file__).name)
    for label,folder in [('initial',INITIAL),('accounting',ACCOUNT),('capture',CAPTURE)]:copy(folder/'plan.json',Path('plans')/(label+'.json'))
    for label,folder in [('compile-attempt-1',FIRST),('compile-attempt-2-and-contracts',GATE)]:
        for source in sorted(folder.iterdir()):
            if source.is_file()and source.suffix in ['.json','.stdout','.stderr']:copy(source,Path('evidence')/label/source.name)
    exe=Path(capture['compile_command'][-1]);copy(exe,Path('vm-nested-bound-tests.exe'),passed['EXE_sha256'])
    stats=passed['contract_stats'];assert stats['original_VM_executions']==3*1081+2*4+2*stats['proved_mutations']==4995
    assert stats['rectangular_goldens']==576 and stats['triangular_goldens']==217 and stats['three_level_goldens']==288 and stats['single_position_mutations']==16320
    summary={'scope':'isolated nested counted-loop proof component, no runtime integration/default or performance claim','component_gates_actual_passed':True,'root_final_acceptance_not_claimed':True,'compile_attempts':2,'first_compile':'controlled termination for undrained stderr PIPE; actual4294967295/tool1, diagnostic only written bytes','second_compile':'natural terminal0 using direct raw-file output, unchanged candidate/flags/gold/ABI','one_original_VM_contract_batch':True,'stats':stats,'compiles':first['runs']+passed['runs'][:1],'contracts':passed['runs'][1],'all_resource_gates':first['resource_gates']+passed['resource_gates'],'ordinary_sha256':passed['ordinary_sha256'],'memory_sha256':passed['memory_sha256'],'default':'ordinary99a fixed1e9/proofOFF remains unchanged','no_new_true_C_reference':True,'all_VM_inputs_N':3,'all_VM_matrix_values':9,'runtime_integrated':False,'large_shape_or_performance_started':False,'remaining_limits':['only canonical positive-increment Lt int32/exact-FP64 loops','unknown for shared/irreducible loops, side entries or uncertain initialization/effects/ranges','conservative maximum across parent-IV interval may overestimate triangular work','charged dominator matrix and work250000 can reject larger otherwise finite PROGRAMs','no real-C nested-source or N10000 integration gate has run']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    manifest={'schema':'isolated-nested-VM-component-acceptance-v1','passed':True,'files':files,'summary_sha256':sha(OUT/'summary.json'),'initial_plan_sha256':sha(INITIAL/'plan.json'),'accounting_plan_sha256':sha(ACCOUNT/'plan.json'),'capture_plan_sha256':sha(CAPTURE/'plan.json'),'passed_execution_report_sha256':sha(GATE/'report.json'),'EXE_sha256':passed['EXE_sha256'],'complete_immutable_dependencies':str(INITIAL/'dependencies'),'dependencies_sha256':{name:row['sha256']for name,row in initial['frozen_files'].items()if name.startswith('dependencies/')},'ABI':account['ABI'],'compiler':capture['compiler'],'compile_flags':capture['compile_flags'],'compile_command':capture['compile_command'],'charge_table':account['charge_table'],'stats':stats,'compile_attempts':2,'actual_contract_batches':1,'root_review_status':'pending independent final audit','current_core_source_unchanged':True,'ordinary_sha256':passed['ordinary_sha256'],'memory_sha256':passed['memory_sha256'],'newRuntime_or_default_changed':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'manifest_sha256':sha(OUT/'manifest.json'),'summary_sha256':sha(OUT/'summary.json'),'EXE_sha256':passed['EXE_sha256'],'frozen_files':len(files),'compilation_attempts':2,'actual_VM_contract_batches':1,'no_new_execution':True}))

if __name__=='__main__':main()
