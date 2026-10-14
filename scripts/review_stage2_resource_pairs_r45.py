"""Root recomputation of all R45 Release paired costs including failures."""
import hashlib
import json
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/27-aicore-streams'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    results, evidence = {}, {}
    for family, count, before_count, after_count in [('hard',202,141,143),('heldout',48,42,42)]:
        summary_path = PROJECT/f'reports/paired-{family}-batch45-summary.json'
        summary = read(summary_path)
        saved = read(PROJECT/f'reports/resource-cost-{family}-batch45.json')
        assert len(summary['runs']) == 3 and sha(PROJECT/summary['suite']) == summary['suite_sha256']
        assert sha(PROJECT/summary['current_solution_path']) == summary['current_solution_sha256']
        assert sha(PROJECT/'research/batch45/release-candidate-frozen-aicore_bench.exe') == summary['current_exe_sha256']
        assert sha(PROJECT/'research/batch44/default-aicore_bench.exe') == summary['baseline_exe_sha256']
        rows = []
        for run, saved_round in zip(summary['runs'],saved['rounds']):
            sides = {}
            for side, expected in [('before',before_count),('after',after_count)]:
                path = PROJECT/run[side]['report']
                evidence[path.relative_to(ROOT).as_posix()] = sha(path)
                assert sha(path) == saved_round['raw_sha'][side]
                sides[side] = {c['name']:c for c in read(path)['cases']}
                assert len(sides[side]) == count and sum(c['pass'] for c in sides[side].values()) == expected
                assert all(c['models_equal'] for c in sides[side].values())
            assert sides['before'].keys() == sides['after'].keys()
            groups = {name:[] for name in ('all','common_success','common_failure','recovered')}
            for name, before in sides['before'].items():
                after = sides['after'][name]
                assert not before['pass'] or after['pass']
                if before['pass']:
                    assert (before['T'],before['peak_memory']) == (after['T'],after['peak_memory'])
                group = 'common_success' if before['pass'] else ('recovered' if after['pass'] else 'common_failure')
                groups[group].append(name);groups['all'].append(name)
            costs = {}
            for group, names in groups.items():
                costs[group] = dict(count=len(names), **{side:dict(wall_us=sum(sides[side][name]['solve_us'] for name in names),thread_cpu_us=sum(sides[side][name]['solve_thread_cpu_us'] for name in names)) for side in ('before','after')})
            assert costs == saved_round['groups']
            rows.append(dict(groups=costs,cpu_ratio=costs['all']['after']['thread_cpu_us']/costs['all']['before']['thread_cpu_us'],wall_ratio=costs['all']['after']['wall_us']/costs['all']['before']['wall_us']))
        medians = {group:{side:{metric:statistics.median(r['groups'][group][side][metric] for r in rows) for metric in ('wall_us','thread_cpu_us')} for side in ('before','after')} for group in rows[0]['groups']}
        assert medians == saved['independent_side_medians']
        paired = statistics.median(r['cpu_ratio'] for r in rows)
        side_ratio = medians['all']['after']['thread_cpu_us']/medians['all']['before']['thread_cpu_us']
        assert paired == saved['median_within_pair_all_cpu_ratio'] and side_ratio == saved['ratio_of_independent_side_all_cpu_medians']
        results[family] = dict(records=count,before_legal=before_count,after_legal=after_count,round_cpu_ratios=[r['cpu_ratio'] for r in rows],median_paired_cpu_ratio=paired,ratio_of_independent_cpu_medians=side_ratio,medians=medians)
    result = dict(reviewed_unix=time.time(),passed=True,groups=results,evidence=evidence,
                  interpretation='All202 and fresh48 three alternating pairs, common successes/failures and recovered cases included. Actual frozen baseline7861 default Release archive and candidate3e827 Release archive; distinct from historicalR44 measured8d43 executable. Source flags Release O3, fullCLI working-set includes harness/witnesses. Per-trial hostload unmeasured and user background active; no idle-machine or general speed/feasibility claim.')
    (ROOT/'outputs/stage2-root-resource-pairs-r45.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,groups={k:dict(paired_cpu_ratio=v['median_paired_cpu_ratio'],side_median_ratio=v['ratio_of_independent_cpu_medians']) for k,v in results.items()})))


if __name__ == '__main__':
    main()
