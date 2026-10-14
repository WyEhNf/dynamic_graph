"""Preserve and independently classify the initial functional runner failure."""
import json,time
from pathlib import Path
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,read,sha

def main():
    out=D/'runtime-integration/functional-evidence'; r=read(out/'report.json')
    assert sha(out/'report.json')=='35047176376fd9cb1b85b89f79883920e183a6c6a4c8cbe67fb603ea0acabdc7'
    assert not r['passed'] and len(r['functional'])==586 and not r['errors'] and not r['cli']
    for row in r['functional']:
        for key in ['metadata','input','reference']:assert sha(row[key])==row[key+'_sha256']
        assert sha(row['output'])==sha(row['reference'])==row['sha256']
        with Path(row['output']).open('rb')as a,Path(row['reference']).open('rb')as b:
            while True:
                x=a.read(1048576);y=b.read(1048576);assert x==y
                if not x:break
    for row in r['runs']:
        assert row['exit_code']==0
        for stream in ['stdout','stderr']:assert sha(out/(row['label']+'.'+stream))==row[stream+'_sha256']
    failed=r['functional'][-1]; assert failed['mode']=='forced-VM-fixed' and failed['vm_budget_mode']=='fixed'
    assert failed['vm_budget_work']==failed['vm_budget_proof_ms']==failed['vm_budget_first_proved_matrices']==failed['vm_budget_first_unknown_matrices']==0
    assert failed['bytes']==31040 and failed['vm_steps']==985573
    runner=(P/'tools/run_vm_nested_runtime_stage2.py').read_text()
    assert "if mode!='fixed-auto'and metric['selected_engine']=='vm':" in runner
    assert "if mode=='fixed-auto' or metric['selected_engine']!='vm':" in runner
    f=read(D/'runtime-integration/implementation-freeze/manifest.json')
    for name,digest in f['mirror_source_sha256'].items():assert sha(D/'runtime-integration/workspace'/name)==digest
    result=dict(passed=True,reviewed_unix=time.time(),failed_report_sha256=sha(out/'report.json'),functional_batch_passed=False,independently_verified_partial_C_outputs=586,pending_C_outputs=38,pending_errors=56,pending_CLI=10,failed_classification='forced-VM-fixed passed actual fixed runtime and original C bytes, but runner treats any mode other than fixed-auto as proved',runtime_changes=False,scope='Audit of first actual terminal exit1 only. All586 completed outputs independently byte-verified; failed fixed row uses zero proof work and actual CLI fixed. Remaining38C/56errors/10CLI plus fullCTest/UBSan are unexecuted, not accepted. Freeze/raw evidence retained; only runner classification/resume supplement authorized.')
    (ROOT/'outputs/stage2-root-vm-nested-runtime-first-failure.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
