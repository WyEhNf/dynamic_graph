"""Freeze this milestone independently of all old R31 artifacts."""
import hashlib
import json
import shutil
import statistics
from pathlib import Path

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    source=sha('solution/solution.cpp');pair=read('reports/paired-hard-batch36-summary.json');strict=read('reports/regression-batch36.json')
    assert source==pair['current_solution_sha256']==strict['source_sha256']==sha('research/batch36/solution.cpp')
    assert pair['current_exe_sha256']==sha('build/aicore_bench.exe')
    for run in pair['runs']:
        c=run['comparison'];assert c['after']==dict(total=202,passed=137,failed=65)
        assert c['common_cases']==133 and len(c['recovered'])==4 and not c['lost']
        assert c['improved_T']==c['regressed_T']==c['improved_peak_at_equal_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    controls=read('reports/resource-cliques-batch36.json');inp={c['name']:c for c in read('data/resource-cliques-batch31.json')['cases']}
    for c in controls['cases']:
        expected=inp[c['name']]['generation'];assert c['pass'] and c['valid'] and c['models_equal'] and c['optimal_certificate']
        assert (c['T'],c['peak_memory'])==(expected['optimal_T'],expected['optimal_peak'])
    audit=read('reports/certificate-audit-batch36.json');assert audit['source_sha256']==source and audit['checked']==132
    chosen=read(pair['runs'][0]['after']['report']);failed=[c for c in chosen['cases'] if not c['pass']]
    assert len(failed)==65
    shutil.copy2('build/aicore_bench.exe','research/batch36/default-aicore_bench.exe')
    costs={}
    for group in ['before_fail69','after_fail65','common_fail65_before','common_fail65_after']:
        for metric in ['solve_us','solve_thread_cpu_us']:
            values=[]
            for run in pair['runs']:
                before=read(run['before']['report'])['cases'];after=read(run['after']['report'])['cases'];names={c['name'] for c in after if not c['pass']}
                rows=before if group.endswith('before') or group=='before_fail69' else after
                subset=[c for c in rows if (c['name'] in names if group.startswith('common') else not c['pass'])]
                values.append(sum(c[metric] for c in subset))
            costs[group+'_'+metric]=statistics.median(values)
    freeze=dict(status='validated_default_milestone',source_sha256=source,default_exe_sha256=sha('research/batch36/default-aicore_bench.exe'),
        candidate_exe_sha256=sha('research/batch36/aicore_bench.exe'),strict_records=979,hard_records=202,hard_legal=137,hard_unresolved=65,
        analytic_records=12,total_records=1193,total_passed_according_to_expectation=1128,expected_infeasible_records=1,
        count_caveat='Records include shared samples and repeated parameters, not 1128 independent feasible topologies',
        optimum_audit_checked=144,certificates=33,ctest='5/5 passed, 1.45s',standalone='GCC15.2 -std=c++17 -O2 -Wall -Wextra -Wpedantic no warnings',
        paired='reports/paired-hard-batch36-summary.json',failed_search_costs=costs,
        unresolved=[dict(name=c['name'],n=c['n'],error=c['error']) for c in failed],
        new_method='Recovery-only <=768-node bounded greedy consumer macros; single then affinity pair; actual Event evaluation decides legality',
        unsupported='No complete hidden-graph guarantee, real NPU, official package or official wall/RAM limit; CP-SAT external serial oracle only')
    Path('research/batch36/provenance.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    Path('reports/final-hard-batch36.json').write_text(json.dumps(freeze|dict(pair=pair,strict=strict,controls=controls['summary'],audit=audit),indent=2),encoding='utf-8')
    v=read('docs/validation.json');v['latest_solution_sha256']=source;v['resumed_batch36']=freeze
    v['resumed_batch36']['paired_summary']=pair;v['resumed_batch36']['strict_regression']=strict
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:freeze[k] for k in ['source_sha256','default_exe_sha256','total_records','total_passed_according_to_expectation','hard_legal','hard_unresolved','ctest']}))

if __name__=='__main__':main()
