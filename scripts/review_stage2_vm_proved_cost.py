"""Independent full-byte audit of actual same-binary proof-policy costs."""
import json
import statistics
import time
from pathlib import Path
from review_stage2_vm_proved_integration import ROOT,P,sha,header
from review_stage2_vm_measurements import compare_files


def main():
    d=P/'artifacts/stage2-vm-proved-budget/policy-cost';f=d/'final-evidence'
    read=lambda path:json.loads(path.read_text())
    plan=read(d/'run-plan.json');report=read(d/'report.json');final=read(f/'manifest.json')
    accepted=read(ROOT/'outputs/stage2-root-vm-proved-cost-plan.json')
    assert accepted['passed'] and accepted['plan_sha256']==sha(d/'run-plan.json')==report['plan_sha256']==final['plan_sha256']
    assert report['passed'] and report['status']=='complete' and final['passed'] and final['actual_exit_code']==0
    assert sha(d/'report.json')==final['report_sha256']
    assert not report['source_or_binary_changed'] and not report['ordinary_default_promoted']
    for key in ('source_snapshot_sha256','raw_log_sha256'):
        for name,digest in final[key].items():assert sha(f/name)==digest,name
    assert len(final['raw_log_sha256'])==228
    assert sha(f/'summary.json')==final['summary_json_sha256'] and sha(f/'summary.md')==final['summary_md_sha256']
    for name,digest in plan['source_snapshot_sha256'].items():assert sha(d/name)==digest,name
    assert sha(d/'runtime.exe')==accepted['immutable_binary_sha256']
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    records=report['records'];assert len(records)==len(report['resource_gates'])==114
    assert final['output_file_evidence']==[dict(path=r['output'],bytes=r['bytes'],verified_sha256=r['sha256'],reference=r['reference'],scope='producer compared complete bytes; no new full-output hash in static freeze') for r in records]
    expected=[]
    for round in range(3):
        for c in plan['cases'][round:]+plan['cases'][:round]:
            for mode in (['fixed','proved'] if round%2==0 else ['proved','fixed']):expected.append((c['source'],round,mode))
    assert [(r['source'],r['round'],r['mode']) for r in records]==expected
    summaries=[];pairs=[];totalbytes=0
    for case in plan['cases']:
        folder=d/case['source'];rows=[r for r in records if r['source']==case['source']];assert len(rows)==6
        for name,digest in case['hashes'].items():assert sha(folder/name)==digest
        # Policy must not silently switch a native kernel or tile geometry.
        for key in ('selected_engine','vm_backend','effective_tile_size','tile_size_min','tile_size_max','vector_kernel','workspace_layout'):
            assert len({row[key] for row in rows})==1,(case['source'],key)
        paths=[folder/'oracle.bin']+[Path(r['output']) for r in rows]
        size,digests=compare_files(paths)
        assert size==case['reference_bytes'] and len(set(digests))==1 and digests[0]==case['hashes']['oracle.bin']
        assert header(folder/'input.bin')==header(paths[0])==case['input_matrix_headers']
        for row,digest in zip(rows,digests[1:]):
            output=Path(row['output']);assert header(output)==case['input_matrix_headers']
            assert row['actual_exit_code']==0 and row['byte_identical'] and row['sha256']==digest and row['bytes']==size
            assert row['exe_sha256']==accepted['immutable_binary_sha256'] and row['case_hashes']==case['hashes']
            raw=json.loads(output.with_suffix('.stdout').read_text());assert output.with_suffix('.stderr').read_bytes()==b''
            for extension in ('stdout','stderr'):
                assert sha(output.with_suffix('.'+extension))==final['raw_log_sha256']['raw/'+case['source']+'/'+output.with_suffix('.'+extension).name]
            for k,v in raw.items():assert row[k]==v,(case['source'],k)
            command=[str(d/'runtime.exe'),'--metadata',str(folder/'program.meta'),'--input',str(folder/'input.bin'),'--output',str(output),'--engine',case['engine_requested'],'--threads','4','--scheduler','parallel','--block-size',str(case['block']),'--vm-budget',row['mode']]
            assert row['command']==command
            assert row['matrices']==case['matrices'] and row['vm_budget_mode']==row['mode']
            assert 0<=row['vm_budget_proof_ms']<=row['compute_ms'] and 0<=row['vm_prepare_ms']<=row['compute_ms']
            assert row['resource_samples']>0 and row['process_peak_working_set_bytes']>0 and row['host_ram_bytes']==33605316608
            assert row['process_cpu_time_ms']==row['process_kernel_cpu_ms']+row['process_user_cpu_ms']
            assert 0<=row['host_busy_percent_during_process']<=100 and row['host_available_ram_min_bytes']>0
            if case['kind']=='vm':
                assert row['selected_engine']=='vm' and row['vm_backend']=='decoded-threaded' and row['vm_steps']==case['expected_vm_steps']
                assert row['vm_effective_step_limit_max']==1000000000
                if row['mode']=='fixed':
                    assert row['vm_budget_work']==row['vm_budget_proof_ms']==row['vm_budget_bound_peak']==0
                    assert row['vm_budget_proved_matrices']==row['vm_budget_unknown_matrices']==row['vm_budget_not_run_matrices']==0
                else:
                    assert row['vm_budget_proved_matrices']+row['vm_budget_unknown_matrices']==case['matrices'] and row['vm_budget_not_run_matrices']==0
                    assert row['vm_budget_proved_matrices' if case['expected_proof_status']=='proved' else 'vm_budget_unknown_matrices']==case['matrices']
            else:
                assert row['selected_engine'] in ('stage','tiled','diagonal') and row['vm_backend']==''
                assert row['vm_steps']==row['vm_budget_proof_ms']==row['vm_budget_work']==row['vm_budget_bound_peak']==row['vm_effective_step_limit_max']==0
                assert row['vm_budget_not_run_matrices']==case['matrices'] and row['vm_budget_proved_matrices']==row['vm_budget_unknown_matrices']==0
            totalbytes+=size
        ratios=[];walls=[]
        for round in range(3):
            fixed=next(r for r in rows if r['round']==round and r['mode']=='fixed');proved=next(r for r in rows if r['round']==round and r['mode']=='proved')
            ratio=proved['compute_ms']/fixed['compute_ms'];wall=proved['process_wall_ms']/fixed['process_wall_ms'];ratios.append(ratio);walls.append(wall)
            pairs.append(dict(source=case['source'],kind=case['kind'],round=round,compute_ratio_proved_over_fixed=ratio,compute_delta_ms=proved['compute_ms']-fixed['compute_ms'],wall_ratio_proved_over_fixed=wall,outcome='win' if ratio<1 else 'tie' if ratio==1 else 'negative'))
        summaries.append(dict(source=case['source'],kind=case['kind'],paired_compute_ratios=ratios,paired_wall_ratios=walls,median_paired_compute_ratio=statistics.median(ratios),median_paired_wall_ratio=statistics.median(walls),fixed_median_compute_ms=statistics.median(r['compute_ms'] for r in rows if r['mode']=='fixed'),proved_median_compute_ms=statistics.median(r['compute_ms'] for r in rows if r['mode']=='proved'),median_proof_ms=statistics.median(r['vm_budget_proof_ms'] for r in rows if r['mode']=='proved'),wins=sum(r<1 for r in ratios),negative=sum(r>1 for r in ratios)))
    assert summaries==report['summary'] and pairs==report['pairs']
    negative=[r for r in pairs if r['outcome']=='negative'];assert negative==report['negative_pairs'] and len(negative)==38
    assert sum(r['kind']=='vm' for r in negative)==34 and report['VM_pairs']==45 and report['native_pairs']==12
    consumed=0
    for row,gate in zip(records,report['resource_gates']):
        assert (row['source'],row['round'],row['mode'])==(gate['source'],gate['round'],gate['mode'])
        assert gate['passed'] and gate['available_RAM_bytes']==row['available_RAM_before_bytes']>=plan['small_batch_minimum_launch_RAM_bytes']
        assert gate['minimum_remaining_disk_bytes']==plan['expected_output_bytes_total']-consumed+plan['minimum_disk_overhead_bytes']
        assert gate['free_F_bytes']>=gate['minimum_remaining_disk_bytes'];consumed+=row['bytes']
    assert consumed==totalbytes==494057592
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(d/'run-plan.json'),report_sha256=sha(d/'report.json'),final_freeze_sha256=sha(f/'manifest.json'),
        binary_sha256=sha(d/'runtime.exe'),actual_session=94396,actual_exit_code=0,actual_whole_C_outputs=114,paired_comparisons=57,
        VM_pairs=45,native_pairs=12,negative_pairs=38,VM_negative_pairs=34,native_negative_pairs=4,complete_output_bytes_compared=totalbytes,
        summaries=summaries,host_busy_percent_range=[min(r['host_busy_percent_during_process'] for r in records),max(r['host_busy_percent_during_process'] for r in records)],
        host_free_ram_min_bytes=min(r['host_available_ram_min_bytes'] for r in records),ordinary_default_promoted=False,
        decision='Retain fixed ordinary default and optional proved isolated policy. Proof safely expands demonstrated large PROGRAM budget but adds measured computation, particularly short tasks; unknown/nested coverage still incomplete.',
        scope='All114 whole outputs independently streamed against frozen actual originalC; every raw metric/flag/proof/native bypass contract, 57 alternating compute/wall pairs, all38 negatives and RAM/disk gates recomputed. Same binary policy cost, not kernel acceleration. Native proof-zero timing fluctuates and host is not idle; no official/generalC/default promotion claim.')
    (ROOT/'outputs/stage2-root-vm-proved-cost.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='summaries'}))


if __name__=='__main__':main()
