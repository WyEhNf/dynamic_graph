"""Freeze the actual single-compile/25-observation analysis-only evidence."""
import hashlib, json, shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
ROOT=STAGE/'analysis-only'
OUT=STAGE/'analysis-only-acceptance'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    plan=read(ROOT/'run-plan.json');report=read(ROOT/'report.json');compiled=read(ROOT/'compile-report.json')
    assert compiled['passed']and compiled['actual_exit_code']==0 and report['passed']and len(report['records'])==25
    assert not OUT.exists();OUT.mkdir();files={}
    def copy(source,relative):
        dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        files[relative]={'origin':str(source),'sha256':sha(source),'bytes':source.stat().st_size}
        assert sha(dest)==files[relative]['sha256']
    for source in sorted(ROOT.rglob('*')):
        if source.is_file():copy(source,source.relative_to(ROOT).as_posix())
    for source in [Path(__file__)]:copy(source,'freeze-source/'+source.relative_to(P).as_posix())
    sources={}
    for case in plan['cases']:
        assert sha(case['source_C_path'])==case['source_C_sha256']
        sources[case['source']]=Path(case['source_C_path'])
    for label,source in sources.items():copy(source,'actual-C-sources/'+label+'.c')
    summaries=[]
    for label in sources:
        rows=[r for r in report['records']if r['source']==label]
        summaries.append({'source':label,'observations':len(rows),'first_proved':sum(r['first_proved']for r in rows),
                          'nested_proved':sum(r['nested_proved']for r in rows),'unknown':sum(not r['proved']for r in rows),
                          'bound_by_N':{str(r['N']):r['bound']for r in rows},
                          'shared_work_values':sorted(set(r['shared_work']for r in rows)),
                          'proof_ms_range':[min(r['proof_ms']for r in rows),max(r['proof_ms']for r in rows)],
                          'minimum_available_RAM_bytes':min(r['host_available_ram_min_bytes']for r in rows),
                          'maximum_process_PeakWS_bytes':max(r['process_peak_working_set_bytes']for r in rows)})
    manifest={'schema':'optional-nested-VM-analysis-only-acceptance-v1','passed':True,'frozen_files':files,
              'source_prepare_manifest_sha256':sha(STAGE/'next-prepared/manifest.json'),
              'plan_sha256':sha(ROOT/'run-plan.json'),'report_sha256':sha(ROOT/'report.json'),
              'compile_report_sha256':sha(ROOT/'compile-report.json'),'EXE_sha256':compiled['EXE_sha256'],
              'actual_compile_attempts':1,'actual_compile_exit_code':0,'actual_analysis_exit_code':0,
              'observations':25,'positive_bounds':15,'unknown_unchanged':10,'summary':summaries,
              'new_ABI':plan['ABI'],'Matrix_allocations_or_C_VM_native_executions':0,
              'not_large_shape_whole_C_or_output_acceptance':True,'cost_batch_started':False,
              'ordinary_changed':False,'ordinary_sha256':plan['ordinary_sha256'],'memory_sha256':plan['memory_sha256']}
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'manifest_sha256':sha(OUT/'manifest.json'),'frozen_files':len(files),'observations':25,'cost_started':False}),flush=True)

if __name__=='__main__':main()
