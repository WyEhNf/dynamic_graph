"""Audit runner-only continuation against immutable first-failure evidence."""
import difflib,json,time
from pathlib import Path
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,read,sha

def main():
    r=D/'runtime-integration'; s=r/'continuation-supplement'; m=read(s/'manifest.json'); failed=read(r/'functional-evidence/report.json')
    assert sha(s/'manifest.json')=='26c41d04eebb229629319749bde62e0f1853751fc0e7d86d6d3d7520c7f392b5'
    assert sha(r/'functional-evidence/report.json')==m['failed_report_sha256']=='35047176376fd9cb1b85b89f79883920e183a6c6a4c8cbe67fb603ea0acabdc7'
    assert sha(r/'implementation-freeze/manifest.json')==m['initial_implementation_manifest_sha256']
    old=P/'tools/run_vm_nested_runtime_stage2.py'; new=P/'tools/run_vm_nested_runtime_continuation_stage2.py'
    assert sha(old)==m['initial_runner_sha256'] and sha(new)==m['runner_sha256']
    diff=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='initial-runner',tofile='continuation-runner'))
    saved=(s/'runner.diff').read_text();assert diff.splitlines()[2:]==saved.splitlines()[2:] and sha(s/'runner.diff')==m['runner_diff_sha256']
    for path,digest in m['cached_source_input_meta_reference_output_raw_actual_sha256'].items():assert sha(path)==digest
    cache={(x['source'],x['family'],x['mode'],x['scope']):x for x in failed['functional']};assert len(cache)==586
    declared=m['cached_rows'] if 'cached_rows'in m else next(v for k,v in m.items()if isinstance(v,list)and len(v)==586)
    assert {tuple(x['identity'])for x in declared}==set(cache)
    for row in declared:
        actual=cache[tuple(row['identity'])];assert row['output']==actual['output'] and row['output_sha256']==sha(actual['output'])
        assert row['reference_sha256']==sha(actual['reference']) and row['runtime_exit_code']==0
    assert (m['reused_whole_C'],m['pending_whole_C'],m['final_unique_whole_C'],m['pending_errors'],m['pending_CLI'])==(586,38,624,56,10)
    assert m['new_actual_C_reference_executions']==5 and not m['new_execution_started'] and not m['mirror_Runtime_C_Metadata_flags_or_gold_modified']
    text=new.read_text();assert "if metric['vm_budget_mode']!='fixed'and metric['selected_engine']=='vm':"in text
    assert "if metric['vm_budget_mode']=='fixed' or metric['selected_engine']!='vm':"in text
    assert "assert metric['vm_budget_mode']==flags[flags.index('--vm-budget')+1]"in text
    assert "assert used_cache==set(cache)and len(report['reused_runs'])==586"in text
    assert "choices=['functional']"in text and "out=R/'functional-evidence-continuation';out.mkdir(exist_ok=False)"in text
    assert not Path(m['new_evidence_directory']).exists()
    for config in read(r/'implementation-freeze/manifest.json')['builds']:assert sha(r/config['build']/'cholesky_runtime.exe')==m['runtime_sha256'][config['label']]
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(s/'manifest.json'),runner_sha256=sha(new),verified_cached_C=586,planned_missing_C=38,planned_errors=56,planned_CLI=10,new_C_oracles=5,authorization='One actual frozen continuation only, preserve terminal result. If all624/56/10 completed then independent root full-byte audit and fullCTest/UBSan; ordinary/default unchanged.',scope='Root reviewed complete runner diff and cached original source/meta/input/reference/output/raw lineage; only classification uses actual emitted budget mode. Reuse586 actual observations, execute38 missing identities. First terminal exit1 immutable; no Runtime/C/Metadata/gold changes or fabricated completed rows.')
    (ROOT/'outputs/stage2-root-vm-nested-continuation-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
