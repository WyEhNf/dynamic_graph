"""Freeze completed174/87 costs and every negative without rerunning any workload."""
import hashlib,json,shutil,statistics
from pathlib import Path

P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-nested-budget'
ROOT=STAGE/'policy-cost';OUT=STAGE/'policy-cost-acceptance'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    plan=read(ROOT/'run-plan.json');report=read(ROOT/'report.json')
    assert report['passed']and len(report['records'])==174 and len(report['pairs'])==87
    assert len({(r['source'],r['round'],r['mode'])for r in report['records']})==174
    assert not OUT.exists();OUT.mkdir();files={};output_index=[];case_index=[]
    def copy(source,relative):
        dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        files[relative]={'origin':str(source),'sha256':sha(source),'bytes':source.stat().st_size}
        assert sha(dest)==files[relative]['sha256']
    for name in ['run-plan.json','report.json','design-plan.json','runtime.exe']:copy(ROOT/name,name)
    for folder in ['implementation-source','implementation-build','plan-source']:
        for source in sorted((ROOT/folder).rglob('*')):
            if source.is_file():copy(source,source.relative_to(ROOT).as_posix())
    for source in sorted((STAGE/'next-prepared/source').rglob('*')):
        if source.is_file():copy(source,'complete-import-closure/'+source.relative_to(STAGE/'next-prepared/source').as_posix())
    for case in plan['cases']:
        for name,digest in case['hashes'].items():
            source=Path(case['paths'][name]);case_index.append({'source':case['source'],'file':name,'path':str(source),'sha256':digest,'bytes':source.stat().st_size})
            if name not in ['input.bin','oracle.bin']:
                assert sha(source)==digest;copy(source,'cases/'+case['source']+'/'+name)
    for row in report['records']:
        for key in ['raw_stdout','raw_stderr']:
            source=Path(row[key]);assert sha(source)==row[key+'_sha256']
            copy(source,'raw/'+row['source']+'/'+source.name)
        output=Path(row['output']);assert output.stat().st_size==row['bytes']and row['byte_identical']
        output_index.append({'source':row['source'],'round':row['round'],'mode':row['mode'],'path':str(output),
                             'sha256':row['sha256'],'bytes':row['bytes'],'originalC_reference':row['reference'],
                             'actual_trial_full_stream_comparison_passed':True})
    groups={}
    for kind in ['vm','native']:
        pairs=[x for x in report['pairs']if x['kind']==kind]
        groups[kind]={'pairs':len(pairs),'win':sum(x['outcome']=='win'for x in pairs),
                      'negative':sum(x['outcome']=='negative'for x in pairs),'tie':sum(x['outcome']=='tie'for x in pairs)}
    summary={'records':174,'pairs':87,'groups':groups,
             'all_negative_pairs':report['negative_pairs'],'all29_case_summaries':report['summary'],
             'actual_elapsed_seconds':report['elapsed_seconds'],
             'all_output_bytes':sum(r['bytes']for r in report['records']),
             'host_busy_percent_range':[min(r['host_busy_percent_during_process']for r in report['records']),max(r['host_busy_percent_during_process']for r in report['records'])],
             'available_host_RAM_min_bytes':min(r['host_available_ram_min_bytes']for r in report['records']),
             'runtime_peak_WS_max_bytes':max(r['process_peak_working_set_bytes']for r in report['records']),
             'all_native_records_no_proof':all(r['vm_budget_work']==r['vm_budget_proof_ms']==0 for r in report['records']if r['kind']=='native'),
             'proved_unknown_matrix_totals_over_three_rounds':{
                 'first_proved':sum(r['vm_budget_first_proved_matrices']for r in report['records']),
                 'first_unknown':sum(r['vm_budget_first_unknown_matrices']for r in report['records']),
                 'nested_proved':sum(r['vm_budget_nested_proved_matrices']for r in report['records']),
                 'nested_unknown':sum(r['vm_budget_nested_unknown_matrices']for r in report['records']),
                 'final_proved':sum(r['vm_budget_proved_matrices']for r in report['records']),
                 'final_unknown':sum(r['vm_budget_unknown_matrices']for r in report['records'])},
             'interpretation':'Optional proof adds semantic/budget coverage, not a demonstrated general compute speedup. No default promotion; native short timing noise cannot be attributed to bypassed proof.',
             'ordinary_default_proof_disabled_retained':True,'maximum_or_large_originalC_VM_executed':False}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    copy(Path(__file__),'freeze-source/tools/'+Path(__file__).name)
    doc=P/'docs/stage2-vm-nested-policy-cost-results.md'
    lines=['# Optional nested VM: actual policy cost results','',
           'The frozen same844 fixed/proved experiment completed all174 executions and87 pairs, with every whole-file result equal to its real original-C reference. The optional proof is retained without default promotion. Ordinary99a still uses fixed1e9 and proofOFF.','',
           f"There were {len(report['negative_pairs'])} negative pairs and {87-len(report['negative_pairs'])} wins, including {groups['vm']['negative']} negatives among69 VM pairs. All outcomes remain in the report. The new short rectangle/triangle/unknown batches show visible proof overhead; larger old streams have smaller relative overhead. Native controls run no proof, so their small timings do not measure proof speedup.",'',
           f"Whole-host busy was {summary['host_busy_percent_range'][0]:.2f}–{summary['host_busy_percent_range'][1]:.2f}%; available RAM minimum was {summary['available_host_RAM_min_bytes']}bytes. User applications were untouched. Compute includes both proof stages/selection/decode; process wall, IO, SHA checking and full-byte comparison are recorded separately.",'',
           '| Case | Engine scope | Median proved/fixed compute | First proof ms | Nested proof ms |',
           '|---|---|---:|---:|---:|']
    for row in report['summary']:
        lines.append(f"| {row['source']} | {row['kind']} | {row['median_paired_compute_ratio']:.4f} | {row['median_first_ms']:.3f} | {row['median_nested_ms']:.3f} |")
    lines+=['','Ratios above1 are slower. Sub-millisecond native controls and the two small positive old-case medians are not evidence of a causal general speedup. No source, input, worker setting, step limit or kernel was changed between paired commands.','',
            'The separate25 high-N analysis-only probe matched15 predicted bounds and10 unknown safety cases. It allocates no matrices or executes C/VM. That evidence establishes the proof result, not full large-shape output acceptance. No N10000 matrix execution or default budget change is included here.','',
            'Actual report: `artifacts/stage2-vm-nested-budget/policy-cost/report.json`; immutable source/raw/summary manifest: `policy-cost-acceptance/manifest.json`. Every large output retains its original path plus the SHA obtained during the actual full-stream comparison. Freeze does not reread/copy the495920904-byte output set.','']
    doc.write_text('\n'.join(lines),encoding='utf-8');copy(doc,'results-document/'+doc.name)
    files['summary.json']={'origin':str(OUT/'summary.json'),'sha256':sha(OUT/'summary.json'),'bytes':(OUT/'summary.json').stat().st_size}
    manifest={'schema':'optional-nested-VM-policy-cost-acceptance-v1','passed':True,
              'actual_tool_session_id':54561,'actual_terminal_exit_code':0,
              'plan_sha256':sha(ROOT/'run-plan.json'),'report_sha256':sha(ROOT/'report.json'),
              'prepared_source_manifest_sha256':sha(STAGE/'next-prepared/manifest.json'),
              'analysis_only_manifest_sha256':sha(STAGE/'analysis-only-acceptance/manifest.json'),
              'frozen_files':files,'case_file_index':case_index,'actual_output_index':output_index,
              'large_output_SHA_from_actual_full_trial_comparison_not_rehashed_during_freeze':True,
              'records':174,'pairs':87,'all_output_bytes':summary['all_output_bytes'],'groups':groups,
              'same_EXE_sha256':plan['binary']['sha256'],'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256'],
              'ordinary_changed':False,'default_promoted':False,'new_C_oracle_executions':0,
              'summary_sha256':sha(OUT/'summary.json'),'source_specific_runtime_dispatch_or_selection':False}
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'manifest_sha256':sha(OUT/'manifest.json'),'summary_sha256':sha(OUT/'summary.json'),
                      'frozen_files':len(files),'groups':groups,'all_output_bytes':summary['all_output_bytes'],'ordinary_changed':False}),flush=True)

if __name__=='__main__':main()
