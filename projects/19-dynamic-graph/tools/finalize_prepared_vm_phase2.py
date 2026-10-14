"""Preserve all negative TOS2 data; no rewrite of the initial candidate freeze."""
import hashlib,json,shutil
from pathlib import Path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-prepared-vm-phase2';initial=json.loads((root/'candidate-manifest.json').read_text());perf=json.loads((root/'performance/report.json').read_text());proof=json.loads((root/'correctness/report.json').read_text())
    assert perf['passed'] and perf['status']=='complete' and len(perf['records'])==120
    assert proof['passed'] and proof['comparisons']==290
    for name,digest in initial['source_sha256'].items():assert sha(p/name)==digest,name
    assert sha(root/'candidate.exe')==initial['candidate_sha256'] and sha(root/'phase1-baseline.exe')==initial['phase1_baseline_sha256']
    assert sha(p/'build/cholesky_runtime.exe')==initial['ordinary_sha256'] and sha(p/'build-memory/cholesky_runtime.exe')==initial['memory_sha256']
    plan_digest=sha(root/'performance/run-plan.json');assert plan_digest=='77501a71459508a7a9beb77a8723382e18262d7c4f91119876f7c3d96f12ee5b'
    negatives=sum(x>=1 for s in perf['summary']for x in s['paired_compute_ratios']);assert negatives==60
    snapshot=root/'final-evidence-source';snapshot.mkdir(exist_ok=False);hashes={}
    for name in ['tools/finalize_prepared_vm_phase2.py','tools/freeze_prepared_vm_phase2.py','tools/test_prepared_vm_tos2_stage2.py','tools/benchmark_prepared_vm_tos2.py','docs/stage2-prepared-vm-phase2.md','README.md']:
        target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/name,target);hashes[name]=sha(target)
    proof_names=['initial-plan.json','candidate-manifest.json','correctness/report.json','ctest.log','performance/run-plan.json','performance/corpus-provenance.json','performance/report.json','performance/benchmark-script.py','performance/windows_resource_probe.py']
    manifest={'passed':True,'meaning':'functional contract and complete benchmark finished; TOS2 performance is negative','phase':'2 TOS2 only; no goto/fusion/Metadata plan cache; no default promotion','candidate_sha256':initial['candidate_sha256'],'phase1_baseline_sha256':initial['phase1_baseline_sha256'],'ordinary_sha256':initial['ordinary_sha256'],'memory_sha256':initial['memory_sha256'],'frozen_source_manifest_sha256':sha(root/'candidate-manifest.json'),'source_snapshot':'candidate-source/ 111 actual files','final_evidence_source_sha256':hashes,'proof_sha256':{name:sha(root/name)for name in proof_names},'functional':initial['correctness'],'performance':{'actual_session':45560,'exit_code':0,'unique_run_plan_sha256':plan_digest,'records':120,'pairs':60,'negative_pairs':negatives,'elapsed_seconds':perf['elapsed_seconds'],'host_busy_percent_range':[min(r['host_busy_percent_during_process']for r in perf['records']),max(r['host_busy_percent_during_process']for r in perf['records'])],'minimum_host_available_bytes':min(r['host_available_ram_min_bytes']for r in perf['records']),'SHA_validation_total_ms':sum(r['sha_validation_ms']for r in perf['records']),'whole_file_comparison_total_ms':sum(r['whole_file_comparison_ms']for r in perf['records']),'scope':'same3230 EXE decoded/TOS2; host user background apps active; all 12 sources/60pairs retained; per-matrix decode remains inside compute','summaries':perf['summary']},'default_promotion':False,'N10000':'prior phase1 copy succeeded only explicit1e10 for1.7b originalsteps; no TOS2 maximum-shape claim'}
    (root/'final-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'negative_pairs':negatives,'candidate_sha256':initial['candidate_sha256'],'manifest':str(root/'final-manifest.json')}))
if __name__=='__main__':main()
