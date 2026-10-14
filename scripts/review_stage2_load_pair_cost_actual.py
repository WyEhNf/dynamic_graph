"""Root completeC/matched-binary cost, all negatives and retained archive."""
import json,statistics,math
from collections import Counter
from pathlib import Path
from review_stage2_load_pair_functional_actual import sha,equal,headers
ROOT=Path(__file__).resolve().parents[1];R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'performance-continuation-evidence';PRE=R/'performance-continuation-plan';ARCH=R/'cost-acceptance'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    report=read(D/'report.json');plan=read(PRE/'plan.json');manifest=read(ARCH/'manifest.json')
    assert sha(D/'report.json')=='113f42451561df72e8b429e6b9eb46beea809b31d5dc8d20d589cc24ed053ca4'
    assert sha(ARCH/'manifest.json')=='57c4f608e5394ae9b3b93151f64adc04a727b1cfdaa599dab0ab3f9a126776cd'
    for path,item in manifest['files'].items():
        assert sha(ARCH/path)==item['sha256'] and (ARCH/path).stat().st_size==item['bytes'],path
        if path=='summary.json':assert item['origin']=='new factual static summary from unchanged actual report'
        else:assert sha(item['origin'])==item['sha256'],path
    assert len(manifest['files'])==3402
    assert report['passed'] and report['owner_PID']==131232 and not report['observer_used'] and not report['runtime_or_default_changed']
    assert report['plan_sha256']==sha(PRE/'plan.json') and len(report['records'])==190 and report['reused_runtime_records']==1 and report['new_runtime_records']==189
    assert len(report['resource_gate_observations'])==379 and all(g['passed'] and min(g['available_RAM_bytes'],g['free_G_bytes'])>=1073741824 for g in report['resource_gate_observations'])
    original=read(R/'performance-evidence/report.json');assert sha(R/'performance-evidence/report.json')==report['original_first_failure_report_sha256']=='070392af398496ac4884a7889bf0b65017c1d4231a6387dc986a30d8e7b06804'
    schedule=plan['full_original_schedule'];assert len(schedule)==190;wholebytes=0;bytrial={};host=[];peak=[]
    cases={c['identity']:c for c in plan['cases']}
    for row,expected in zip(report['records'],schedule,strict=True):
        assert all(row[k]==expected[k] for k in ['identity','round','backend']) and row['actual_exitcode']==0 and row['passed']
        case=cases[row['identity']];assert row['case']==case and row['actual_exe_sha256']==plan['runtime']['sha256']
        assert row['command']==case['runtime_command_common']+['--output',row['output'],'--vm-backend',row['backend']]
        for name,path in case['paths'].items():assert sha(path)==case['hashes'][name]==row['actual_reference_sha256'][name]
        for name in ['stdout','stderr']:assert sha(row['raw_'+name])==row['raw_'+name+'_sha256']
        metric=json.loads(Path(row['raw_stdout']).read_text());assert metric==row['metric']
        assert metric['vm_steps']==case['expected_vm_steps'] and metric['matrices']==case['matrices'] and metric['compute_ms']>0
        assert metric['vm_budget_mode']=='fixed' and metric['vm_budget_work']==metric['vm_budget_proof_ms']==0 and metric['vm_budget_proved_matrices']==metric['vm_budget_unknown_matrices']==0
        assert metric['vm_budget_not_run_matrices']==(case['matrices'] if case['default_path_scope']=='native-control' else 0)
        assert 'vm_last_pc' not in metric and row['vm_last_pc'] is None
        assert all(math.isfinite(metric[k]) and metric[k]>=0 for k in ['metadata_read_ms','input_read_ms','output_write_ms','compute_ms','vm_prepare_ms','vm_fusion_plan_ms'])
        if case['default_path_scope']=='native-control':assert metric['selected_engine']!='vm' and metric['vm_fusion_pairs_executed']==metric['vm_fusion_pairs_discovered']==0
        else:
            assert metric['selected_engine']=='vm' and metric['vm_backend']==row['backend'] and metric['vm_effective_step_limit_max']==1000000000
            if row['backend']=='decoded-threaded':assert metric['vm_fusion_pairs_executed']==metric['vm_fusion_pairs_discovered']==metric['vm_fusion_plan_ms']==0
            else:assert metric['vm_fusion_status_last']=='entry-safe-pairs' and metric['vm_fusion_pairs_executed']<=metric['vm_steps']//2
        n=equal(row['output'],case['paths']['oracle.bin']);assert n==case['reference_bytes'] and sha(row['output'])==case['hashes']['oracle.bin'];wholebytes+=n
        assert headers(row['output'])==case['input_matrix_headers'] and Path(row['output']).drive.upper()=='G:'
        bytrial[(row['identity'],row['round'],row['backend'])]=row;host.append(row['resource']['host_busy_percent_during_process']);peak.append(row['resource']['process_peak_working_set_bytes'])
    assert report['records'][0]['metric']==original['records'][0]['metric'] and report['records'][0]['reused_actual_execution']
    summary=[];allcounts=Counter();continuous=Counter();vmcontinuous=Counter();nativecontinuous=Counter()
    for c,s in zip(plan['cases'],report['summary'],strict=True):
        ratios=[];kept=[]
        for r in range(5):
            a=bytrial[c['identity'],r,'decoded-threaded'];b=bytrial[c['identity'],r,'decoded-threaded-load-pair'];ratio=b['metric']['compute_ms']/a['metric']['compute_ms'];ratios.append(ratio)
            interrupted=c['identity']=='changed-arithmetic' and r==0;outcome='win' if ratio<1 else 'negative' if ratio>1 else 'tie';allcounts[outcome]+=1
            p=next(p for p in report['pairs'] if p['identity']==c['identity'] and p['round']==r)
            assert p['compute_ratio_fused_over_plain']==ratio and p['outcome']==outcome and p['interrupted_noncontiguous']==interrupted
            if not interrupted:
                kept.append(ratio);continuous[outcome]+=1;(nativecontinuous if c['default_path_scope']=='native-control' else vmcontinuous)[outcome]+=1
        assert s['all_five_compute_ratios']==ratios and s['continuous_compute_ratios']==kept and s['continuous_median_paired_compute_ratio']==statistics.median(kept)
        summary.append(dict(identity=c['identity'],scope=c['default_path_scope'],continuous_pairs=len(kept),continuous_median_ratio=statistics.median(kept),all_planned_ratios=ratios))
    assert wholebytes==817390840 and dict(allcounts)==dict(win=49,negative=45,tie=1) and dict(continuous)==dict(win=48,negative=45,tie=1)
    assert dict(vmcontinuous)==dict(win=46,negative=42,tie=1) and dict(nativecontinuous)==dict(win=2,negative=3)
    result=dict(passed=True,actual_owner_session=82170,actual_owner_PID=131232,actual_tool_chunk='72a964',actual_terminal_exit_code=0,report_sha256=sha(D/'report.json'),archive_sha256=sha(ARCH/'manifest.json'),archive_files=3402,archive_bytes=sum(f['bytes'] for f in manifest['files'].values()),actual_originalC_outputs=190,independent_full_C_bytes=wholebytes,planned_pairs=95,continuous_pairs=94,first_interrupted_pair_retained=True,all_planned_outcomes=dict(allcounts),continuous_outcomes=dict(continuous),continuous_VM_outcomes=dict(vmcontinuous),continuous_native_outcomes=dict(nativecontinuous),fresh_continuation_resource_gates=379,host_busy_percent_range=[min(host),max(host)],measured_cli_peak_working_set_max_bytes=max(peak),summaries=summary,scope='Actual exactsamea95/backend-only comparison, strictFP and all190 originalC full streams independently checked. First runner classification failure preserved; first noncontiguous pair separate from94 continuous. Mixed46wins42negative1tie VM means no uniform speed improvement/default promotion; whole-host contention and short cases remain. No official85 compute or arbitraryC claim.',authorized_next='Freeze mixed costs; inspect per-source dynamic hot opcode coverage/entry-safety/discovery overhead from actualPROGRAM/metrics before choosing an execution mechanism. No automatic promotion or repeat ofsame95 benchmark.')
    (ROOT/'outputs/stage2-root-load-pair-cost-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='summaries'}))
if __name__=='__main__':main()
