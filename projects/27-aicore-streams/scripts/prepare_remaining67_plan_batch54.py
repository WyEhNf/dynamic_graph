"""Static plan only: all R51 remaining63 + four restored controls, no solve."""
from pathlib import Path
import collections,hashlib,json,statistics
P=Path('research/batch54');P.mkdir(exist_ok=True)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
canonical=lambda c:hashlib.sha256(json.dumps({k:c[k] for k in ('hardware','nodes','deadline_us')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
remaining=json.loads(Path('research/batch52/remaining63-input-only.json').read_text())['cases']
selected12=json.loads(Path('research/batch52/observer-selected12-input-only.json').read_text())['cases']
previous12=json.loads(Path('reports/observer-baseline-batch52.json').read_text())['cases']
restore_names=[c['name'] for c in previous12 if c['whole']['valid']]
controls=[c for c in selected12 if c['name'] in restore_names];assert len(controls)==4 and len(remaining)==63
fields=('name','hardware','nodes','deadline_us','expected_feasible')
cases=[{k:c[k] for k in fields} for c in remaining+controls];assert len({c['name'] for c in cases})==67
source_sets=[('hard','data/hard-corpus-resumed.json','reports/hard-functional-batch51.json'),('heldout','data/projection-retention-heldout-batch45.json','reports/heldout-functional-batch51.json')]
origins={}
for partition,inputs,results in source_sets:
    ins=json.loads(Path(inputs).read_text())['cases'];outs=json.loads(Path(results).read_text())['cases'];assert len(ins)==len(outs)
    for index,(i,r) in enumerate(zip(ins,outs)):
        assert i['name']==r['name'];origins[i['name']]=(partition,inputs,results,index,i,r)
helper_sources=[('data/unresolved-r44-input-only-batch45.json','reports/projection-unresolved-diagnostic-batch51.json'),('data/projection-heldout-unresolved-input-only-batch45.json','reports/projection-heldout-unresolved-diagnostic-batch51.json')]
helpers={}
for inputs,results in helper_sources:
    ins=json.loads(Path(inputs).read_text())['cases'];outs=json.loads(Path(results).read_text())['cases'];assert len(ins)==len(outs)
    for index,(i,r) in enumerate(zip(ins,outs)):assert i['name']==r['name'];helpers[i['name']]=(inputs,results,index,i,r)
assert len(helpers)==67 and set(helpers)=={c['name'] for c in cases}
smoke={c['name']:c for c in json.loads(Path('reports/default-smoke-batch51.json').read_text())['cases']}
baseline=[];lineage=[]
for index,c in enumerate(cases):
    assert c['expected_feasible'] is True
    partition,ip,rp,slot,original,source_result=origins[c['name']]
    hi,hr,hs,hinput,hresult=helpers[c['name']]
    assert canonical(c)==canonical(original)==canonical(hinput)
    control=c['name'] in restore_names
    assert source_result['valid']==control and hresult['valid']==control
    # Honest provenance: source-equivalent accepted candidate reports for all67;
    # current actual default saved smoke supersedes whole quality when available.
    whole=smoke.get(c['name'],source_result)
    assert whole['valid']==control
    baseline.append(dict(name=c['name'],input_sha256=canonical(c),partition=partition,control=control,whole=dict(valid=whole['valid'],T=whole['T'],peak=whole['peak_memory'],error=whole['error'],plan=whole['plan']),whole_source='reports/default-smoke-batch51.json' if c['name'] in smoke else rp,whole_source_kind='actual_current_default_smoke' if c['name'] in smoke else 'accepted_R51_source_equivalent_candidate_full_functional',helper=dict(valid=hresult['valid'],T=hresult['T'],peak=hresult['peak_memory'],work=hresult['work'],evaluations=hresult['evaluations'],exhausted=hresult['exhausted'],best_peak_lo=hresult['best_peak_lo'],best_peak_hi=hresult['best_peak_hi'],plan=hresult['plan']),helper_source=hr))
    lineage.append(dict(index=index,name=c['name'],role='restored_control' if control else 'remaining_known_witness_feasible_failed',partition=partition,input_sha256=canonical(c),original_input_path=ip,original_input_record_index=slot,original_result_path=rp,original_result_index=slot,helper_input_path=hi,helper_result_path=hr,helper_record_index=hs,actual_default_smoke_saved=c['name'] in smoke,solver_input_keys=list(fields),witness_generation_or_saved_plan_fed_to_solver=False))
inputfile=P/'remaining67-input-only.json';inputfile.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases),indent=2)+'\n',encoding='utf-8')
(P/'baseline-saved67.json').write_text(json.dumps(dict(cases=baseline,provenance='R51 identical frozen source8b7c;actual current default saved smoke7 covers fourcontrols+threefailures;other60 whole records from accepted source-equivalent R51 full functional,not newly run currentdefault. All67 helper records are saved prior R51 source-only diagnostic. No CPU speed comparison.'),indent=2)+'\n',encoding='utf-8')
(P/'input-lineage67.json').write_text(json.dumps(dict(cases=lineage,solver_reads_only='hardware,nodes,deadline_us;name/expectedfeasible only wrapper metadata',selection='all63 frozen failures,then four original restored controls;no further filtering'),indent=2)+'\n',encoding='utf-8')
work=[b['helper']['work'] for b in baseline]
stats=dict(records=67,remaining=dict(hard=57,heldout=6),controls=4,baseline_whole_legal=4,baseline_whole_failed=63,baseline_helper_legal=sum(b['helper']['valid'] for b in baseline),baseline_helper_exhausted=sum(b['helper']['exhausted'] for b in baseline),baseline_helper_work_sum=sum(work),baseline_helper_work_max=max(work),baseline_helper_work_median=statistics.median(work),baseline_helper_evaluations_sum=sum(b['helper']['evaluations'] for b in baseline),actual_current_default_saved_records=sum(x['actual_default_smoke_saved'] for x in lineage),source_equivalent_saved_other_records=sum(not x['actual_default_smoke_saved'] for x in lineage),charged_units_not_cpu_cycles=True)
paths=[str(inputfile).replace('\\','/'),'research/batch54/baseline-saved67.json','research/batch54/input-lineage67.json','research/batch52/remaining63-input-only.json','research/batch52/observer-selected12-input-only.json','reports/observer-baseline-batch52.json','reports/default-smoke-batch51.json','research/batch53/solution.cpp','research/batch53/selected12-driver.cpp','research/batch53/selected12-gcc.exe','research/batch53/charged-work-table.json','research/batch53/small-acceptance-checkpoint.json','research/batch53/corrected/completion.json','research/batch51/solution.cpp','research/batch51/functional-checkpoint.json','research/batch51/acceptance-checkpoint.json','research/batch51/provenance.json','solution/solution.cpp','build/aicore_bench.exe','reports/project27-research.tex','include/problem.h','include/local_json.h','include/simulator.h','src/benchmark.cpp','src/simulator.cpp','scripts/prepare_remaining67_plan_batch54.py','scripts/run_remaining67_batch54.py','scripts/verify_remaining67_batch54.py']
paths += [f for _,i,r in source_sets for f in (i,r)] + [f for i,r in helper_sources for f in (i,r)]
assert sha('research/batch53/solution.cpp')=='fcbb968cff47dd0b95edb576f1fcf0bd04e900eb0f37ecb28383607ca02f3a21'
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
plan=dict(status='STATIC_PREPARED_NOT_EXECUTED_WAIT_ROOT_AUTHORIZATION',scope='Exactly67 source-only functionality;reuse fcbb same compiledGCCO2 selected12 driver;no compile/budget change/full250/1099/performance/default',candidate_source_sha256=sha('research/batch53/solution.cpp'),candidate_exe_sha256=sha('research/batch53/selected12-gcc.exe'),command=['research/batch53/selected12-gcc.exe','research/batch54/remaining67-input-only.json','reports/final-live-remaining67-batch54.json'],baseline_statistics=stats,budgets=dict(cut=2000000,total=16000000,closure_nodes=128,held_top=24,seeds_threshold_sort_unchanged=True),output_contract=dict(raw_json='Everycase helperwork/evaluations/exhausted/orderids/fullverifiedhelperplan,whole returned/error/valid/T/peak/fullplan/metrics;failures retained as failedboundedheuristic,not infeasibility certificates',raw_stdout='reports/final-live-remaining67-batch54.stdout.txt',raw_stderr='reports/final-live-remaining67-batch54.stderr.txt',wrapper_exit='Driver0 means all returnedplans passed twoC++models;not67feasible. Any unexpecteddriver nonzero preserved and gatefailed.',full_plans='All returned plans save every original op_id, wait_before,record_after andstream structure for independentrootheap;baseline plans separate never solver input.'),comparison_contract=['perrecordwhole success/failure/T/peak/plan equality;restored andlost separately','helperwork/evaluations/exhaustion sums,median,max and perrecorddifferences including allfailed','newcompleteplans requireoriginalnodes/hardware/deadline exactmatch andindependentverification','sharedfunctional wall only,notCPU/Wall speed comparison againsthistoricalrecords'],execution_authorized=False,solver_executed=False,compile_executed=False,default_changed=False,files=[dict(path=f,sha256=sha(f)) for f in sorted(set(paths))])
(P/'functional-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(plan_sha256=sha(P/'functional-plan.json'),candidate_exe_sha256=plan['candidate_exe_sha256'],frozen_files=len(plan['files']),baseline_statistics=stats),indent=2))
