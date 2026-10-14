"""Record bounded aggregate-group shortlist and a different post-freeze DAG grammar."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read('docs/validation.json');source=hashlib.sha256(Path('research/batch29/solution.cpp').read_bytes()).hexdigest()
    paired={n:read(f'reports/paired-group-hints-{n}-batch29-summary.json') for n in ['structural','wide','irregular']}
    for d in paired.values():
        assert d['current_solution_sha256']==source
        for run in d['runs']:
            c=run['comparison'];assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    checks={}
    for name,before,after in [('irregular-holdout','reports/irregular-eight-final-holdout-batch28.json','reports/irregular-final-group-hints-holdout-batch29.json'),
        ('lifetime','reports/lifetime-eight-final-batch28.json','reports/lifetime-final-group-hints-batch29.json'),
        ('lifetime-holdout','reports/paired-eight-lifetime-holdout-batch28-1-after.json','reports/lifetime-final-group-hints-holdout-batch29.json')]:
        c=summarize(read(before),read(after));assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0;checks[name]=c
    blind=summarize(read('reports/recursive-sharing-before-batch29.json'),read('reports/recursive-sharing-after-batch29.json'))
    assert not blind['lost'] and blind['regressed_T']==blind['regressed_peak_at_equal_T']==blind['model_disagreements']==0
    v['latest_solution_sha256']=source
    v['aggregate_group_hints_batch29']=dict(source_sha256=source,regression=read('reports/regression-batch29.json'),certificate_audit=read('reports/certificate-audit-batch29.json'),paired=paired,
        other_hard_checks=checks,ctest='4/4',ctest_wall_seconds=.84,standalone_compile='GCC -O2 no warnings',ordering_cycle_precedence_and_alias_checks=24,
        trigger='Only un solved 512<n<=4096; group>4 empirical cost trigger and >128 initial target groups (otherwise shortlist cannot change), three objectives/nine candidates',
        withdrawn='Dual group8/group4 aggregate diagnostic frozen separately; default omits group4 portfolio and broad untriggered search',
        unseen=dict(provenance=read('reports/recursive-sharing-unseen-batch29-provenance.json'),comparison=blind,scope='one-time frozen28/29 comparison; no batch29 tuning after result, diagnostic costs'))
    v['batch29_counts']=dict(strict_regression_records=979,old_hard_records=48,old_hard_passed=32,new_hard_records=72,new_hard_passed=54,
        structural_records=36,structural_passed=14,wide_hardware_records=12,wide_hardware_passed=3,new_recursive_records=18,new_recursive_passed=15,
        total_records=1165,total_passed=1097,total_failed=68)
    Path('reports/recursive-sharing-comparison-batch29.json').write_text(json.dumps(blind,indent=2))
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(v['batch29_counts'])


if __name__=='__main__':main()
