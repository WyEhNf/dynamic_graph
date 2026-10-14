"""Independently verify every actual whole-C file and frozen integration lineage."""
import json,time
from pathlib import Path
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,sha,read
from review_stage2_vm_proved_integration import header

def main():
    base=D/'runtime-integration'; out=base/'functional-evidence-continuation'; r=read(out/'report.json'); f=read(base/'implementation-freeze/manifest.json'); plan=read(base/'initial-plan/plan.json')
    initial=read(base/'functional-evidence/report.json');supplement=read(base/'continuation-supplement/manifest.json')
    assert sha(base/'functional-evidence/report.json')==r['initial_failed_report_sha256']==supplement['failed_report_sha256']
    assert sha(base/'continuation-supplement/manifest.json')==r['continuation_manifest_sha256']
    cached={(x['source'],x['family'],x['mode'],x['scope'])for x in initial['functional']}
    actual={(x['source'],x['family'],x['mode'],x['scope'])for x in r['functional']}
    reused={(x['source'],x['family'],x['mode'],x['scope'])for x in r['functional']if x['reused_actual_execution']}
    assert len(actual)==624 and reused==cached and len(reused)==len(r['reused_runs'])==586
    assert sum(not x['reused_actual_execution']for x in r['functional'])==38
    assert r['passed'] and len(r['functional'])==r['all_whole_C']==624
    assert len(r['errors'])==r['all_errors']==56 and len(r['cli'])==r['all_CLI']==10
    assert r['main_whole_C']==557 and r['separate_compat_whole_C']==67
    for name,digest in f['mirror_source_sha256'].items():assert sha(base/'workspace'/name)==digest
    for label,digest in r['binary_sha256'].items():
        build=next(b for b in f['builds']if b['label']==label);assert sha(base/build['build']/'cholesky_runtime.exe')==digest
    total_bytes=0; shapes=set(); sources=set(); fresh={s['label']:s for s in plan['fresh_C_sources']}
    for row in r['functional']:
        for key in ['metadata','input','reference']:assert sha(row[key])==row[key+'_sha256']
        reference=Path(row['reference']); output=Path(row['output']);assert reference.stat().st_size==output.stat().st_size==row['bytes']
        # Stream exact original C FP64 bytes, including signed zeros and headers.
        with reference.open('rb')as a,output.open('rb')as b:
            while True:
                x=a.read(1024*1024);y=b.read(1024*1024);assert x==y
                if not x:break
        assert sha(output)==row['sha256']==row['reference_sha256']
        metric=json.loads(Path(row['raw_stdout']).read_text());assert Path(row['raw_stderr']).read_text()==''
        for key,value in metric.items():assert row[key]==value
        assert row['vm_budget_mode']==row['command'][row['command'].index('--vm-budget')+1]
        ns=header(output);assert len(ns)==row['matrices'];shapes.update(ns);sources.add(row['source']);total_bytes+=row['bytes']
        if row['selected_engine']=='vm' and row['vm_budget_mode']=='proved':
            assert row['vm_budget_work']==row['vm_budget_first_work']+row['vm_budget_nested_work']<=250000*row['matrices']
            assert row['vm_budget_first_proved_matrices']+row['vm_budget_first_unknown_matrices']==row['matrices']
        else:assert row['vm_budget_work']==0 and row['vm_budget_nested_attempted_matrices']==0
        if row['mode']=='proved-auto' and row['source']in fresh:
            label=row['source']
            if label.startswith('unknown-'):assert row['vm_budget_unknown_matrices']==5 and row['vm_effective_step_limit_max']==1000000000
            elif label=='strict-cholesky-control':assert row['selected_engine']!='vm' and row['vm_budget_not_run_matrices']==5
            else:assert row['vm_budget_first_unknown_matrices']==5 and row['vm_budget_nested_proved_matrices']==5
    old=read(P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json')
    for row in r['errors']:
        reference=next(x for x in old['failures']if x['source']==row['source']);assert row['exit_code']==1 and row['stderr']==reference['results'][0]['stderr']
        target=Path(row['target']);assert not target.exists() and not Path(str(target)+'.partial').exists()
        assert sha(row['metadata'])==row['metadata_sha256']and sha(row['input'])==row['input_sha256']
        assert Path(row['raw_stderr']).read_text()==row['stderr'] and Path(row['raw_stdout']).read_text()==row['stdout']
    for phase,runs in [(out,r['runs']),(base/'functional-evidence',initial['runs'])]:
      for row in runs:
        assert row['exit_code']==(1 if row['label'].startswith('error-') else next((x['exit_code']for i,x in enumerate(old['cli'])if row['label']=='CLI-'+str(i)),0))
        for stream in ['stdout','stderr']:assert sha(phase/(row['label']+'.'+stream))==row[stream+'_sha256']
    for index,row in enumerate(r['cli']):
        ref=old['cli'][index]if index<9 else next(x for x in old['cli']if x['flags']==['--help']and 'disabled'not in x['exe'])
        assert row['stdout']==ref['stdout'] and row['stderr']==ref['stderr'] and row['flags']==ref['flags']
        assert Path(row['raw_stdout']).read_text()==row['stdout'] and Path(row['raw_stderr']).read_text()==row['stderr']
    for source in r['sources']:
        if source['label']not in fresh:continue
        folder=Path(source['actual_folder']);assert sha(source['path'])==source['sha256']==fresh[source['label']]['sha256']
        for key,name in [('metadata_sha256','program.meta'),('analysis_sha256','program.analysis.json'),('harness_sha256','oracle.c')]:assert sha(folder/name)==source[key]
        compile_row=next(x for x in [*initial['runs'],*r['runs']]if x['label']==source['label']+'-oracle-compile');assert '-fno-fast-math'in compile_row['command'] and '-ffp-contract=off'in compile_row['command']
    assert sha(P/'build/cholesky_runtime.exe')==f['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==f['memory_sha256']
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(out/'report.json'),first_failure_report_sha256=r['initial_failed_report_sha256'],whole_C_outputs=624,reused_original_C=586,new_actual_C=38,main_C=557,separate_compat_C=67,errors=56,CLI=10,source_count=len(sources),shapes=sorted(shapes),independent_streamed_output_bytes=total_bytes,scope='All624 actual FP64 C reference/output files streamed byte-for-byte with source/input/metadata/rawmetric lineage and matrix headers;586 actual prior executions reused,38 missing identities newly executed, first terminal failure retained.56 original errors and10 CLI independently compared. Fresh nested/native/unknown source behavior and shared250k work checks accepted. General C, maximum-size nested runtime and performance remain unproved; ordinary/default unchanged.')
    (ROOT/'outputs/stage2-root-vm-nested-runtime-functional.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
