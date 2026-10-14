"""Freeze completed evidence and negative observations without replacing release."""
import json,shutil,statistics
from pathlib import Path
from datetime import datetime,timezone
from benchmark_grain48_stage2 import sha

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-avx512';target=root/'final-manifest.json'
    if target.exists():raise SystemExit('Completed AVX512 study already frozen')
    candidate=json.loads((root/'candidate-manifest.json').read_text());plan=json.loads((root/'performance/run-plan-v2.json').read_text());report=json.loads((root/'performance/performance.json').read_text())
    assert report['passed'] and report['status']=='complete' and len(report['records'])==60
    assert report['plan_sha256']==sha(root/'performance/run-plan-v2.json')
    assert candidate['runtime_sha256']==plan['runtime_sha256']==sha(root/'performance/runtime.exe')
    assert all(sha(project/k)==v for k,v in plan['source_sha256'].items())
    for row,step in zip(report['records'],plan['schedule']):
        assert all(row[k]==v for k,v in step.items()) and row['byte_identical']
        r=next(r for r in plan['references']if r['n']==step['n'])
        assert row['verified_before_trial_sha256']=={'input':r['input_sha256'],'original_c_output':r['oracle_sha256'],'original_c_source':r['source_sha256'],'metadata':plan['metadata_sha256'],'runtime':plan['runtime_sha256']}
    assert sha(project/'build/cholesky_runtime.exe')==candidate['ordinary_sha256']
    assert sha(project/'build-memory/cholesky_runtime.exe')==candidate['memory_sha256']
    derived=[]
    for group in plan['groups']:
        rows={m:next(r for r in report['summary']if all(r[k]==v for k,v in group.items())and r['simd']==m)for m in ('avx2','avx512')}
        pairs=[r['compute_ratio_avx512_over_avx2']for r in report['paired_ratios']if all(r[k]==v for k,v in group.items())]
        derived.append({**group,'avx2_compute_ms':rows['avx2']['compute_ms'],'avx512_compute_ms':rows['avx512']['compute_ms'],'median_compute_percent':100*(rows['avx512']['compute_ms']['median']/rows['avx2']['compute_ms']['median']-1),'paired_ratios':pairs,'paired_wins':sum(x<1 for x in pairs),'paired_losses':sum(x>=1 for x in pairs)})
    checks=[r['provenance_check_ms']for r in report['records']];frozen=root/'completed-source';files={}
    for name in ('README.md','docs/stage2-avx512.md','tools/benchmark_avx512_stage2.py','tools/finalize_avx512_stage2.py'):
        out=frozen/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,out);files[name]=sha(out)
    manifest={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'actual_session':45883,'actual_exit_code':0,'candidate_manifest_sha256':sha(root/'candidate-manifest.json'),'plan_v1_sha256':sha(root/'performance/run-plan.json'),'plan_v2_sha256':sha(root/'performance/run-plan-v2.json'),'performance_sha256':sha(root/'performance/performance.json'),'candidate_runtime_sha256':plan['runtime_sha256'],'ordinary_sha256':candidate['ordinary_sha256'],'memory_sha256':candidate['memory_sha256'],'source_sha256':plan['source_sha256'],'completed_doc_tool_sha256':files,'byte_comparisons':60,'each_trial_hash_verifications':60,'costs':{'total_batch_seconds':report['wall_seconds'],'separate_provenance_check_total_ms':sum(checks),'separate_provenance_check_median_ms':statistics.median(checks),'all_runtime_cost_fields':'Retained per trial in original performance.json, including compute/graph/kernel/export/inputvalidation/Metadata/input/output IO/wall; provenance checks and output comparison outside runtime costs'},'results':derived,'interpretation':'No consistent cross-shape/geometry gain:6145B128 negative22.75%;10000 median <1% gain with long-tail negative. Every pair/loss retained, no AUTO promotion or fitted threshold; optional research only. No official score inference.','cpu_window_released':True}
    target.write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'completed':True,'records':60,'paired_losses':sum(x['paired_losses']for x in derived),'default_changed':False}),flush=True)
if __name__=='__main__':main()
