"""Seal completed functional evidence without executing any contracts again."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'artifacts/stage2-vm-nested-budget/runtime-integration';A=R/'acceptance'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as s:
        for part in iter(lambda:s.read(1048576),b''):h.update(part)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main():
    assert not A.exists();frozen=read(R/'implementation-freeze/manifest.json');continuation=read(R/'continuation-supplement/manifest.json');reports={name:read(R/name/'report.json')for name in ['build-evidence','contracts-evidence','functional-evidence','functional-evidence-continuation','ctest-evidence','ubsan-evidence']}
    assert not reports['functional-evidence']['passed']and all(reports[n]['passed']for n in reports if n!='functional-evidence')
    functional=reports['functional-evidence-continuation'];assert len(functional['functional'])==624 and len(functional['errors'])==56 and len(functional['cli'])==10 and len(functional['reused_runs'])==586
    assert sha(R/'functional-evidence/report.json')==continuation['failed_report_sha256']and sha(P/'tools/run_vm_nested_runtime_stage2.py')==frozen['runner_sha256']and sha(P/'tools/run_vm_nested_runtime_continuation_stage2.py')==continuation['runner_sha256']
    ordinary=sha(P/'build/cholesky_runtime.exe');memory=sha(P/'build-memory/cholesky_runtime.exe');assert ordinary==frozen['ordinary_sha256']and memory==frozen['memory_sha256'];assert sha(P/'src/vm_step_bound.cpp')==frozen['working_original_proof_CPP_sha256']
    A.mkdir();files={}
    def copy(path,relative,expected=None):
        path=Path(path);actual=sha(path)
        if expected:assert actual==expected,(path,actual,expected)
        target=A/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);assert sha(target)==actual;files[relative.as_posix()]={'sha256':actual,'bytes':target.stat().st_size,'origin':str(path)}
    for rel,digest in frozen['mirror_source_sha256'].items():copy(R/'workspace'/rel,Path('source')/rel,digest)
    for name in ['run_vm_nested_runtime_stage2.py','run_vm_nested_runtime_continuation_stage2.py','windows_file_resource_probe_stage2.py','freeze_vm_nested_runtime_acceptance_stage2.py','prepare_vm_nested_runtime_continuation_stage2.py','diagnose_vm_nested_functional_failure_stage2.py']:
        copy(P/'tools'/name,Path('control-source/tools')/name)
    for directory in ['initial-plan','contract-supplement','implementation-freeze','continuation-supplement']:
        copy(R/directory/('plan.json'if directory in ['initial-plan','contract-supplement']else'manifest.json'),Path('lineage')/(directory+'.json'))
    copy(R/'functional-first-failure/diagnosis.json',Path('lineage/first-failure-diagnosis.json'))
    for directory in reports:
        copy(R/directory/'report.json',Path('evidence')/directory/'report.json')
        for raw in sorted((R/directory).glob('*.stdout'))+sorted((R/directory).glob('*.stderr')):copy(raw,Path('evidence')/directory/raw.name)
    build=reports['build-evidence'];matching_builds={}
    for label,entry in build['build_inventory'].items():
        assert entry['matching_runtime_header_sha256']==sha(R/'workspace/include/cholesky/runtime.hpp');inventory={}
        for rel,item in entry['artifacts'].items():
            copy(item['path'],Path('builds')/label/rel,item['sha256']);inventory[rel]=files[(Path('builds')/label/rel).as_posix()]
        matching_builds[label]={'same_matching_new_header_SHA':entry['matching_runtime_header_sha256'],'artifacts':inventory}
    for path in sorted((R/'ubsan-evidence').glob('*')):
        if path.suffix in ['.exe','.cmd']:copy(path,Path('ubsan')/path.name)
    fresh=[]
    for row in functional['sources']:
        if 'actual_folder'not in row:continue
        folder=Path(row['actual_folder']);label=row['label'];record={'label':label,'source_folder':str(folder),'files':{}}
        for path in [folder/'source.c',folder/'program.meta',folder/'program.analysis.json',folder/'oracle.c',folder/'oracle.exe',Path(row['analysis']['ir'])]:
            relative=Path('actual-C')/label/path.name;copy(path,relative);record['files'][path.name]=files[relative.as_posix()]
        fresh.append(record)
    assert len(fresh)==6
    outputs=[{k:row[k]for k in ['source','family','mode','scope','output','reference','metadata','input','sha256','bytes','metadata_sha256','input_sha256','reference_sha256','raw_stdout','raw_stderr','reused_actual_execution']}for row in functional['functional']]
    # Do not claim another oracle run or silently rewrite initial evidence; root independently
    # streamed all624 in its acceptance. The index seals the original actual SHA/byte records.
    (A/'output-index.json').write_text(json.dumps(outputs,indent=2),encoding='utf-8')
    fresh_auto=[r for r in functional['functional']if r['mode']=='proved-auto'and r['source']in [s['label']for s in fresh]]
    summary={'schema':'optional-nested-VM-runtime-acceptance-summary-v1','passed':True,'optional_only':True,'same_frozen_candidate_runtime':True,'main_whole_C':557,'compat_whole_C':67,'all_whole_C':624,'total_output_bytes':sum(r['bytes']for r in functional['functional']),'reused_initial_whole_C':586,'new_continuation_whole_C':38,'original_first_failed_owner_exit':1,'first_failure_is_runner_classification':True,'runtime_or_C_source_not_fixed':True,'all_exact_error_checks':56,'main_errors':49,'all_CLI':10,'main_CLI':9,'selection_observations':190,'residual_auxiliary_checks':15,'fixed_boundary_executions':60,'full_ctest_expected':{'gnu-nested':17,'portable-nested':13,'proved-only-compat':12,'disabled':10},'new_component_denominators':{'gold':1081,'step_boundaries':2162,'single_position_mutants':16320,'proved_mutants':872,'original_legacy_VM_executions':4995},'UBSan_old_and_derived_threaded_contracts':934,'UBSan_selection_observations':60,'fresh_auto':[{k:r[k]for k in ['source','family','matrices','selected_engine','vm_budget_first_proved_matrices','vm_budget_first_unknown_matrices','vm_budget_nested_attempted_matrices','vm_budget_nested_proved_matrices','vm_budget_unknown_matrices','vm_budget_not_run_matrices','vm_budget_bound_peak','vm_steps','vm_budget_work']}for r in fresh_auto],'analysis_within_compute':True,'shared_work_limit_per_matrix':250000,'new_source_oracle_compiles':6,'new_actual_C_references':12,'native_math_AUTO_unchanged':True,'ordinary_runtime_sha256':ordinary,'memory_runtime_sha256':memory,'default_fixed_budget':1000000000,'default_nested_or_proved_promoted':False,'new_N10000_execution':False,'performance_benefit_established':False,'next_stage':'separate static same-binary fixed/proved cost and highN proof/step/resource design; do not equate larger finite cap with faster compute'}
    (A/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    manifest={'schema':'optional-nested-VM-runtime-acceptance-manifest-v1','passed':True,'frozen_files':files,'mirror_source_count':len(frozen['mirror_source_sha256']),'matching_four_new_ABI_builds':matching_builds,'new_actual_C_source_lineage':fresh,'original_first_proof_source_sha256':sha(P/'src/vm_step_bound.cpp'),'nested_component_source_sha256':sha(R/'workspace/src/vm_nested_step_bound.cpp'),'output_index_sha256':sha(A/'output-index.json'),'summary_sha256':sha(A/'summary.json'),'ordinary_sha256':ordinary,'memory_sha256':memory,'owner_actual_tool_terminals':{'build':{'session':77532,'exit':0},'contracts':{'session':73341,'exit':0},'initial-functional':{'session':23349,'exit':1},'continuation-functional':{'session':35094,'exit':0},'full-ctest':{'session':54712,'exit':0},'UBSan':{'session':40337,'exit':0}},'root_624_functional_audit':str(P.parents[1]/'outputs/stage2-root-vm-nested-runtime-functional.json'),'root_final_CTest_UBSan_audit_pending':True,'all_624_whole_output_and_RAW_paths_preserved':True,'performance_or_maximum_or_ordinary_install_started':False}
    (A/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'frozen':True,'manifest_sha256':sha(A/'manifest.json'),'summary_sha256':sha(A/'summary.json'),'source_files':178,'whole_C':624,'no_extra_test_execution':True}))
if __name__=='__main__':main()
