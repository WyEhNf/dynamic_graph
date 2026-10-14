"""Audit complete old/fresh cost scope and small-N instruction-count predictions."""
import json,time
from pathlib import Path
from collections import Counter
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,read,sha
from review_stage2_vm_proved_integration import header

def main():
    d=D/'next-static-design';m=read(d/'plan.json')
    assert sha(d/'plan.json')=='c39c4ff7352e522d9de795008cbb8f4f80b3960f589d4df2e05c159c2d9bd59f'
    assert sha(D/'runtime-integration/acceptance/manifest.json')==m['accepted_manifest_sha256']
    assert sha(m['same_binary']['path'])==m['same_binary']['sha256']
    s=m['cost_scope'];assert (s['case_count'],s['VM_case_count'],s['native_case_count'],s['rounds_proposed'],s['records'],s['pairs'])==(29,23,6,3,174,87)
    assert len(s['cases'])==29 and len({x['source']for x in s['cases']})==29
    assert Counter(x['kind']for x in s['cases'])==dict(vm=23,native=6)
    frozen_paths=set();expected_steps=0
    for row in s['cases']:
        for name,path in row['paths'].items():assert sha(path)==row['hashes'][name];frozen_paths.add(path)
        assert header(Path(row['paths']['input.bin']))==row['input_matrix_headers']
        assert header(Path(row['paths']['oracle.bin']))==row['input_matrix_headers']
        assert len(row['input_matrix_headers'])==row['matrices'] and Path(row['paths']['oracle.bin']).stat().st_size==row['reference_bytes']
        expected_steps+=row['expected_vm_steps']
    actual=read(D/'runtime-integration/functional-evidence-continuation/report.json')['functional']
    formula={
      'nested-rect-strides':lambda n:9+17*(n//2)+30*(n//2)*((n+2)//3),
      'nested-triangular':lambda n:14*n*n+3*n+9,
      'nested-gram-three':lambda n:30*n*n*n+28*n*n+17*n+9}
    for source,f in formula.items():
        rows=[x for x in actual if x['source']==source and x['mode']=='fixed-auto'];assert len(rows)==2
        for row in rows:assert sum(f(n)for n in header(Path(row['input'])))==row['vm_steps']
    assert formula['nested-triangular'](10000)==1400030009>1000000000
    assert 28*10000**2-11*10000+9==2799890009
    assert formula['nested-rect-strides'](10000)==500185009<1000000000
    assert formula['nested-gram-three'](10000)==30002800170009
    large=m['large_functional_design'];assert not large['maximum_or_performance_execution_started']and large['strict_sequential']and large['speedup_claim_from_reject_vs_success_forbidden']
    assert large['minimum_new_output_disk_bytes_including512MiB_reserve']==2*800000008+512*1024**2
    assert sha(P/'build/cholesky_runtime.exe')==m['ordinary_runtime_sha256']and sha(P/'build-memory/cholesky_runtime.exe')==m['memory_runtime_sha256']
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(d/'plan.json'),cost_cases=29,VM_cases=23,native_cases=6,planned_actual_records=174,planned_pairs=87,existing_paths_checked=len(frozen_paths),small_shapes=[3,7,13,29,53],predicted_tri_N10000_actual_steps=1400030009,predicted_tri_N10000_bound=2799890009,authorization='Prepare frozen samebinary29case3round alternating cost runner and matchingABI analysis-only proof probe/scope first. Do not execute performance or highN VM/C/allocation until actualrunner/resource review; nolargeGram/default promotion.',scope='All original cached source/metadata/input/trueC/reference paths and matrix headers rechecked. Three fullPROGRAM count formulas independently match six actual dense/signedzero streams comprising30matrices; highN bounds remain predictions until analysis-only compiled proof. Maximumtri resource gate includes two800MBoutputs+512MiB reserve; omitted extra backendoutputs not authorized. Cost results must retain allnegative and proofwork, not infer official85speedup.')
    (ROOT/'outputs/stage2-root-vm-nested-next-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
