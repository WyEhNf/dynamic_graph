"""Static continuation supplement; never execute a Runtime or retry first row."""
import difflib,hashlib,json,shutil
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
OLD=R/'performance-plan';NEW=R/'performance-continuation-plan'
FAILED=R/'performance-evidence'
OLD_PLAN_SHA='04d73f41e492f90033bf600470f5d724868ab639765a8a1e44abb6fb29811907'
FAILED_REPORT_SHA='070392af398496ac4884a7889bf0b65017c1d4231a6387dc986a30d8e7b06804'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    assert sha(OLD/'plan.json')==OLD_PLAN_SHA and sha(FAILED/'report.json')==FAILED_REPORT_SHA
    previous=read(OLD/'plan.json');failed=read(FAILED/'report.json')
    assert not failed['passed']and len(failed['records'])==1
    first=failed['records'][0];assert first['actual_exitcode']==0
    assert {k:first[k]for k in ['identity','round','backend']}==previous['schedule'][0]
    assert first['metric']['vm_steps']==first['case']['expected_vm_steps']
    assert first['metric']['vm_budget_not_run_matrices']==0
    assert not NEW.exists();shutil.copytree(OLD,NEW)
    original=(OLD/'runner.py').read_text();candidate=original
    candidate=candidate.replace("PLAN=R/'performance-plan'","PLAN=R/'performance-continuation-plan'")
    candidate=candidate.replace("OUT=R/'performance-evidence'","OUT=R/'performance-continuation-evidence'")
    before="    assert metric['vm_budget_not_run_matrices']==case['matrices']"
    after="    expected_not_run=case['matrices']if case['default_path_scope']=='native-control'else 0\n    assert metric['vm_budget_not_run_matrices']==expected_not_run"
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="            report['pairs'].append({'identity':case['identity'],'round':round_index,'scope':case['default_path_scope'],\n                                   'compute_ratio_fused_over_plain':ratio,'process_wall_ratio_fused_over_plain':wall_ratio,'outcome':outcome})"
    after="""            interrupted=case['identity']==plan['interrupted_pair']['identity']and round_index==plan['interrupted_pair']['round']
            report['pairs'].append({'identity':case['identity'],'round':round_index,'scope':case['default_path_scope'],
                                   'compute_ratio_fused_over_plain':ratio,'process_wall_ratio_fused_over_plain':wall_ratio,'outcome':outcome,
                                   'interrupted_noncontiguous':interrupted,
                                   'timing_comparison_scope':'planned noncontiguous diagnostic only'if interrupted else'continuous alternating pair'})"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="                                  'wins':sum(x<1 for x in ratios),'negative':sum(x>1 for x in ratios),'ties':sum(x==1 for x in ratios)})"
    after="""                                  'wins':sum(x<1 for x in ratios),'negative':sum(x>1 for x in ratios),'ties':sum(x==1 for x in ratios),
                                  'interrupted_rounds':[p['round']for p in report['pairs']if p['identity']==case['identity']and p['interrupted_noncontiguous']],
                                  'continuous_compute_ratios':[p['compute_ratio_fused_over_plain']for p in report['pairs']if p['identity']==case['identity']and not p['interrupted_noncontiguous']],
                                  'continuous_median_paired_compute_ratio':statistics.median(p['compute_ratio_fused_over_plain']for p in report['pairs']if p['identity']==case['identity']and not p['interrupted_noncontiguous'])})"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="                                      'negative':sum(p['outcome']=='negative'for p in pairs),'ties':sum(p['outcome']=='tie'for p in pairs)}"
    after="""                                      'negative':sum(p['outcome']=='negative'for p in pairs),'ties':sum(p['outcome']=='tie'for p in pairs)}
    report['comparison_groups']={}
    for name,pairs in [('all95_planned',report['pairs']),('continuous94',[p for p in report['pairs']if not p['interrupted_noncontiguous']])]:
        expected=95 if name=='all95_planned'else 94;assert len(pairs)==expected
        report['comparison_groups'][name]={'pairs':len(pairs),'wins':sum(p['outcome']=='win'for p in pairs),
                                         'negative':sum(p['outcome']=='negative'for p in pairs),'ties':sum(p['outcome']=='tie'for p in pairs),
                                         'VM_pairs':sum(p['scope']=='genuine-default-VM'for p in pairs),
                                         'native_pairs':sum(p['scope']=='native-control'for p in pairs)}
    assert report['comparison_groups']['continuous94']['VM_pairs']==89
    assert report['comparison_groups']['continuous94']['native_pairs']==5"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="            'resource_gate_observations':[],'cohort_counts':{},'observer_used':False,'runtime_or_default_changed':False}"
    after="""            'resource_gate_observations':[],'cohort_counts':{},'observer_used':False,'runtime_or_default_changed':False,
            'original_first_failure_plan_sha256':plan['original_first_failure_plan_sha256'],
            'original_first_failure_report_sha256':plan['original_first_failure_report_sha256'],
            'interrupted_pair':plan['interrupted_pair'],'reused_runtime_records':1,'new_runtime_records':189} """
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="    try:\n        for trial in plan['schedule']:"
    after="""    try:
        # Complete validation of the one actual exit0 result; never launch it twice.
        initial_path=Path(plan['original_first_failure_report_path'])
        assert sha(initial_path)==plan['original_first_failure_report_sha256']
        initial=read(initial_path);assert not initial['passed']and len(initial['records'])==1
        inherited=initial['records'][0]
        assert inherited['case']==cases[inherited['identity']]and inherited['actual_exitcode']==0
        for key,path in plan['inherited_first_row_files'].items():assert sha(path['path'])==path['sha256'],key
        inherited['inherited_raw_directory']=str(initial_path.parent)
        inherited['original_record_index']=0;inherited['reused_actual_execution']=True
        inherited['interrupted_pair_noncontiguous']=True
        report['records'].append(inherited)
        report['inherited_resource_gate_observations']=initial['resource_gate_observations']
        gate('inherited-first-result-validation')
        start=time.perf_counter()
        inherited['continuation_actual_reference_sha256']={name:sha(path)for name,path in inherited['case']['paths'].items()}
        assert inherited['continuation_actual_reference_sha256']==inherited['case']['hashes']
        assert sha(plan['runtime']['path'])==plan['runtime']['sha256']
        inherited['continuation_reference_SHA_ms']=(time.perf_counter()-start)*1000
        assert headers(inherited['case']['paths']['input.bin'])==headers(inherited['case']['paths']['oracle.bin'])==inherited['case']['input_matrix_headers']
        assert json.loads(Path(inherited['raw_stdout']).read_text())==inherited['metric']
        validate_metric(inherited['metric'],inherited['case'],inherited['backend'])
        start=time.perf_counter();inherited['wholeC']=whole_compare(inherited['output'],inherited['case']['paths']['oracle.bin'])
        inherited['whole_file_compare_and_SHA_ms']=(time.perf_counter()-start)*1000
        assert inherited['wholeC']['bytes_compared']==inherited['case']['reference_bytes']
        assert inherited['wholeC']['original_C_sha256']==inherited['case']['hashes']['oracle.bin']
        assert headers(inherited['output'])==inherited['case']['input_matrix_headers']
        inherited['passed']=True;save()
        assert len(plan['schedule'])==189
        for trial in plan['schedule']:"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    (NEW/'runner.py').write_text(candidate)
    (NEW/'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='original04d-runner',tofile='classification-and-single-record-continuation')))
    shutil.copyfile(Path(__file__),NEW/'continuation-producer.py')
    previous.update(schema='load-pair-same-a95-cost-continuation-plan-v1',status='source-only; no continuation executed',
                    original_first_failure_plan_sha256=OLD_PLAN_SHA,original_first_failure_report_sha256=FAILED_REPORT_SHA,
                    original_first_failure_report_path=str(FAILED/'report.json'),
                    full_original_schedule=previous['schedule'],schedule=previous['schedule'][1:],
                    new_runtime_records=189,reused_runtime_records=1,
                    interrupted_pair={'identity':first['identity'],'round':first['round'],'scope':'genuine-default-VM',
                                      'reason':'runtime first plain result succeeded before runner-only assertion; fused partner resumes after audit gap',
                                      'interrupted_noncontiguous':True,'use':'retained all95 planned; excluded continuous94/VM89 comparison'},
                    comparison_denominators={'all_planned':95,'all_VM':90,'all_native':5,'continuous':94,'continuous_VM':89,'continuous_native':5})
    assert previous['full_original_schedule'][1:]==previous['schedule']
    assert len(previous['full_original_schedule'])==190 and len(previous['schedule'])==189
    paths={'original_report':FAILED/'report.json','original_stdout':Path(first['raw_stdout']),
           'original_stderr':Path(first['raw_stderr']),'original_output':Path(first['output'])}
    previous['inherited_first_row_files']={k:{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for k,p in paths.items()}
    previous['files']={p.relative_to(NEW).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(NEW.rglob('*'))if p.is_file()and p.name!='plan.json'}
    (NEW/'plan.json').write_text(json.dumps(previous,indent=2)+'\n')
    print(json.dumps({'plan':str(NEW/'plan.json'),'sha256':sha(NEW/'plan.json'),'new_records':189,'inherited_records':1,
                      'all_pairs':95,'continuous_pairs':94,'frozen_files':len(previous['files']),'actual_runtime_launches':0}),flush=True)
if __name__=='__main__':main()
