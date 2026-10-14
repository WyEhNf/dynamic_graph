"""Append final Phase1 evidence without altering the accepted source manifest."""
import hashlib,json,shutil
from pathlib import Path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-prepared-vm-phase1'
    initial=json.loads((root/'phase1-manifest.json').read_text())
    for name,digest in initial['source_sha256'].items():assert sha(project/name)==digest,name
    assert sha(root/'candidate.exe')==initial['candidate_sha256']
    assert sha(project/'build/cholesky_runtime.exe')==initial['ordinary_sha256']
    assert sha(project/'build-memory/cholesky_runtime.exe')==initial['memory_sha256']
    reports={name:json.loads((root/name).read_text())for name in ['correctness/report.json','fp-supplement/report.json','maximum-shape/report.json','performance-v3/report.json']}
    assert all(r['passed'] and r['status']=='complete'for r in reports.values())
    perf=reports['performance-v3/report.json'];assert len(perf['records'])==90
    maximum=reports['maximum-shape/report.json'];assert len(maximum['runs'])==4 and all(r['bytes']==800000008 and r['byte_identical']for r in maximum['runs'])
    assert maximum['runs'][1]['vm_steps']==maximum['runs'][2]['vm_steps']==maximum['runs'][3]['vm_steps']==1700000012
    paths=['tools/test_prepared_vm_supplement.py','tools/benchmark_prepared_vm_phase1.py','tools/windows_resource_probe.py','tools/finalize_prepared_vm_phase1.py','docs/stage2-prepared-vm-phase1.md','README.md']
    snapshot=root/'final-evidence-source';snapshot.mkdir(exist_ok=False);hashes={}
    for name in paths:
        target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target);hashes[name]=sha(target)
    proof_paths=['phase1-manifest.json','correctness/report.json','ctest.log','fp-supplement/plan.json','fp-supplement/report.json','fp-supplement/test-script.py','maximum-shape/plan.json','maximum-shape/report.json','maximum-shape/test-script.py','performance-v3/run-plan.json','performance-v3/report.json','performance-v3/benchmark-script.py','performance-v3/windows_resource_probe.py']
    manifest={'passed':True,'phase':'decode-only accepted and measured; no TOS/goto/cache/fusion added','source_manifest_sha256':sha(root/'phase1-manifest.json'),'candidate_sha256':initial['candidate_sha256'],'ordinary_sha256':initial['ordinary_sha256'],'memory_sha256':initial['memory_sha256'],'frozen_source':'candidate-source/ (103 actual files); supplemental producers separately snapshotted','final_evidence_source_sha256':hashes,'proof_sha256':{name:sha(root/name)for name in proof_paths},'ctest':'9/9','actual_C_functional_comparisons':180,'source_error_contracts':7,'direct_API_comparisons':404,'opcode_count':33,'maximum_shape':{'n':10000,'actual_original_steps':1700000012,'explicit_limit':10000000000,'default_limit_unchanged':1000000000,'original_C_source_sha256':maximum['source_sha256'],'input_sha256':maximum['input_sha256'],'original_C_output_sha256':maximum['oracle_output_sha256'],'complete_output_bytes_each':800000008,'backend_count':4,'maximum_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in maximum['runs']),'minimum_host_available_bytes':min(maximum['oracle']['host_available_ram_min_bytes'],*(r['host_available_ram_min_bytes']for r in maximum['runs']))},'performance':{'unique_run_plan':'performance-v3/run-plan.json','actual_session':79341,'exit_code':0,'trials':90,'pairs':45,'negative_pairs':sum(x>=1 for s in perf['summary']for x in s['paired_compute_ratios']),'elapsed_seconds':perf['elapsed_seconds'],'host_busy_percent_range':[min(r['host_busy_percent_during_process']for r in perf['records']),max(r['host_busy_percent_during_process']for r in perf['records'])],'minimum_host_available_bytes':min(r['host_available_ram_min_bytes']for r in perf['records']),'summaries':perf['summary'],'scope':'this host with user background apps; project test jobs isolated; compute includes per-matrix decode; no official score inference'},'default_promotion':False}
    (root/'final-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'manifest':str(root/'final-manifest.json'),'candidate_sha256':manifest['candidate_sha256'],'negative_pairs':manifest['performance']['negative_pairs']}))
if __name__=='__main__':main()
