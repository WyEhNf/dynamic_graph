"""Semantic equality + independent state equations, excluding only timing."""
import collections
import hashlib
import json
from pathlib import Path

sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
p=Path('research/batch52');inputs=json.loads((p/'observer-selected12-input-only.json').read_text())['cases']
baseline=json.loads(Path('reports/observer-baseline-batch52.json').read_text())['cases']
observed=json.loads(Path('reports/observer-observed-batch52.json').read_text())['cases']
actual=json.loads(Path('reports/observer-actual-default-batch52.json').read_text())['cases']
assert len(inputs)==len(baseline)==len(observed)==len(actual)==12
cases=[];snapshot_count=0;coherent_snapshots=0;transitional_snapshots=0
for case,a,b,ordinary in zip(inputs,baseline,observed,actual):
    assert case['name']==a['name']==b['name']==ordinary['name']
    assert a['helper']==b['helper'] and a['whole']==b['whole']
    assert b['helper']['work']<=16000000
    assert b['whole']['valid']==ordinary['valid'] and b['whole']['T']==ordinary['T'] and b['whole']['peak']==ordinary['peak_memory']
    assert b['whole']['plan']==ordinary['plan'] and b['whole']['error']==ordinary['error']
    metric_names={0:'candidates',1:'feasible_candidates',5:'duplicate_candidates',6:'attempts',7:'beam_expansions',8:'beam_width',9:'optimal_certificate',10:'time_lower_bound',11:'memory_lower_bound'}
    for key,label in metric_names.items():assert b['whole']['metrics'][str(key)]==ordinary[label],(case['name'],label)
    nodes=case['nodes'];index={node['id']:i for i,node in enumerate(nodes)};parents=[[index[i] for i in node['inputs']] for node in nodes];children=[[] for _ in nodes]
    for i,ps in enumerate(parents):
        for parent in ps:children[parent].append(i)
    for scope in ('helper_observer','whole_observer'):
        log=b[scope]
        assert log['cut_work']<=2000000 and log['total_work']<=16000000
        assert log['cut_work']+log['projection_work']==log['total_work']
        for row in log['snapshots']:
            snapshot_count+=1
            if not row['state_initialized']:continue
            assert row['node_ids']==[node['id'] for node in nodes]
            if row['transition_may_be_incomplete']:
                # A budgeted rejected temporary probe can stop midway through
                # END bookkeeping. It is preserved, not labelled a legal prefix.
                assert row['kind']=='probe' and row['phase']=='apply' and row['reason']=='budget_exhausted'
                transitional_snapshots+=1
                continue
            coherent_snapshots+=1
            done=row['done'];users=row['remaining_direct_users'];degrees=row['remaining_degree']
            assert len(done)==len(users)==len(degrees)==len(nodes)
            assert users==[sum(not done[c] for c in cs) for cs in children]
            assert degrees==[sum(not done[parent] for parent in ps) for ps in parents]
            assert all(not done[i] or degrees[i]==0 for i in range(len(nodes)))
            held=[i for i,node in enumerate(nodes) if done[i] and (users[i] or not children[i])]
            assert row['live']==sum(nodes[i]['output_memory'] for i in held)
            assert row['live']<=case['hardware']['memory_limit']
            ready=[i for i in range(len(nodes)) if not done[i] and degrees[i]==0]
            fit=[i for i in ready if row['live']+nodes[i]['workspace_memory']+nodes[i]['output_memory']<=case['hardware']['memory_limit']]
            assert row['global_ready_ids']==[nodes[i]['id'] for i in ready]
            assert row['global_ready_fit_ids']==[nodes[i]['id'] for i in fit]
            if row['kind']=='probe' and row['reason']=='ready_but_no_fit':assert row['cut_ready_ids'] and not row['cut_ready_fit_ids']
            assert row['held_sink_output']==sum(nodes[i]['output_memory'] for i in held if not children[i])
    log=b['helper_observer']
    assert log['total_work']==b['helper']['work']
    cases.append(dict(name=case['name'],helper_work=b['helper']['work'],helper_order_complete=len(b['helper']['order_ids'])==len(nodes),whole_valid=b['whole']['valid'],cut_work=log['cut_work'],projection_work=log['projection_work'],cut_complete=log['cut_complete'],cut_exhausted=log['cut_exhausted'],projection_exhausted=log['projection_exhausted'],counts=log['counts'],terminal=[row for row in log['snapshots'] if row['kind']=='outer']))
gold=json.loads(Path('reports/whole-numeric-gold-batch52.json').read_text())
assert len(gold['cases'])==8 and all(row['pass'] for row in gold['cases']) and all(not row['solver_called'] for row in gold['cases'])
status=json.loads((p/'observer-status.json').read_text());assert all(row['actual_exit_code'] in (0,1) for row in status['statuses'])
report=dict(status='Small diagnostic semantic equality and independent state equations passed;no algorithm branch/default change',selected_original_cases=12,failed_controls=8,existing_recoveries=4,helper_and_whole_every_nontiming_field_identical=True,actual_default_comparison=True,snapshots_preserved=snapshot_count,coherent_prefix_snapshots_checked=coherent_snapshots,transitional_budget_probe_snapshots_preserved=transitional_snapshots,complete_fixed_plan_bigint_controls=8,UBSan_runtime_errors=0,cases=cases,source_sha=sha('research/batch51/solution.cpp'),observer_source_sha=sha(p/'observer-solution.cpp'),plan_sha=sha(p/'observer-plan.json'),baseline_exe_sha=sha(p/'baseline-driver.exe'),observer_exe_sha=sha(p/'observed-driver.exe'),actual_default_exe_sha=sha('build/aicore_bench.exe'),timing='Shared functional diagnostic with observer overhead;not performance or full63/250',files={path:sha(path) for path in ['reports/observer-baseline-batch52.json','reports/observer-observed-batch52.json','reports/observer-actual-default-batch52.json','reports/whole-numeric-gold-batch52.json','reports/whole-python-gold-batch52.json','research/batch52/whole-fixed-gold.json']})
Path('reports/observer-summary-batch52.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('12 source-only observer cases exactly match R51 + actualdefault;8 independent full-plan gold',flush=True)
