"""Independent whole-C byte and paired-cost audit for the actual same844 batch."""
import json,statistics,time
from pathlib import Path
from review_stage2_vm_nested_next_sources import ROOT,P,D,read,sha
from review_stage2_vm_measurements import compare_files
def main():
    folder=D/'policy-cost';plan=read(folder/'run-plan.json');r=read(folder/'report.json')
    assert sha(folder/'report.json')=='12b4f66ed52857dd14aa5b2bfb9d623c2c393cb2634bbfed3d63d87ab751ec84'
    assert r['passed'] and r['status']=='complete' and r['plan_sha256']==sha(folder/'run-plan.json')
    assert sha(plan['binary']['path'])==plan['binary']['sha256']
    rows=r['records'];assert len(rows)==len(r['resource_gates'])==174
    expected=[(c['source'],k,mode)for c in plan['cases']for k in range(3)for mode in (['fixed','proved']if k%2==0 else ['proved','fixed'])]
    assert [(x['source'],x['round'],x['mode'])for x in rows]==expected
    total=consumed=0;pairs=[];summaries=[]
    for case in plan['cases']:
        selected=[x for x in rows if x['source']==case['source']];assert len(selected)==6
        for name,digest in case['hashes'].items():assert sha(case['paths'][name])==digest
        for key in ['selected_engine','vm_backend','effective_tile_size','tile_size_min','tile_size_max','vector_kernel','workspace_layout']:
            assert len({x[key]for x in selected})==1
        size,digests=compare_files([Path(case['paths']['oracle.bin'])]+[Path(x['output'])for x in selected]);assert size==case['reference_bytes'] and len(set(digests))==1 and digests[0]==case['hashes']['oracle.bin']
        for row,digest in zip(selected,digests[1:]):
            assert row['actual_exit_code']==0 and row['byte_identical'] and row['sha256']==digest and row['bytes']==size
            for ext in ['stdout','stderr']:assert sha(row['raw_'+ext])==row['raw_'+ext+'_sha256']
            assert not Path(row['raw_stderr']).read_bytes();raw=read(row['raw_stdout'])
            for k,v in raw.items():assert row[k]==v
            assert row['command']==[plan['binary']['path'],'--metadata',case['paths']['program.meta'],'--input',case['paths']['input.bin'],'--output',row['output'],'--engine',case['engine_requested'],'--threads','4','--scheduler','parallel','--block-size',str(case['block']),'--vm-budget',row['mode']]
            assert row['matrices']==case['matrices'] and row['vm_budget_mode']==row['mode']
            assert row['resource_samples']>0 and row['process_peak_working_set_bytes']>0
            assert 0<=row['host_busy_percent_during_process']<=100 and row['host_available_ram_min_bytes']>0
            assert row['vm_budget_first_work']+row['vm_budget_nested_work']==row['vm_budget_work']<=250000*case['matrices']
            assert 0<=row['vm_budget_proof_ms']<=row['compute_ms']
            if case['kind']=='vm':
                assert row['selected_engine']=='vm' and row['vm_backend']=='decoded-threaded' and row['vm_steps']==case['expected_vm_steps']
                assert row['vm_effective_step_limit_max']==max(1000000000,row['vm_budget_bound_peak'])
                if row['mode']=='fixed':assert row['vm_budget_work']==row['vm_budget_proof_ms']==row['vm_budget_proved_matrices']==row['vm_budget_unknown_matrices']==0
                else:
                    assert row['vm_budget_proved_matrices']+row['vm_budget_unknown_matrices']==case['matrices']
                    assert row['vm_budget_proved_matrices']==row['vm_budget_first_proved_matrices']+row['vm_budget_nested_proved_matrices']
                    assert row['vm_budget_nested_attempted_matrices']+row['vm_budget_nested_work_exhausted_skips']==row['vm_budget_first_unknown_matrices']
            else:
                assert row['vm_steps']==row['vm_budget_work']==row['vm_budget_proof_ms']==row['vm_effective_step_limit_max']==0
                assert row['vm_budget_not_run_matrices']==case['matrices']
            total+=size
        ratios=[]
        for k in range(3):
            fixed=next(x for x in selected if x['round']==k and x['mode']=='fixed');proved=next(x for x in selected if x['round']==k and x['mode']=='proved');ratio=proved['compute_ms']/fixed['compute_ms'];ratios.append(ratio)
            pairs.append(dict(source=case['source'],kind=case['kind'],round=k,compute_ratio_proved_over_fixed=ratio,compute_delta_ms=proved['compute_ms']-fixed['compute_ms'],wall_ratio_proved_over_fixed=proved['process_wall_ms']/fixed['process_wall_ms'],outcome='win'if ratio<1 else 'negative'if ratio>1 else 'tie'))
        summaries.append(dict(source=case['source'],kind=case['kind'],median_compute_ratio=statistics.median(ratios)))
    assert pairs==r['pairs'] and [p for p in pairs if p['outcome']=='negative']==r['negative_pairs']
    for row,gate in zip(rows,r['resource_gates']):
        assert gate['passed'] and gate['minimum_remaining_disk_bytes']==plan['expected_output_bytes_total']-consumed+plan['minimum_disk_reserve_bytes']
        assert gate['free_F_bytes']>=gate['minimum_remaining_disk_bytes'] and gate['available_RAM_bytes']>=plan['minimum_launch_RAM_bytes'];consumed+=row['bytes']
    assert consumed==total==495920904
    negative=r['negative_pairs'];result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(folder/'report.json'),actual_exit_code=0,actual_session=54561,whole_C_outputs=174,paired_comparisons=87,VM_pairs=69,native_pairs=18,negative_pairs=len(negative),VM_negative_pairs=sum(p['kind']=='vm'for p in negative),native_negative_pairs=sum(p['kind']=='native'for p in negative),independently_compared_bytes=total,summaries=summaries,host_busy_percent_range=[min(x['host_busy_percent_during_process']for x in rows),max(x['host_busy_percent_during_process']for x in rows)],scope='All174 realC fullbytes/rawmetrics/commands/nativebypass/proofwork and87 alternatingsamebinary compute/wall pairs independently verified. Proof can extend safe semantic coverage but is additional compute; allnegatives retained. Sharedhost timings, no kernel/official speedup or default promotion.')
    (ROOT/'outputs/stage2-root-vm-nested-cost-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='summaries'}))
if __name__=='__main__':main()
