"""Freeze the terminal N10000 true-C triangle evidence without rereading1.6GB."""
import json,shutil
from pathlib import Path
from benchmark_vm_nested_policy_stage2 import read,sha,write

P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-nested-budget'
ROOT=STAGE/'triangular-maximum';OUT=STAGE/'triangular-maximum-acceptance'

def main():
    plan=read(ROOT/'run-plan.json');report=read(ROOT/'report.json')
    assert report['passed']and report['status']=='complete'and len(report['runs'])==3
    assert report['actual_C_reference']['sha256']==report['actual_proved_output']['sha256']
    assert report['actual_fixed_rejection']['no_published_or_partial_output']
    assert all(g['passed']for g in report['resource_gates'])and report['after_candidate_disk_reserve']['passed']
    assert not OUT.exists();OUT.mkdir();files={}
    def copy(source,relative):
        source=Path(source);dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        files[relative]={'origin':str(source),'sha256':sha(source),'bytes':source.stat().st_size}
        assert sha(dest)==files[relative]['sha256']
    for source in sorted(ROOT.rglob('*')):
        if source.is_file()and source.suffix not in ['.bin','.partial']:
            copy(source,source.relative_to(ROOT).as_posix())
    for source in [Path(__file__)]:copy(source,'freeze-source/'+source.relative_to(P).as_posix())
    final=report['actual_proved_output'];oracle=report['actual_C_reference'];reject=report['actual_fixed_rejection']
    summary={'shape':10000,'matrices':1,'full_original_C_bytes':800000008,
             'actual_steps':final['vm_steps'],'proved_bound':final['vm_budget_bound_peak'],
             'effective_cap':final['vm_effective_step_limit_max'],'shared_work':final['vm_budget_work'],
             'first_work':final['vm_budget_first_work'],'nested_work':final['vm_budget_nested_work'],
             'compute_ms':final['compute_ms'],'proof_ms':final['vm_budget_proof_ms'],
             'actual_C_process_wall_ms':oracle['process_wall_ms'],'proved_process_wall_ms':final['process_wall_ms'],
             'fixed_rejection_process_wall_ms':reject['process_wall_ms'],
             'all_process_PeakWS_bytes':{r['stage']:r['process_peak_working_set_bytes']for r in report['runs']},
             'all_process_peak_commit_bytes':{r['stage']:r['process_peak_commit_bytes']for r in report['runs']},
             'minimum_host_available_RAM_bytes':min(r['host_available_ram_min_bytes']for r in report['runs']),
             'all_fresh_resource_gates_passed':True,'fixed1e9_rejected_without_output_or_partial':True,
             'optional_proved_original_C_passed':True,'ordinary_fixed_default_fullshape_passed':False,
             'explicit_step_limit':False,'source_or_N_specific_runtime_routing':False,
             'no_speedup_from_reject_vs_success_claim':True,'default_promotion':False}
    write(OUT/'summary.json',summary)
    files['summary.json']={'origin':str(OUT/'summary.json'),'sha256':sha(OUT/'summary.json'),'bytes':(OUT/'summary.json').stat().st_size}
    doc=P/'docs/stage2-vm-nested-triangular-maximum.md'
    doc.write_text('\n'.join([
      '# Optional nested VM: actual N10000 triangle acceptance','',
      'The frozen true-C triangular source completed one N10000 matrix. The new real GCC oracle output and GNUauto-proved output are each800000008bytes and match over every byte. Their SHA256 is '+final['sha256']+'. This is an actual full-shape check, separately from the previous allocation-free proof probe.','',
      'OriginalVM steps are1,400,030,009; the generic conservative nested bound and effective automatic proved cap are2,799,890,009. No explicit step limit was passed. Shared analysis work is24,161 within250,000. Source, PROGRAM, symbolic Metadata graph, strict FP flags and same844 runtime are unchanged. The ordinary99a runtime remains fixed1e9/proofOFF.','',
      'The same candidate with fixed1e9 rejected with the original instruction-limit error, actualexit1, without published or partial output. Proved success versus fixed rejection establishes a budget/semantic-coverage gain; it is not a speedup measurement. This does not establish arbitrary C or every genericN10000 case. No large Gram, decoded or portable run was added.','',
      f"Proved reported compute was{final['compute_ms']:.3f}ms including{final['vm_budget_proof_ms']:.3f}ms proof. OriginalC process wall was{oracle['process_wall_ms']:.3f}ms; proved process wall was{final['process_wall_ms']:.3f}ms. These are functional-resource observations, not alternating performance results.",'',
      'The three processes ran sequentially. Every actual launch rechecked at least2.5GiB available RAM after input/source/exe SHA. Disk gates reserved still-ungenerated full outputs plus512MiB, while all completed outputs were preserved. Actual PeakWS/commit, whole-host background CPU/RAM, metadata/IO/compute, rawstdout/stderr and external SHA/comparison costs are saved. User applications were untouched.','',
      'Frozen manifest: `artifacts/stage2-vm-nested-budget/triangular-maximum-acceptance/manifest.json`. Original large files retain their actual paths plus SHA from the completed streaming checks; freeze does not copy or reread the1.6GB output pair.','']),encoding='utf-8')
    copy(doc,'results-document/'+doc.name)
    outputs=[]
    for row in [oracle,final]:
        path=Path(row['output']);assert path.stat().st_size==800000008
        outputs.append({'path':str(path),'bytes':path.stat().st_size,'sha256':row['sha256'],
                        'stage':row['stage'],'SHA_from_actual_production_or_full_stream_comparison':True})
    manifest={'schema':'optional-nested-VM-triangular-maximum-acceptance-v1','passed':True,
              'actual_session_id':64477,'actual_terminal_exit_code':0,'frozen_files':files,
              'plan_sha256':sha(ROOT/'run-plan.json'),'report_sha256':sha(ROOT/'report.json'),
              'summary_sha256':sha(OUT/'summary.json'),'large_output_index':outputs,
              'input_index':{'path':plan['input'],'bytes':plan['input_bytes'],'sha256':plan['input_sha256'],
                             'fresh_prepare_and_each_launch_SHA_checked':True},
              'large_files_not_rehashed_or_copied_during_freeze':True,
              'same_runtime_EXE_sha256':plan['runtime_EXE_sha256'],'actual_originalC_EXE_sha256':plan['oracle_EXE_sha256'],
              'source_sha256':plan['source_sha256'],'metadata_sha256':plan['metadata_sha256'],
              'strict_sequential':True,'actual_originalC_executions':1,'actual_VM_executions':2,
              'ordinary_fixed_default_passed':False,'optin_proved_passed':True,
              'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256'],
              'ordinary_or_default_changed':False,'performance_claim':False}
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    write(OUT/'manifest.json',manifest)
    print(json.dumps({'passed':True,'manifest_sha256':sha(OUT/'manifest.json'),'summary_sha256':sha(OUT/'summary.json'),
                      'frozen_files':len(files),'large_files_rehashed_or_C_VM_rerun':False}),flush=True)

if __name__=='__main__':main()
