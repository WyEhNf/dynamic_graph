"""Record consumer-group recovery separately from common quality and all-call cost."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p): return json.loads(Path(p).read_text())
    v = read('docs/validation.json')
    source = hashlib.sha256(Path('research/batch26/solution.cpp').read_bytes()).hexdigest()
    paired = {n: read(f'reports/paired-grouped-{n}-batch26-summary.json')
              for n in ['irregular', 'irregular-holdout', 'lifetime', 'lifetime-holdout']}
    recovered = []
    for d in paired.values():
        assert d['current_solution_sha256'] == source
        for run in d['runs']:
            c = run['comparison']
            assert not c['lost'] and not c['regressed_T'] and not c['regressed_peak_at_equal_T'] and not c['model_disagreements']
        recovered.extend(d['runs'][0]['comparison']['recovered'])
    assert len(recovered) == 5
    v['latest_solution_sha256'] = source
    v['consumer_group_batch26'] = dict(source_sha256=source, regression=read('reports/regression-batch26.json'),
        certificate_audit=read('reports/certificate-audit-batch26.json'), paired=paired,
        recovered_records=recovered, ctest='4/4', ctest_wall_seconds=3.37,
        standalone_compile='GCC -O2 -Wall -Wextra -Wpedantic, no warnings',
        trigger='Only when all earlier candidates have failed, n<=4096; at most nine new distinct candidates',
        scope='Both historical seed sets were inspected during development; not a blind test.',
        correct_ablation=dict(report='reports/ancestor-limit-ablation-batch26.json', restored=0, records=48,
            interpretation='Same new budget/objectives and 128-ancestor cap, without groups, restores none of previously failed records; selected diagnostic subset only.'),
        exclusions=['Misrouted ablation switched the old call: retained as ancestor-limit-misrouted-diagnostic-batch26, excluded from ablation conclusion.',
            'Restoring a frozen source preserved an old timestamp and CMake initially reused the ablation object. Partial stale pipeline interrupted before completed formal reports. Source touched and compile/link confirmed before final formal pipeline.'])
    v['batch26_counts'] = dict(strict_regression_records=979, old_hard_records=48, old_hard_passed=30,
        new_hard_records=72, new_hard_passed=47, total_records=1099, total_passed=1056, total_failed=43)
    Path('docs/validation.json').write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8')
    print('batch26:979 strict;1099 total/1056 pass/43 witness-feasible failures;5 restored records')


if __name__ == '__main__': main()
