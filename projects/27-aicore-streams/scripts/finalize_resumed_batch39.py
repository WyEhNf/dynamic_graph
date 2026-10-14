"""Freeze a tested milestone; never overwrite old R31/R36 evidence."""
import hashlib,json,shutil,statistics
from pathlib import Path
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    source=sha('solution/solution.cpp');strict=read('reports/regression-batch39.json');hard=read('reports/paired-hard-batch39-summary.json');new=read('reports/paired-forkjoin-batch39-summary.json')
    assert source==sha('research/batch39/solution.cpp')==strict['source_sha256']==hard['current_solution_sha256']==new['current_solution_sha256']
    assert hard['current_exe_sha256']==new['current_exe_sha256']==sha('build/aicore_bench.exe')
    for pair,passed,failed,common,recovered in [(hard,139,63,137,2),(new,36,0,14,22)]:
        for r in pair['runs']:
            c=r['comparison'];assert c['after']==dict(total=passed+failed,passed=passed,failed=failed)
            assert c['common_cases']==common and len(c['recovered'])==recovered and not c['lost']
            assert c['improved_T']==c['regressed_T']==c['improved_peak_at_equal_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    controls=read('reports/resource-cliques-batch39.json');inp={c['name']:c for c in read('data/resource-cliques-batch31.json')['cases']}
    for c in controls['cases']:
        expected=inp[c['name']]['generation'];assert c['pass'] and c['valid'] and c['models_equal'] and c['optimal_certificate']
        assert (c['T'],c['peak_memory'])==(expected['optimal_T'],expected['optimal_peak'])
    audit=read('reports/certificate-audit-batch39.json');assert audit['source_sha256']==source and audit['checked']==132
    rows=read(hard['runs'][0]['after']['report'])['cases'];failed=[c for c in rows if not c['pass']];assert len(failed)==63
    costs={}
    for label,side,names in [('before_fail65','before',None),('after_fail63','after',None),('common_fail63_before','before',{x['name'] for x in failed}),('common_fail63_after','after',{x['name'] for x in failed})]:
        for metric in ['solve_us','solve_thread_cpu_us']:
            vals=[]
            for run in hard['runs']:
                chosen=read(run[side]['report'])['cases'];subset=[x for x in chosen if (x['name'] in names if names else not x['pass'])]
                vals.append(sum(x[metric] for x in subset))
            costs[label+'_'+metric]=statistics.median(vals)
    shutil.copy2('build/aicore_bench.exe','research/batch39/default-aicore_bench.exe')
    freeze=dict(status='validated_default_milestone',source_sha256=source,default_exe_sha256=sha('research/batch39/default-aicore_bench.exe'),
        strict_records=979,hard_records=202,hard_legal=139,hard_unresolved=63,analytic_records=12,new_structure_records=36,
        total_records=1229,total_passed_according_to_expectation=1166,expected_infeasible_records=1,
        original_1193_passed_according_to_expectation=1130,new_structure_legal=36,new_structure_baseline_legal=14,
        count_caveat='Records include shared samples and repeated parameters; not 1166 independent feasible topologies.',
        optimum_audit_checked=144,certificates=33,additional_memory_subset_oracles=12,ctest='5/5 passed, 0.99s',serial_checks=1120,
        standalone='GCC15.2 -std=c++17 -O2 -Wall -Wextra -Wpedantic no warnings',paired_hard='reports/paired-hard-batch39-summary.json',
        paired_new='reports/paired-forkjoin-batch39-summary.json',failed_search_costs=costs,
        unresolved=[dict(name=c['name'],n=c['n'],error=c['error']) for c in failed],
        algorithm='R36 plus late bounded inner safe-consumer normalization; strict nested fork/join contiguous-block profile candidate before new frontier failures.',
        structural_limit='Whole graph must match all original entry/exit edges; no dominant/global serial optimum claim. Recognition linear; vector order concatenation O(n*depth), depth capped512/n4096.',
        unsupported='No complete hidden-graph guarantee, real NPU, official package or official wall/RAM limit; no third-party submission dependency.')
    Path('research/batch39/provenance.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    Path('reports/final-hard-batch39.json').write_text(json.dumps(freeze|dict(paired_hard=hard,paired_new=new,strict=strict,audit=audit),indent=2),encoding='utf-8')
    v=read('docs/validation.json');v['latest_solution_sha256']=source;v['resumed_batch39']=freeze|dict(paired_hard_summary=hard,paired_new_summary=new,strict_regression=strict)
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:freeze[k] for k in ['source_sha256','default_exe_sha256','total_records','total_passed_according_to_expectation','hard_legal','hard_unresolved']}))
if __name__=='__main__':main()
