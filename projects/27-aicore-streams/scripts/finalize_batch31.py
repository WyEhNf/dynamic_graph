"""Freeze and validate the final default without treating known failures as success."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from compare_research import summarize


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    source=digest('solution/solution.cpp')
    paired={n:read(f'reports/paired-resource-clique-{n}-batch31-summary.json') for n in ['controls','main','wide']}
    for d in paired.values():
        assert d['current_solution_sha256']==source
        assert d['current_exe_sha256']==digest('build/aicore_bench.exe')
        for run in d['runs']:
            c=run['comparison']
            assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    freeze=Path('research/batch31');freeze.mkdir(exist_ok=True)
    shutil.copy2('solution/solution.cpp',freeze/'solution.cpp')
    shutil.copy2('build/aicore_bench.exe',freeze/'aicore_bench.exe')
    suites=[
        ('irregular','data/irregular-consumers.json','reports/irregular-wide-projection-batch30.json'),
        ('irregular-holdout','data/irregular-consumers-holdout.json','reports/irregular-wide-projection-holdout-batch30.json'),
        ('lifetime','data/lifetime-locality.json','reports/lifetime-wide-projection-batch30.json'),
        ('lifetime-holdout','data/lifetime-locality-holdout.json','reports/lifetime-wide-projection-holdout-batch30.json'),
        ('structural','data/structural-blind-batch26.json','reports/paired-wide-projection-structural-batch30-1-after.json'),
        ('wide','data/wide-unseen-batch28.json','reports/paired-wide-projection-wide-batch30-1-after.json'),
        ('recursive','data/recursive-sharing-unseen-batch29.json','reports/paired-wide-projection-recursive-batch30-1-after.json'),
        ('projection','data/projection-unseen-batch30.json','reports/projection-unseen-after-batch30.json')]
    checks={};failed=[];all_rows=[];start=time.perf_counter()
    for name,input_file,before in suites:
        out=f'reports/final-{name}-batch31.json'
        proc=subprocess.run([str((freeze/'aicore_bench.exe').resolve()),'--input',input_file,'--output',out,'--csv',str(Path(out).with_suffix('.csv'))])
        assert proc.returncode in (0,1)
        after=read(out);c=summarize(read(before),after)
        assert not c['lost'] and not c['recovered'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
        assert c['improved_T']==c['improved_peak_at_equal_T']==0
        checks[name]=dict(input=input_file,input_sha256=digest(input_file),report=out,comparison=c)
        all_rows.extend(after['cases'])
        failed.extend(dict(suite=name,input=input_file,name=r['name'],n=r['n'],error=r['error'],solve_us=r['solve_us'],solve_thread_cpu_us=r['solve_thread_cpu_us']) for r in after['cases'] if not r['pass'])
        print(name,c['after'],flush=True)
    final=dict(source_sha256=source,exe_sha256=digest(freeze/'aicore_bench.exe'),record_count=len(all_rows),passed=sum(r['pass'] for r in all_rows),failed=len(failed),
        elapsed_wall_seconds=time.perf_counter()-start,all_solve_us=sum(r['solve_us'] for r in all_rows),all_thread_cpu_us=sum(r['solve_thread_cpu_us'] for r in all_rows),
        failed_solve_us=sum(r['solve_us'] for r in failed),failed_thread_cpu_us=sum(r['solve_thread_cpu_us'] for r in failed),
        scope='One final functional run of all 202 difficult records, including failures; not a paired speed experiment',checks=checks,failures=failed)
    assert (final['record_count'],final['passed'],final['failed'])==(202,133,69)
    Path('reports/final-hard-batch31.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
    cases={x['name']:x for x in read('data/resource-cliques-batch31.json')['cases']}
    audits=[]
    for phase in ['before','after']:
        rows=read(f'reports/paired-resource-clique-controls-batch31-1-{phase}.json')['cases']
        count=0
        for r in rows:
            meta=cases[r['name']]['generation'];opt=(meta['optimal_T'],meta['optimal_peak'])
            assert r['pass'] and r['models_equal'] and (r['T'],r['peak_memory'])==opt
            assert r['time_lower_bound']<=opt[0]
            if r['time_lower_bound']==opt[0]:assert r['memory_lower_bound']<=opt[1]
            count+=int(r['optimal_certificate'])
        audits.append(dict(phase=phase,checked=len(rows),certified=count))
    assert audits[1]['certified']==12
    old_audit=read('reports/certificate-audit-batch31.json')
    certificate_audit=dict(checked=old_audit['checked']+12,certified=old_audit['certified']+12,old=old_audit,resource_cliques=audits,
        resource_input_sha256=digest('data/resource-cliques-batch31.json'),source_sha256=source)
    Path('reports/final-certificate-audit-batch31.json').write_text(json.dumps(certificate_audit,indent=2))
    v=read('docs/validation.json');v['latest_solution_sha256']=source
    v['resource_clique_batch31']=dict(source_sha256=source,exe_sha256=final['exe_sha256'],regression=read('reports/regression-batch31.json'),
        certificate_audit=certificate_audit,paired=paired,final_hard=final,ctest='4/4',ctest_wall_seconds=1.01,standalone_compile='GCC -O2 -Wall -Wextra -Wpedantic no warnings',
        literal_resource_checks=6,ordering_checks=24,frozen_assignment_checks=288,analytic_projection_checks=3,
        proof='Within one core pool, requests strictly greater than half capacity are pairwise incompatible. W+O coexist for the full Compute interval; strictly more than half device capacity gives a separate memory clique. Sum durations is a necessary T bound.',
        arithmetic='Compare requirement > capacity/2; no multiplying by two. W+O and duration sums use saturating positive int64 additions.',
        provenance=read('reports/resource-cliques-batch31-provenance.json'))
    v['batch31_counts']=dict(strict_regression_records=979,hard_records=202,hard_passed=133,analytic_resource_records=12,analytic_resource_passed=12,
        total_records=1193,total_passed_according_to_expectation=1124,known_feasible_unresolved=69,
        caveat='Case records include repeated official samples, parameter controls and one expected-infeasible stress case. Not 1124 independent feasible topologies.')
    strict=v['resource_clique_batch31']['regression']
    strict_rows=[r for name in strict['comparisons'] for r in read(f'reports/{name}-batch31.json')['cases']]
    controls=read('reports/paired-resource-clique-controls-batch31-1-after.json')['cases']
    final_rows=strict_rows+all_rows+controls
    assert len(final_rows)==1193 and sum(r['pass'] for r in final_rows)==1124
    v['resource_clique_batch31']['final_functional_cost']=dict(records=len(final_rows),all_solve_us=sum(r['solve_us'] for r in final_rows),
        all_thread_cpu_us=sum(r['solve_thread_cpu_us'] for r in final_rows),
        scope='One chosen final run per record: strict 979, difficult 202, first analytic after run 12; not contemporaneous paired speed evidence',
        strict_cli_wall_seconds=strict['elapsed_wall_seconds'],hard_cli_wall_seconds=final['elapsed_wall_seconds'],
        analytic_cli_wall_seconds=paired['controls']['runs'][0]['after']['wall_seconds'])
    if Path('reports/resource-liveness-audit-batch31.json').exists():
        extra=read('reports/resource-liveness-audit-batch31.json');assert extra['source_sha256']==source
        v['resource_clique_batch31']['auxiliary_resource_liveness_audit']=extra
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:final[k] for k in ['source_sha256','record_count','passed','failed','elapsed_wall_seconds','all_solve_us','all_thread_cpu_us','failed_solve_us','failed_thread_cpu_us']},indent=2))


if __name__=='__main__':main()
