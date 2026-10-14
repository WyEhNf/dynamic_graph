"""Run after actual three-round terminal; no timing or baseline filtering."""
import hashlib,json,statistics
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
results={}
for family in ('hard','heldout'):
    summary=json.loads(Path(f'reports/paired-{family}-batch45-summary.json').read_text());rounds=[]
    for n in range(1,4):
        paths={side:Path(f'reports/paired-{family}-batch45-{n}-{side}.json') for side in ('before','after')}
        rows={side:json.loads(p.read_text())['cases'] for side,p in paths.items()};a,b=rows['before'],rows['after']
        assert len(a)==len(b) and all(x['name']==y['name'] for x,y in zip(a,b))
        groups=dict(all=list(range(len(a))),common_success=[i for i in range(len(a)) if a[i]['pass'] and b[i]['pass']],common_failure=[i for i in range(len(a)) if not a[i]['pass'] and not b[i]['pass']],recovered=[i for i in range(len(a)) if not a[i]['pass'] and b[i]['pass']])
        assert not any(x['pass'] and not y['pass'] for x,y in zip(a,b))
        assert all((a[i]['T'],a[i]['peak_memory'])==(b[i]['T'],b[i]['peak_memory']) for i in groups['common_success'])
        assert all(x['models_equal'] for x in b)
        costs={group:dict(count=len(indices),**{side:dict(wall_us=sum(rows[side][i]['solve_us'] for i in indices),thread_cpu_us=sum(rows[side][i]['solve_thread_cpu_us'] for i in indices)) for side in ('before','after')}) for group,indices in groups.items()}
        meta=summary['runs'][n-1]
        row=dict(round=n,groups=costs,raw_sha={side:sha(p) for side,p in paths.items()},cli={side:dict(wall_seconds=meta[side]['wall_seconds'],working_set_bytes=meta[side]['peak_working_set_bytes']) for side in ('before','after')},recovered=[a[i]['name'] for i in groups['recovered']])
        row['all_cpu_ratio']=costs['all']['after']['thread_cpu_us']/costs['all']['before']['thread_cpu_us'];row['all_wall_ratio']=costs['all']['after']['wall_us']/costs['all']['before']['wall_us'];rounds.append(row)
    medians={g:{side:{metric:statistics.median(r['groups'][g][side][metric] for r in rounds) for metric in ('wall_us','thread_cpu_us')} for side in ('before','after')} for g in rounds[0]['groups']}
    report=dict(rounds=rounds,independent_side_medians=medians,median_within_pair_all_cpu_ratio=statistics.median(r['all_cpu_ratio'] for r in rounds),ratio_of_independent_side_all_cpu_medians=medians['all']['after']['thread_cpu_us']/medians['all']['before']['thread_cpu_us'],median_within_pair_all_wall_ratio=statistics.median(r['all_wall_ratio'] for r in rounds),cli_side_medians={side:dict(wall_seconds=statistics.median(r['cli'][side]['wall_seconds'] for r in rounds),maximum_working_set_bytes=max(r['cli'][side]['working_set_bytes'] for r in rounds)) for side in ('before','after')},source_sha=summary['current_solution_sha256'],exe_sha=summary['current_exe_sha256'],baseline_source_sha=summary['baseline_solution_sha256'],baseline_exe_sha=summary['baseline_exe_sha256'],counts={k:v['count'] for k,v in rounds[0]['groups'].items()},timing='Same GCC Release O3; complete failures included; original record order retained; Win32 thread CPU quantized; process WS includes JSON/plans/validators; background user applications remain; side-median and median-paired ratios distinguished')
    report['host_load']={'trial_host_busy':'unmeasured','trial_host_available_ram':'unmeasured','pre_window_observation':'Parent observed about1.32GiB available RAM and active user applications; not a complete-window sample','harness_modified_during_run':False,'extra_runs_for_background':False}
    report['paired_plan_path']='research/batch45/paired-plan.json';report['paired_plan_sha']=sha(report['paired_plan_path'])
    report['baseline_executed_path']='research/batch44/default-aicore_bench.exe';report['candidate_executed_path']='research/batch45/release-candidate-frozen-aicore_bench.exe'
    Path(f'reports/resource-cost-{family}-batch45.json').write_text(json.dumps(report,indent=2),encoding='utf-8');results[family]=report
    print(family,report['counts'],'CPU pairs',[round(r['all_cpu_ratio'],6) for r in rounds],'median',round(report['median_within_pair_all_cpu_ratio'],6),'side',round(report['ratio_of_independent_side_all_cpu_medians'],6),flush=True)
Path('reports/resource-cost-summary-batch45.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
