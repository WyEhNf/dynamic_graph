"""Verify all remaining original graphs and frozen same-source baselines."""
import json
import time
from collections import Counter
from review_stage2_observer_r52 import ROOT,P,sha,simulate

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    d=P/'research/batch54';plan=read(d/'functional-plan.json')
    for row in plan['files']:assert sha(P/row['path'])==row['sha256']
    assert plan['candidate_source_sha256']==sha(P/'research/batch53/solution.cpp')=='fcbb968cff47dd0b95edb576f1fcf0bd04e900eb0f37ecb28383607ca02f3a21'
    assert plan['candidate_exe_sha256']==sha(P/'research/batch53/selected12-gcc.exe')
    assert plan['budgets']==dict(cut=2000000,total=16000000,closure_nodes=128,held_top=24,seeds_threshold_sort_unchanged=True)
    cases=read(d/'remaining67-input-only.json')['cases'];lineage=read(d/'input-lineage67.json')['cases'];saved=read(d/'baseline-saved67.json')['cases']
    assert len(cases)==len(lineage)==len(saved)==67 and len({c['name'] for c in cases})==67
    partitions=Counter();controls=0
    for c,l,b in zip(cases,lineage,saved):
        assert c['name']==l['name']==b['name'] and set(c)=={'name','hardware','nodes','deadline_us','expected_feasible'}
        source=read(P/l['original_input_path'])['cases'][l['original_input_record_index']]
        for key in ('name','hardware','nodes','deadline_us'):assert c[key]==source[key]
        original=read(P/l['original_result_path'])['cases'][l['original_result_index']]
        assert original['name']==c['name'] and not l['witness_generation_or_saved_plan_fed_to_solver']
        assert b['whole']['valid']==original['valid'] and b['whole']['T']==original['T'] and b['whole']['peak']==original['peak_memory']
        if b['control']:
            controls+=1;assert b['whole']['valid']
            T,peak=simulate(c,b['whole']['plan']);assert T==b['whole']['T'] and peak==b['whole']['peak']
        else:partitions[b['partition']]+=1;assert not b['whole']['valid'] and b['whole']['plan'] is None
        assert b['helper']['work']<=16000000
    assert dict(partitions)==dict(hard=57,heldout=6) and controls==4
    s=plan['baseline_statistics'];assert s['baseline_whole_legal']==4 and s['baseline_whole_failed']==63
    assert s['actual_current_default_saved_records']==7 and s['source_equivalent_saved_other_records']==60
    assert not any(plan[k] for k in ('execution_authorized','solver_executed','compile_executed','default_changed'))
    driver=(P/'research/batch53/selected12-driver.cpp').read_text()
    assert 'aicore_detail::Graph g(h,nodes)' in driver and 'ScheduleCvGraph(h,nodes,c.at("deadline_us").integer())' in driver
    assert 'expected_feasible' not in driver and 'generation' not in driver and 'fixed_plan' not in driver
    result=dict(passed=True,reviewed_unix=time.time(),functional_plan_sha256=sha(d/'functional-plan.json'),frozen_files=len(plan['files']),
        original_inputs=67,original_remaining_hard=57,original_remaining_fresh=6,known_recovery_controls=4,
        independently_replayed_baseline_plans=4,actual_default_baseline_records=7,same_source_accepted_baseline_records=60,
        actual_candidate_executions=0,scope='All63 original failed known-feasible graphs plus4 accepted recoveries, original hardware/edges/deadlines unchanged.67complete frozen baseline/source lineage reviewed; selected12 driver reuses exactcandidate GCC EXE and reads only hardware/nodes/deadline. Same2M/16M; functional execution still required, no full250/regression/performance/default promotion.')
    (ROOT/'outputs/stage2-root-remaining-plan-r54.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
