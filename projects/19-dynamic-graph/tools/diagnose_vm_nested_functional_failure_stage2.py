"""Freeze the observed runner assertion failure; no candidate or test changes."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'artifacts/stage2-vm-nested-budget/runtime-integration'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=R/'functional-first-failure';assert not out.exists();old=R/'functional-evidence';report=json.loads((old/'report.json').read_text(encoding='utf-8'));last=report['functional'][-1];process=report['runs'][-1]
    assert not report['passed'] and len(report['functional'])==586 and len(report['errors'])==len(report['cli'])==0
    assert last['mode']=='forced-VM-fixed'and last['vm_budget_mode']=='fixed'and last['byte_identical']and process['exit_code']==0 and last['vm_budget_first_proved_matrices']==last['vm_budget_first_unknown_matrices']==last['vm_budget_work']==0
    out.mkdir();shutil.copyfile(old/'report.json',out/'report.json');shutil.copyfile(P/'tools/run_vm_nested_runtime_stage2.py',out/'runner.py')
    raw={}
    for suffix in ['stdout','stderr']:
        source=old/(process['label']+'.'+suffix);shutil.copyfile(source,out/source.name);raw[source.name]=sha(out/source.name)
    record={'schema':'optional-nested-VM-runtime-first-functional-failure-v1','observed_owner_session':23349,'observed_owner_terminal_exit_code':1,'last_runtime_exit_code':0,'first_failed_assertion':'runner mode!=fixed-auto incorrectly classifies forced-VM-fixed as proved and requires first proved+unknown counts==matrices','frozen_initial_runner_sha256':sha(out/'runner.py'),'failed_report_sha256':sha(out/'report.json'),'last_raw_sha256':raw,'whole_C_completed_and_byte_identical':586,'whole_C_pending':38,'old_C_compat_total_completed':536,'fresh_three_positive_matrices':30,'last_actual_VM_steps':last['vm_steps'],'last_actual_whole_C_bytes':last['bytes'],'last_actual_output_sha256':last['sha256'],'error_groups_started':False,'CLI_started':False,'candidate_or_C_source_or_assertions_modified':False,'ordinary_runtime_sha256':sha(P/'build/cholesky_runtime.exe'),'memory_runtime_sha256':sha(P/'build-memory/cholesky_runtime.exe'),'new_compile_or_VM_execution_started':False,'diagnosis':'Expected fixed no-analysis metrics are correct; only runner mode-label classification is incorrect. Proposed repair classifies from actual --vm-budget flag and verifies emitted vm_budget_mode equality. Frozen source/denominator unchanged; continuation must preserve first failed report and reuse passed records/oracles without reexecution.'}
    (out/'diagnosis.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'diagnosis_sha256':sha(out/'diagnosis.json'),'failed_report_sha256':sha(out/'report.json'),'completed':586,'new_VM_or_compile':False}))
if __name__=='__main__':main()
