"""Recompute every R43 paired cost from actual per-case before/after reports."""
import hashlib
import json
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/27-aicore-streams'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


results = {}
evidence = {}
for family, expected, legal in (('hard',202,139),('forkjoin',36,36)):
    summary_path = PROJECT / f'reports/paired-{family}-batch43-summary.json'
    summary = read(summary_path)
    evidence[str(summary_path.relative_to(ROOT))] = sha(summary_path)
    assert len(summary['runs']) == 3
    assert sha(PROJECT / summary['suite']) == summary['suite_sha256']
    assert sha(PROJECT / summary['current_solution_path']) == summary['current_solution_sha256']
    assert sha(PROJECT / summary['baseline_solution_path']) == summary['baseline_solution_sha256']
    assert sha(PROJECT / 'research/batch42/default-aicore_bench.exe') == summary['baseline_exe_sha256']
    assert sha(PROJECT / 'research/batch43/default-style-aicore_bench.exe') == summary['current_exe_sha256']
    rows = []
    for run in summary['runs']:
        cases, costs = {}, {}
        for side in ('before','after'):
            path = PROJECT / run[side]['report']
            evidence[str(path.relative_to(ROOT))] = sha(path)
            data = read(path)
            case_map = {c['name']: c for c in data['cases']}
            assert len(case_map) == expected
            assert sum(c['pass'] for c in case_map.values()) == legal
            assert all(c['models_equal'] for c in case_map.values())
            assert all(c['solve_thread_cpu_us'] >= 0 for c in case_map.values())
            cases[side] = case_map
            costs[side] = dict(all_wall=sum(c['solve_us'] for c in case_map.values()),
                               all_cpu=sum(c['solve_thread_cpu_us'] for c in case_map.values()),
                               failed_wall=sum(c['solve_us'] for c in case_map.values() if not c['pass']),
                               failed_cpu=sum(c['solve_thread_cpu_us'] for c in case_map.values() if not c['pass']),
                               cli_wall=run[side]['wall_seconds'])
        assert cases['before'].keys() == cases['after'].keys()
        for name in cases['before']:
            assert all(cases['before'][name][k] == cases['after'][name][k]
                       for k in ('pass','T','peak_memory'))
        rows.append(dict(repetition=run['repetition'],before=costs['before'],after=costs['after'],
                         all_cpu_ratio=costs['after']['all_cpu']/costs['before']['all_cpu']))
    medians = {side:{metric:statistics.median(r[side][metric] for r in rows)
                     for metric in rows[0][side]} for side in ('before','after')}
    cost_path = PROJECT / f'reports/resource-cost-{family}-batch43.json'
    saved = read(cost_path)
    evidence[str(cost_path.relative_to(ROOT))] = sha(cost_path)
    for side in ('before','after'):
        assert medians[side]['all_wall'] == saved[f'median_all_solve_us_{side}']
        assert medians[side]['all_cpu'] == saved[f'median_all_thread_cpu_us_{side}']
        assert medians[side]['failed_wall'] == saved['common_fail_cost'][side]['wall']
        assert medians[side]['failed_cpu'] == saved['common_fail_cost'][side]['cpu']
    results[family] = dict(records_per_round=expected,legal=legal,unresolved=expected-legal,
                           all_pass_T_peak_same=True,rows=rows,medians=medians,
                           median_paired_cpu_ratio=statistics.median(r['all_cpu_ratio'] for r in rows),
                           median_cpu_ratio=medians['after']['all_cpu']/medians['before']['all_cpu'])
result = dict(reviewed_unix=time.time(),passed=True,groups=results,evidence=evidence,
              static_equivalence_review=[
                  'All macro closures are filters of the same graph topological order. A pending node-set bitmask and the previous pending vector therefore encode exactly the same duplicate relation; set iteration is not used to choose candidates.',
                  'Greedy streaming replacement uses strict (final_live,peak) comparison, retaining the first tied candidate, matching the previous stable-sort first candidate.',
                  'Explicit fork/join emission traverses the same stored first/second children followed by original join, retaining root/node coverage and previous node/depth limits.'
              ],
              limitation='Three local paired runs with identical Release flags and preserved failed paths. CPU counters are quantized; forkjoin wall time slightly regressed. No RAM-reduction, official-score or universal speed claim, and no recovery of63 unresolved cases.')
destination = ROOT / 'outputs/stage2-root-resource-pairs-r43.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,groups={k:dict(cpu_ratio=v['median_cpu_ratio'],
                      round_cpu_ratios=[r['all_cpu_ratio'] for r in v['rows']]) for k,v in results.items()})))
