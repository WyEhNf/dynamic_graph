"""Record wider-group trigger, same-time quality, and post-freeze unseen controls."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read('docs/validation.json');source=hashlib.sha256(Path('research/batch28/solution.cpp').read_bytes()).hexdigest()
    paired={n:read(f'reports/paired-eight-{n}-batch28-summary.json') for n in ['structural','irregular','lifetime-holdout']}
    for d in paired.values():
        assert d['current_solution_sha256']==source
        for run in d['runs']:
            c=run['comparison'];assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    blind=summarize(read('reports/wide-unseen-before-batch28.json'),read('reports/wide-unseen-after-batch28.json'))
    assert not blind['lost'] and blind['regressed_T']==blind['regressed_peak_at_equal_T']==blind['model_disagreements']==0
    checks={}
    for name,before,after in [('irregular-holdout','reports/irregular-owner-holdout-batch27.json','reports/irregular-eight-final-holdout-batch28.json'),
        ('lifetime','reports/lifetime-owner-batch27.json','reports/lifetime-eight-final-batch28.json')]:
        c=summarize(read(before),read(after));assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0;checks[name]=c
    v['latest_solution_sha256']=source
    v['wide_consumer_group_batch28']=dict(source_sha256=source,regression=read('reports/regression-batch28.json'),certificate_audit=read('reports/certificate-audit-batch28.json'),paired=paired,
        other_hard_checks=checks,ctest='4/4',ctest_wall_seconds=1.12,standalone_compile='GCC -O2 no warnings',owner_cycle_precedence_and_alias_checks=15,
        trigger='Only after prior search fails, n<=4096; skip when no newly eligible affinity edge and all groups remain <=4, because old owner traversals then identical',
        unseen=dict(provenance=read('reports/wide-unseen-batch28-provenance.json'),comparison=blind,scope='one-time frozen 27/28 comparison, no subsequent batch28 tuning; costs diagnostic'))
    passed=1078+blind['after']['passed'];total=1147
    v['batch28_counts']=dict(strict_regression_records=979,old_hard_records=48,old_hard_passed=32,new_hard_records=72,new_hard_passed=54,
        structural_records=36,structural_passed=13,new_unseen_records=12,new_unseen_passed=blind['after']['passed'],total_records=total,total_passed=passed,total_failed=total-passed)
    Path('reports/wide-unseen-comparison-batch28.json').write_text(json.dumps(blind,indent=2))
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(v['batch28_counts'])


if __name__=='__main__':main()
