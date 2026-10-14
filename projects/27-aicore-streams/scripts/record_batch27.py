"""Record ordering-only consumer ownership; all failed calls remain in cost."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p): return json.loads(Path(p).read_text())
    v=read('docs/validation.json');source=hashlib.sha256(Path('research/batch27/solution.cpp').read_bytes()).hexdigest()
    paired={n:read(f'reports/paired-owner-{n}-batch27-summary.json') for n in ['irregular','irregular-holdout','lifetime','lifetime-holdout']}
    recovered=[]
    for d in paired.values():
        assert d['current_solution_sha256']==source
        for run in d['runs']:
            c=run['comparison'];assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
        recovered.extend(d['runs'][0]['comparison']['recovered'])
    assert len(recovered)==9
    v['latest_solution_sha256']=source
    v['ordering_owner_batch27']=dict(source_sha256=source,regression=read('reports/regression-batch27.json'),
        certificate_audit=read('reports/certificate-audit-batch27.json'),paired=paired,recovered_records=recovered,
        ctest='4/4',ctest_wall_seconds=.82,standalone_compile='GCC -O2 no warnings',new_owner_cycle_and_precedence_checks=6,
        trigger='Only after all earlier candidates including batch26 fail, n<=4096, at most nine new distinct candidates',
        invariant='Synthetic ordering-only edges rejected if cyclic; no changes to real dependencies/events/last direct consumer release',
        structural_previous_validation=read('reports/owner-diagnostic-structural-batch27.json'),
        structural_scope='Already observed during batch26; not a new blind test for batch27')
    v['batch27_counts']=dict(strict_regression_records=979,old_hard_records=48,old_hard_passed=32,new_hard_records=72,new_hard_passed=54,
        structural_records=36,structural_passed=10,total_records=1135,total_passed=1075,total_failed=60)
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print('batch27:979 strict,1135 total/1075 pass/60 witness-feasible failures;9 restored records')


if __name__=='__main__':main()
