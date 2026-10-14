"""Freeze completed policy costs without rerunning C, VM, or full output hashes."""
import hashlib,json,shutil,statistics
from pathlib import Path

P=Path(__file__).resolve().parents[1]
ROOT=P/'artifacts/stage2-vm-proved-budget/policy-cost'
DEST=ROOT/'final-evidence'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    plan=read(ROOT/'run-plan.json');report=read(ROOT/'report.json')
    assert report['passed'] and report['status']=='complete'
    assert len(report['records'])==114 and len(report['pairs'])==57
    assert report['plan_sha256']==digest(ROOT/'run-plan.json')
    assert len(report['resource_gates'])==114 and all(x['passed']for x in report['resource_gates'])
    assert digest(plan['binary']['path'])==plan['binary']['sha256']
    assert digest(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert digest(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    for path,sha in plan['source_snapshot_sha256'].items():assert digest(ROOT/path)==sha
    DEST.mkdir(exist_ok=False)
    records=report['records'];vm=[x for x in report['pairs']if x['kind']=='vm'];controls=[x for x in report['pairs']if x['kind']=='native']
    assert len(vm)==45 and len(controls)==12
    assert all(x['actual_exit_code']==0 and x['byte_identical']for x in records)
    summary={'status':'completed; optional policy not promoted','actual_tool_session':94396,'actual_exit_code':0,'plan_sha256':digest(ROOT/'run-plan.json'),'report_sha256':digest(ROOT/'report.json'),'records':114,'pairs':57,'VM_pairs':45,'native_control_pairs':12,'whole_C_output_bytes':sum(x['bytes']for x in records),'negative_pairs':len(report['negative_pairs']),'VM_negative_pairs':sum(x['outcome']=='negative'for x in vm),'native_negative_pairs':sum(x['outcome']=='negative'for x in controls),'VM_wins':sum(x['outcome']=='win'for x in vm),'native_wins':sum(x['outcome']=='win'for x in controls),'all_case_results':report['summary'],'host_busy_percent_min':min(x['host_busy_percent_during_process']for x in records),'host_busy_percent_max':max(x['host_busy_percent_during_process']for x in records),'host_available_RAM_min_bytes':min(x['host_available_ram_min_bytes']for x in records),'process_PeakWS_max_bytes':max(x['process_peak_working_set_bytes']for x in records),'process_peak_commit_max_bytes':max(x['process_peak_commit_bytes']for x in records),'proof_in_compute':True,'unknown_retains_fixed_limit':True,'native_proof_work_ms_zero':all(x['vm_budget_proof_ms']==x['vm_budget_work']==0 for x in records if x['kind']=='native'),'ordinary_default_promoted':False,'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256'],'scope_limit':'This measures policy cost on this host and does not establish a kernel speedup or official score; maximum no-explicit-limit coverage was a separate functional gate.','decision':'Keep optional proof and fixed production default pending a separate policy decision. Short-task proof overhead and all negative results remain visible.','CPU_window_released':True,'subsequent_new_execution':False}
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines=['# Completed optional proof policy cost evidence','', 'Actual session94396 exited0. All114 outputs match actual original C bytes;57 alternating pairs were preserved. Production99a/fixed1e9 and default-OFF proof compilation remain unchanged.','', f"VM cohort: {summary['VM_negative_pairs']}/45 negative pairs; controls: {summary['native_negative_pairs']}/12 negative pairs. Controls execute native stage/diagonal/tiled with zero proof work/time and cannot establish a proof speedup.",'', '| Source | Kind | Three proved/fixed compute ratios | Median ratio | Fixed/proved median ms | Median proof ms |','|---|---|---|---:|---:|---:|']
    for row in report['summary']:
        lines.append(f"| {row['source']} | {row['kind']} | {', '.join(f'{x:.6f}'for x in row['paired_compute_ratios'])} | {row['median_paired_compute_ratio']:.6f} | {row['fixed_median_compute_ms']:.3f}/{row['proved_median_compute_ms']:.3f} | {row['median_proof_ms']:.3f} |")
    lines += ['', 'Ratios above1 mean an increased cost. The two fresh small batches retain their original four shapes rather than artificial repetition: stride2 and disjoint have median cost ratios1.821138 and2.269231, with approximately0.1–0.15ms added proof work. Historical long VM sources have mixed paired results, including all-negative integer/helper/SSA sources. Small native controls show timing variation despite no proof being performed; these results are retained as controls, not attributed to proof logic.', '', f"Measured host CPU busy spans {summary['host_busy_percent_min']:.2f}–{summary['host_busy_percent_max']:.2f}% and sampled free RAM never falls below {summary['host_available_RAM_min_bytes']}bytes. User applications were untouched. Proof and decoding remain within compute; per-trial metadata/input/output I/O, process wall, SHA validation, full-file comparison and Win32 process/host counters are available in the frozen report.", '', 'Recommendation: retain optional proof with this complete cost evidence. No timing-based promotion threshold, caching, default change, new source sizing, or nested-loop implementation is introduced. The previously verified N10000 optional proof removes the need for an explicit limit on the accepted finite subset; it does not prove arbitrary C or eliminate the documented fixed-default limitation.', '', 'Only static nested-loop design review follows this run.']
    (DEST/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    snapshots={}
    for source in [Path(__file__),P/'docs/stage2-vm-proved-policy-cost-plan.md',P/'docs/stage2-vm-nested-budget-design.md']:
        target=DEST/'source'/source.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);snapshots[target.relative_to(DEST).as_posix()]=digest(target)
    for name in ['run-plan.json','report.json']:
        shutil.copyfile(ROOT/name,DEST/name)
    logs={}
    for row in records:
        folder=ROOT/row['source']
        for suffix in ['stdout','stderr']:
            path=folder/f"round-{row['round']}-{row['mode']}.{suffix}";target=DEST/'raw'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);logs[target.relative_to(DEST).as_posix()]=digest(target)
    outputs=[{'path':x['output'],'bytes':x['bytes'],'verified_sha256':x['sha256'],'reference':x['reference'],'scope':'producer compared complete bytes; no new full-output hash in static freeze'}for x in records]
    manifest={'passed':True,'schema':'vm-proved-policy-cost-final-v1','actual_exit_code':0,'plan_sha256':digest(DEST/'run-plan.json'),'report_sha256':digest(DEST/'report.json'),'summary_json_sha256':digest(DEST/'summary.json'),'summary_md_sha256':digest(DEST/'summary.md'),'source_snapshot_sha256':snapshots,'raw_log_sha256':logs,'implementation_and_flags_frozen_in_plan':True,'output_file_evidence':outputs,'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256'],'default_changed':False,'new_C_or_VM_execution':False,'full_output_rehash':False}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'manifest_sha256':digest(DEST/'manifest.json'),'summary_sha256':digest(DEST/'summary.json'),'VM_negative_pairs':summary['VM_negative_pairs'],'native_negative_pairs':summary['native_negative_pairs'],'host_busy_percent_range':[summary['host_busy_percent_min'],summary['host_busy_percent_max']],'host_free_RAM_min':summary['host_available_RAM_min_bytes'],'no_new_execution':True}))

if __name__=='__main__':main()
