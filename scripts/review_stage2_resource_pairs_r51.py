"""Root recomputation of all paired costs, actual plans and raw host counters."""
import json
import statistics
import time
from pathlib import Path
from review_stage2_resource_pairs_r48 import sha, read
from review_stage2_functional_plans_r44 import simulate

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/27-aicore-streams'


def cpu_delta(a, b):
    idle, kernel, user = (b[k]-a[k] for k in ('idle', 'kernel', 'user'))
    assert min(idle, kernel, user) >= 0 and kernel+user > 0 and idle <= kernel+user
    return dict(idle_ticks=idle, kernel_ticks=kernel, user_ticks=user,
                total_ticks=kernel+user, busy_ticks=kernel+user-idle,
                busy_fraction=(kernel+user-idle)/(kernel+user))


def main():
    completion = P/'research/batch51/paired-completion.json'; manifest = read(completion)
    assert sha(completion) == '5ea14780ba5c41c8b1b9c7cd8731395908d76698f3ce80f1bdeecedd12486271'
    assert manifest['actual_session'] == 32966 and manifest['actual_exit_code'] == 0
    assert manifest['trials'] == 12 and manifest['case_execution_records'] == 1500
    for name, expected in manifest['files'].items():
        assert sha(P/name) == expected, name
    assert sha(P/manifest['candidate_exe_path']) == manifest['candidate_exe_sha']
    assert sha(P/manifest['baseline_exe_path']) == manifest['baseline_exe_sha']
    driver = read(P/'research/batch51/paired-driver-status.json')
    assert len(driver['statuses']) == 2 and all(r['actual_exit_code'] == 0 for r in driver['statuses'])
    results, evidence, hosts = {}, {}, []; plans = records = 0
    for family, count, before_count, after_count in [('hard', 202, 144, 145), ('heldout', 48, 42, 42)]:
        path = P/f'reports/paired-{family}-batch51-summary.json'; summary = read(path)
        saved = read(P/f'reports/resource-cost-{family}-batch51.json')
        assert len(summary['runs']) == 3 and sha(P/summary['suite']) == summary['suite_sha256']
        assert summary['current_exe_sha256'] == manifest['candidate_exe_sha']
        assert summary['baseline_exe_sha256'] == manifest['baseline_exe_sha']
        cases = {r['name']: r for r in read(P/summary['suite'])['cases']}; rows = []
        for run, saved_round in zip(summary['runs'], saved['rounds']):
            sides = {}; endpoints = {}
            for side, expected in [('before', before_count), ('after', after_count)]:
                raw_path = P/run[side]['report']; raw = read(raw_path)
                assert sha(raw_path) == saved_round['raw_sha'][side]
                evidence[raw_path.relative_to(ROOT).as_posix()] = sha(raw_path)
                sides[side] = {c['name']: c for c in raw['cases']}
                assert set(sides[side]) == set(cases) and len(sides[side]) == count
                assert sum(c['pass'] for c in sides[side].values()) == expected
                assert all(c['models_equal'] for c in sides[side].values())
                assert run[side]['exit_code'] == 1
                assert raw_path.with_suffix('.stderr.txt').read_text() == ''
                for name, row in sides[side].items():
                    records += 1
                    assert row['solve_us'] >= 0 and row['solve_thread_cpu_us'] >= 0
                    if row['pass']:
                        assert simulate(cases[name], row['plan']) == (row['T'], row['peak_memory'])
                        plans += 1
                hp = P/run[side]['host_report']; host = read(hp)
                assert sha(hp) == run[side]['host_report_sha256'] and host == run[side]['host_load']
                assert host['status'] == 'measured' and not host['errors'] and host['logical_processors'] == 32
                samples = host['samples']; assert len(samples) >= 2
                endpoint = cpu_delta(samples[0]['cpu_ticks'], samples[-1]['cpu_ticks'])
                assert endpoint == host['trial_cpu_delta']
                memories = [s['memory']['available_physical_bytes'] for s in samples]
                assert (memories[0], memories[-1], min(memories)) == tuple(host[k] for k in (
                    'available_physical_bytes_start', 'available_physical_bytes_end', 'available_physical_bytes_min'))
                assert len(host['cpu_intervals']) == len(samples)-1
                for interval, a, b in zip(host['cpu_intervals'], samples, samples[1:]):
                    assert a['elapsed_seconds'] < b['elapsed_seconds']
                    assert interval == dict(begin_seconds=a['elapsed_seconds'], end_seconds=b['elapsed_seconds'], delta=cpu_delta(a['cpu_ticks'], b['cpu_ticks']))
                endpoints[side] = samples[0]['cpu_ticks']['kernel']+samples[0]['cpu_ticks']['user']
                hosts.append(dict(family=family, round=run['repetition'], side=side,
                                  host_busy_fraction=endpoint['busy_fraction'], sampled_free_ram_min_bytes=min(memories)))
            assert (endpoints['before'] < endpoints['after']) == (run['repetition'] % 2 == 1)
            groups = {name: [] for name in ('all', 'common_success', 'common_failure', 'recovered')}
            for name, before in sides['before'].items():
                after = sides['after'][name]
                assert not before['pass'] or after['pass']
                if before['pass']:
                    assert (before['T'], before['peak_memory']) == (after['T'], after['peak_memory'])
                group = 'common_success' if before['pass'] else 'recovered' if after['pass'] else 'common_failure'
                groups[group].append(name); groups['all'].append(name)
            costs = {g: dict(count=len(names), **{s: dict(wall_us=sum(sides[s][n]['solve_us'] for n in names),
                        thread_cpu_us=sum(sides[s][n]['solve_thread_cpu_us'] for n in names)) for s in ('before', 'after')})
                     for g, names in groups.items()}
            assert costs == saved_round['groups']
            rows.append(dict(groups=costs, cpu_ratio=costs['all']['after']['thread_cpu_us']/costs['all']['before']['thread_cpu_us'],
                             wall_ratio=costs['all']['after']['wall_us']/costs['all']['before']['wall_us']))
        medians = {g: {s: {metric: statistics.median(r['groups'][g][s][metric] for r in rows)
                   for metric in ('wall_us', 'thread_cpu_us')} for s in ('before', 'after')} for g in rows[0]['groups']}
        assert medians == saved['independent_side_medians']
        paired = statistics.median(r['cpu_ratio'] for r in rows)
        side_ratio = medians['all']['after']['thread_cpu_us']/medians['all']['before']['thread_cpu_us']
        assert paired == saved['median_within_pair_all_cpu_ratio']
        assert side_ratio == saved['ratio_of_independent_side_all_cpu_medians']
        results[family] = dict(records=count, before_legal=before_count, after_legal=after_count,
                              round_cpu_ratios=[r['cpu_ratio'] for r in rows], median_paired_cpu_ratio=paired,
                              median_paired_solve_wall_ratio=statistics.median(r['wall_ratio'] for r in rows),
                              ratio_of_independent_cpu_medians=side_ratio, medians=medians)
    assert (records, plans, len(hosts)) == (1500, 1119, 12)
    result = dict(passed=True, reviewed_unix=time.time(), groups=results, actual_case_records=records,
                  independent_actual_full_plan_replays=plans, host_trials=hosts,
                  evidence={**evidence, completion.relative_to(ROOT).as_posix(): sha(completion)},
                  interpretation='All202+48 x two actual Release EXEs x three alternating rounds; all failure costs included. Root1119 full actual plans replayed, raw integer host ticks/intervals/RAM recomputed. Hard medianCPU -6.24percent but third+6.07percent; fresh medianCPU -2.90percent and median solvewall+0.46percent. Active background recorded, no idle/general stable acceleration or universal feasibility claim. Default remains R48 pending actual integration.')
    (ROOT/'outputs/stage2-root-resource-pairs-r51.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence', 'host_trials')}))


if __name__ == '__main__':
    main()
