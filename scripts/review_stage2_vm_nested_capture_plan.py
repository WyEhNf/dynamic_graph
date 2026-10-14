"""Root review of file-stdio correction; preserve actual failed first compile."""
import difflib
import json
import time
from review_stage2_vm_nested_component_plan import ROOT,P,D,read,sha

def main():
    c=D/'capture-supplement';plan=read(c/'plan.json');old=read(D/'accounting-supplement/plan.json')
    assert sha(c/'plan.json')=='a853c83a17aef8f77617d6a06f468bc86573ddc4556e95ee7dd4c0ce6e367059'
    assert plan['accounting_plan_sha256']==sha(D/'accounting-supplement/plan.json')
    for name,digest in plan['retained_immutable_source_sha256'].items():assert sha(D/name)==digest
    for name,digest in plan['capture_source_sha256'].items():assert sha(c/name)==digest
    for name,digest in plan['failed_attempt_files_sha256'].items():assert sha(c/'failed-attempt'/name)==sha(D/'component-gate'/name)==digest
    for key in ('ABI','compile_flags','golden_plan','work_limit','compiler','future_compile_environment'):
        assert plan[key]==old[key]
    assert plan['compile_command'][:-1]==old['compile_command'][:-1]
    assert plan['compile_command'][-1]==old['compile_command'][-1].replace('component-gate','component-gate-capture')
    previous=(D/'component-gate/source/tools/windows_resource_probe.py').read_text()
    after=(c/'source/tools/windows_file_resource_probe_stage2.py').read_text()
    diff=list(difflib.unified_diff(previous.splitlines(True),after.splitlines(True),fromfile='previous-resource-probe',tofile='capture-resource-probe'))
    assert ''.join(diff)==(c/'resource-probe.diff').read_text()
    assert len([line for line in diff if line.startswith('@@')])==4
    assert 'stdout=out_file,stderr=err_file' in after and 'subprocess.PIPE' not in after
    failed=read(c/'failed-attempt/report.json')
    assert failed['actual_exit_code']==4294967295 and failed['status']=='compile-failed' and len(failed['runs'])==1
    assert plan['failed_attempt_actual_tool_session']==71641 and plan['failed_attempt_tool_exit_code']==1
    assert not any(plan[k] for k in ('candidate_changed','ABI_changed','gold_or_algorithm_changed','default_changed','compiler_started','VM_started','large_input_started'))
    result=dict(passed=True,reviewed_unix=time.time(),capture_plan_sha256=sha(c/'plan.json'),retained_source_files=len(plan['retained_immutable_source_sha256']),
        first_compile_tool_session=71641,first_compile_tool_exit=1,first_compile_process_exit=4294967295,
        original_VM_test_executions=0,second_attempt_executions=0,
        scope='Only file stdout/stderr capture replaces undrained PIPE. Original resource method/gates/candidate/gold/ABI/flags retained; sole command change output filename. First owned compiler blocked and was controlled-terminated; saved stderr is only bytes written before termination, not natural complete diagnostics. Authorizes second isolated compile/small tests, no Runtime/largeN/default/performance.')
    (ROOT/'outputs/stage2-root-vm-nested-capture-plan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
