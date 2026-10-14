"""Record bounded >72-sink projection and independent duration validation."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read('docs/validation.json');source=hashlib.sha256(Path('research/batch30/solution.cpp').read_bytes()).hexdigest()
    paired={n:read(f'reports/paired-wide-projection-{n}-batch30-summary.json') for n in ['wide','structural','recursive']}
    for d in paired.values():
        assert d['current_solution_sha256']==source
        for run in d['runs']:
            c=run['comparison'];assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0
    checks={}
    for n,before,after in [('irregular','reports/paired-group-hints-irregular-batch29-1-after.json','reports/irregular-wide-projection-batch30.json'),
        ('irregular-holdout','reports/irregular-final-group-hints-holdout-batch29.json','reports/irregular-wide-projection-holdout-batch30.json'),
        ('lifetime','reports/lifetime-final-group-hints-batch29.json','reports/lifetime-wide-projection-batch30.json'),
        ('lifetime-holdout','reports/lifetime-final-group-hints-holdout-batch29.json','reports/lifetime-wide-projection-holdout-batch30.json')]:
        c=summarize(read(before),read(after));assert not c['lost'] and c['regressed_T']==c['regressed_peak_at_equal_T']==c['model_disagreements']==0;checks[n]=c
    blind=summarize(read('reports/projection-unseen-before-batch30.json'),read('reports/projection-unseen-after-batch30.json'))
    assert not blind['lost'] and blind['regressed_T']==blind['regressed_peak_at_equal_T']==blind['model_disagreements']==0
    v['latest_solution_sha256']=source
    v['wide_sink_projection_batch30']=dict(source_sha256=source,regression=read('reports/regression-batch30.json'),certificate_audit=read('reports/certificate-audit-batch30.json'),paired=paired,
        other_hard_checks=checks,ctest='4/4',ctest_wall_seconds=.84,standalone_compile='GCC -O2 no warnings',ordering_checks=24,analytic_wide_projection_checks=3,
        trigger='Only previously unsolved n<=512 with 73..144 sinks; <=8 members/group, <=18 groups, eight-million elementary work cap',
        invariant='Partition only orders closures; direct user counts determine release; mask state is exact for completed closure sets, not complete over all serial node orders',
        unseen=dict(provenance=read('reports/projection-unseen-batch30-provenance.json'),comparison=blind,scope='one-time frozen29/30, no tuning from result; distinct seeds for two duration profiles'))
    v['batch30_counts']=dict(strict_regression_records=979,old_hard_records=48,old_hard_passed=32,new_hard_records=72,new_hard_passed=54,
        structural_records=36,structural_passed=14,wide_hardware_records=12,wide_hardware_passed=5,recursive_records=18,recursive_passed=15,
        new_projection_records=16,new_projection_passed=13,total_records=1181,total_passed=1112,total_failed=69)
    Path('reports/projection-unseen-comparison-batch30.json').write_text(json.dumps(blind,indent=2))
    Path('docs/validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(v['batch30_counts'])


if __name__=='__main__':main()
