"""Keep full costs and separate recovered from common-failure records."""
import hashlib,json,statistics
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
results={}
for family in ['hard','heldout']:
    summary=json.loads(Path(f'reports/paired-{family}-batch44-summary.json').read_text());rounds=[]
    for n in range(1,4):
        paths={side:Path(f'reports/paired-{family}-batch44-{n}-{side}.json') for side in ['before','after']}
        rows={side:{r['name']:r for r in json.loads(p.read_text())['cases']} for side,p in paths.items()};a,b=rows['before'],rows['after'];assert a.keys()==b.keys()
        groups=dict(all=list(a),common_success=[k for k in a if a[k]['pass'] and b[k]['pass']],common_failure=[k for k in a if not a[k]['pass'] and not b[k]['pass']],recovered=[k for k in a if not a[k]['pass'] and b[k]['pass']])
        assert not [k for k in a if a[k]['pass'] and not b[k]['pass']]
        assert all((a[k]['T'],a[k]['peak_memory'])==(b[k]['T'],b[k]['peak_memory']) for k in groups['common_success'])
        assert all(r['models_equal'] for r in b.values())
        costs={}
        for group,names in groups.items():
            costs[group]=dict(count=len(names),**{side:dict(wall_us=sum(rows[side][k]['solve_us'] for k in names),thread_cpu_us=sum(rows[side][k]['solve_thread_cpu_us'] for k in names)) for side in ['before','after']})
        meta=summary['runs'][n-1]
        roundrow=dict(round=n,groups=costs,raw_sha={side:sha(p) for side,p in paths.items()},cli={side:dict(wall_seconds=meta[side]['wall_seconds'],working_set_bytes=meta[side]['peak_working_set_bytes']) for side in ['before','after']},recovered=groups['recovered'])
        roundrow['all_cpu_ratio']=costs['all']['after']['thread_cpu_us']/costs['all']['before']['thread_cpu_us'];roundrow['all_wall_ratio']=costs['all']['after']['wall_us']/costs['all']['before']['wall_us']
        rounds.append(roundrow)
    medians={g:{side:{metric:statistics.median(r['groups'][g][side][metric] for r in rounds) for metric in ['wall_us','thread_cpu_us']} for side in ['before','after']} for g in rounds[0]['groups']}
    report=dict(rounds=rounds,independent_side_medians=medians,median_within_pair_all_cpu_ratio=statistics.median(r['all_cpu_ratio'] for r in rounds),ratio_of_independent_side_all_cpu_medians=medians['all']['after']['thread_cpu_us']/medians['all']['before']['thread_cpu_us'],median_within_pair_all_wall_ratio=statistics.median(r['all_wall_ratio'] for r in rounds),cli_side_medians={side:dict(wall_seconds=statistics.median(r['cli'][side]['wall_seconds'] for r in rounds),maximum_working_set_bytes=max(r['cli'][side]['working_set_bytes'] for r in rounds)) for side in ['before','after']},source_sha=summary['current_solution_sha256'],exe_sha=summary['current_exe_sha256'],baseline_source_sha=summary['baseline_solution_sha256'],baseline_exe_sha=summary['baseline_exe_sha256'],counts= {k:v['count'] for k,v in rounds[0]['groups'].items()},timing='same GCC Release O3; all failures included; Win32 CPU quantized; independent-side median ratio differs from median per-pair ratio; process WS includes whole JSON/witness/validators')
    Path(f'reports/resource-cost-{family}-batch44.json').write_text(json.dumps(report,indent=2),encoding='utf-8');results[family]=report
    print(family,report['counts'],'CPU pairs',[round(r['all_cpu_ratio'],6) for r in rounds],'median',round(report['median_within_pair_all_cpu_ratio'],6),'side',round(report['ratio_of_independent_side_all_cpu_medians'],6))
Path('reports/resource-cost-summary-batch44.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
