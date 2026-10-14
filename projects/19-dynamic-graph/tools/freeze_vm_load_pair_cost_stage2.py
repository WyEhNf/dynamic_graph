"""Preserve every successful/failed cost record and reconstructable candidate."""
import hashlib,json,shutil,statistics
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
P=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def main():
    report=json.loads((R/'performance-continuation-evidence/report.json').read_text())
    plan=json.loads((R/'performance-continuation-plan/plan.json').read_text())
    assert report['passed']and len(report['records'])==190 and len(report['pairs'])==95
    assert report['comparison_groups']['continuous94']['pairs']==94
    assert sum(p['interrupted_noncontiguous']for p in report['pairs'])==1
    out=R/'cost-acceptance';assert not out.exists();out.mkdir()
    origins={}
    def copy(origin,relative):
        dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin,dest);origins[relative]=origin
    for directory in ['workspace','source-before','performance-plan','performance-continuation-plan',
                      'performance-evidence','performance-continuation-evidence']:
        for p in sorted((R/directory).rglob('*')):
            if p.is_file():copy(p,directory+'/'+p.relative_to(R/directory).as_posix())
    accepted=R/'build-gate-acceptance/build-gnu'
    for name in ['cholesky_runtime.exe','libcholesky_core.a','CMakeCache.txt',
                 'CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/flags.make',
                 'CMakeFiles/cholesky_runtime.dir/link.txt','CMakeFiles/cholesky_runtime.dir/linkLibs.rsp']:
        copy(accepted/name,'matching-build/'+name)
    for name in ['manifest.json','implementation.diff']:
        copy(R/name,'original-load-pair-source/'+name)
    copy(R/'build-gate-acceptance/manifest.json','prior-build-gate-manifest.json')
    copy(R/'functional-acceptance/manifest.json','prior-functional-manifest.json')
    for case in plan['cases']:
        for name,path in case['paths'].items():
            origin=Path(path);assert sha(origin)==case['hashes'][name]
            copy(origin,'originalC-reference/'+case['identity']+'/'+name)
    copy(Path(__file__),'freeze-producer.py')
    summary={'schema':'load-pair-same-a95-cost-summary-v1','passed':True,'scope':'explicit samebinary a95 threaded versus LOAD+LOAD fused, default fixed1e9',
             'actual_records':190,'initial_successful_execution_reused':1,'new_runtime_executions':189,
             'first_runner_failure':'initial genericVM not-run counter assertion expected10 but actual fixed status counter0; original failedplan/report/raw/output preserved; runtime unchanged',
             'comparison_groups':report['comparison_groups'],'cohort_counts':report['cohort_counts'],'sources':report['summary'],
             'interrupted_pair':report['interrupted_pair'],
             'interruption_limitation':'changed-arithmetic round0 retains measured ratio only as noncontiguous diagnostic; exclude it from continuous94 comparison; do not treat it as evidence of continuous speedup',
             'decision':'do not promote; mixed full-cohort performance, negative and short tasks retained; no native/official85 score or pure branch-dispatch gain inference',
             'compute_includes':'decode and per-execution fullCFG LOAD-pair discovery+dispatch; original main compute timer unchanged',
             'external_costs':'each trial raw Metadata/input/output IO, process wall, separate fresh source/input/oracle/EXE SHA and full byte comparison retained; no observer timings',
             'host_scope':'user programs untouched; observed whole-host load includes probe/other programs; no whole-host idle assertion',
             'resources':{'fresh_available_RAM_min_bytes':min(g['available_RAM_bytes']for g in report['resource_gate_observations']),
                          'host_available_RAM_min_bytes':min(r['resource']['host_available_ram_min_bytes']for r in report['records']),
                          'host_busy_percent_min':min(r['resource']['host_busy_percent_during_process']for r in report['records']),
                          'host_busy_percent_max':max(r['resource']['host_busy_percent_during_process']for r in report['records']),
                          'process_PeakWS_max_bytes':max(r['resource']['process_peak_working_set_bytes']for r in report['records']),
                          'process_peak_commit_max_bytes':max(r['resource']['process_peak_commit_bytes']for r in report['records'])},
             'whole_originalC_bytes':sum(r['wholeC']['bytes_compared']for r in report['records']),
             'canonical_CLI_PC':'not exported, actual trial field is null/unavailable; actual PC parity proved separately by54 functional observer, not by expected PC or copied oracle result',
             'runtime_sha256':plan['runtime']['sha256'],'candidate_source_vs_baseline':'workspace is matching-a95 candidate; source-before is old844 before LOAD+LOAD, not a sameflags performance comparator'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    files={}
    for relative,origin in origins.items():
        p=out/relative;digest=sha(p);assert sha(origin)==digest
        files[relative]={'origin':str(origin),'sha256':digest,'bytes':p.stat().st_size}
    files['summary.json']={'origin':'new factual static summary from unchanged actual report','sha256':sha(out/'summary.json'),'bytes':(out/'summary.json').stat().st_size}
    manifest={'schema':'load-pair-same-a95-cost-final-acceptance-v1','passed':True,
              'initial_plan_sha256':sha(R/'performance-plan/plan.json'),
              'initial_failed_report_sha256':sha(R/'performance-evidence/report.json'),
              'continuation_plan_sha256':sha(R/'performance-continuation-plan/plan.json'),
              'actual_passed_report_sha256':sha(R/'performance-continuation-evidence/report.json'),
              'functional_acceptance_sha256':sha(R/'functional-acceptance/manifest.json'),
              'summary_sha256':sha(out/'summary.json'),'actual_runtime_sha256':sha(out/'matching-build/cholesky_runtime.exe'),
              'core_sha256':sha(out/'matching-build/libcholesky_core.a'),'ABI_header_sha256':sha(out/'workspace/include/cholesky/runtime.hpp'),
              'ordinary_sha256':sha(P/'build/cholesky_runtime.exe'),'memory_sha256':sha(P/'build-memory/cholesky_runtime.exe'),
              'records':190,'all_planned_pairs':95,'continuous_pairs':94,'default_promotion':False,'files':files}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'manifest':str(out/'manifest.json'),'sha256':sha(out/'manifest.json'),'frozen_files':len(files),
                      'summary_sha256':sha(out/'summary.json'),'snapshot_bytes':sum(i['bytes']for i in files.values()),
                      'ordinary_sha256':manifest['ordinary_sha256'],'memory_sha256':manifest['memory_sha256']}),flush=True)
if __name__=='__main__':main()
