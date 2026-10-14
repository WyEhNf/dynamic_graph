"""Once-only wrapper control tests plus original saved ca93 real search."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter
import unittest

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.tree_pair_anytime_refine import refine_fixed_tree_pairs_anytime
from scripts.research_tree_pair_anytime_84 import export_diagnostics
from scripts.research_spine_age_probe import check


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def main():
    folder=ROOT/'experiments/r176-anytime-wrapper-cap-ca93'; folder.mkdir(exist_ok=False)
    source=ROOT/'experiments/r172-tree-pair-anytime-84'; short='ca93bf4ab93ad824'
    source_parameters={'fixed_weight':2,'total_time_budget_ms':500,'cumulative_states':20000,'outlets_each_pair':16,'parent_max_nodes':96}
    core=ROOT/'isa_scheduler/tree_pair_anytime.py'; wrapper=ROOT/'isa_scheduler/tree_pair_anytime_refine.py'
    original_wrapper=source/'src/isa_scheduler/tree_pair_anytime_refine.py'
    assert sha(core)=='dac3b71701e4085f7fb7e1ca2f829937cbb028cc8b68a773c1021ff16c1477c7'
    original=original_wrapper.read_text(); updated=wrapper.read_text()
    start='        block=parse_block'; end='        for parent,child_copies'
    before=original[original.index(start):original.index(end)]; after=updated[updated.index(start):updated.index(end)]
    assert before==after
    proof={'core_exact_r172_sha256':sha(core),'r172_wrapper_sha256':sha(original_wrapper),
           'new_wrapper_sha256':sha(wrapper),'selector_exact_same_sha256':hashlib.sha256(before.encode()).hexdigest(),
           'dispatch_only_scope':'Added outlet_limited_parents, cap continues same eligible sequence, final partial preserved. Core/selector/cost/sameinitial/sink/deadline/budget unchanged.'}
    write(folder/'unchanged-core-selector.json',proof)
    case=None
    for line in (source/'inputs.jsonl').read_text().splitlines():
        item=json.loads(line); data=item['input']
        key=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        if key.startswith(short): case=item; break
    assert case is not None
    data=case['input']; key=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write(folder/'input.json',data)
    baseline_path=source/(short+'-baseline-output.json'); old_dp_path=source/(short+'-dp-actual-output.json')
    shutil.copy2(baseline_path,folder/'baseline-output.json'); shutil.copy2(old_dp_path,folder/'historical-dp21-only-comparison.json')
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'tests/test_tree_pair_wrapper_cap.py',
           ROOT/'scripts/research_tree_pair_anytime_84.py',ROOT/'scripts/research_spine_age_probe.py',
           ROOT/'research/level-stage/tree-pair-outlet-wrapper-plan.md']
    hashes={}
    for path in sources:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        hashes[str(path.relative_to(ROOT))]=sha(path)
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,
                'aggregate_source_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
                'input_sha256':key,'input_file_sha256':sha(folder/'input.json'),
                'baseline_file_sha256':sha(baseline_path),'historical_dp21_sha256':sha(old_dp_path),
                'parameters':source_parameters,'scope':'Before tests and real candidate execution. Only6 synthetic contracts and once ca93 real; no baseline/oracle/84/336/default.'}
    write(folder/'source-provenance.json',provenance)

    spec=importlib.util.spec_from_file_location('wrapper_cap_contract',ROOT/'tests/test_tree_pair_wrapper_cap.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    tests=unittest.defaultTestLoader.loadTestsFromModule(module); test_tick=perf_counter(); result=unittest.TestResult(); tests.run(result)
    test_seconds=perf_counter()-test_tick
    synthetic_paths=[]; synthetic_verify_tick=perf_counter()
    for index,entry in enumerate(module.EMITTED):
        path=folder/(f'synthetic-{index}-output.json'); write(path,entry); synthetic_paths.append(path)
        check(entry['input'],entry['candidate']['output'],entry['candidate']['original_order'])
    for returned in module.RETURNS:
        # No sentinel is sent through raw frontier exporter or claimed as age evidence.
        assert all(s['kind']=='synthetic_dispatch_sentinel' and not s['actual_physical_frontier'] for s in returned['diagnostic_sentinels'])
    synthetic_verify_seconds=perf_counter()-synthetic_verify_tick
    write(folder/'synthetic-control-report.json',{'tests_run':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],
         'elapsed_seconds':test_seconds,'physical_sink_outputs':len(synthetic_paths),
         'physical_verify_seconds':synthetic_verify_seconds,'returns':module.RETURNS,
         'scope':'Synthetic child/frontier counters only, actual physical sink calls each saved and four-checked; no new pair-family search gains.'})
    if not result.wasSuccessful(): raise AssertionError('Wrapper contracts failed; no real ca93 search started')

    baseline=json.loads(baseline_path.read_text()); pre_tick=perf_counter(); check(data,baseline['output'],baseline['original_order'])
    precheck_seconds=perf_counter()-pre_tick
    before=sum(row['op']=='COPY' for row in baseline['output']['optimized_instructions']); assert before==23
    paths=[]; complete_io_seconds=0.0
    def sink(parent,candidate):
        nonlocal complete_io_seconds
        tick=perf_counter(); path=folder/(f'parent{parent}-candidate{len(paths)}-output.json')
        write(path,{'input_sha256':key,'parent':parent,**candidate}); paths.append(path)
        complete_io_seconds+=perf_counter()-tick
    started=perf_counter()
    proposal=refine_fixed_tree_pairs_anytime(data,baseline,time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96,on_completed=sink)
    search_before_export_seconds=perf_counter()-started; best=proposal['best']; stats=proposal['stats']
    export_tick=perf_counter(); exports=export_diagnostics(proposal,folder,key); diagnostic_flow_seconds=perf_counter()-export_tick
    del proposal
    verify_tick=perf_counter()
    for path in paths:
        candidate=json.loads(path.read_text()); check(data,candidate['output'],candidate['original_order'])
    check(data,best['output'],best['original_order']); write(folder/'best-output.json',{'input_sha256':key,**best})
    verify_seconds=perf_counter()-verify_tick
    report={'input_sha256':key,'node_count':64,'window':4,'before_copies':before,'historical_dp21_copies_only_comparison':21,
            'after_copies':best['copies'],'actual_complete_proposals':len(paths),'stats':stats,
            'parameters':source_parameters,'precheck_seconds':precheck_seconds,
            'candidate_seconds_before_export':search_before_export_seconds,'complete_json_io_inside_deadline_seconds':complete_io_seconds,
            'diagnostic_flow_seconds':diagnostic_flow_seconds,
            'diagnostic_export_seconds':sum(row['diagnostic_export_seconds'] for row in exports),
            'diagnostic_json_io_seconds':sum(row['diagnostic_json_io_seconds'] for row in exports),
            'verify_seconds':verify_seconds,'whole_real_stage_seconds':perf_counter()-started,
            'complete_output_bytes':sum(p.stat().st_size for p in paths),
            'diagnostic_bytes':sum((ROOT/row['path']).stat().st_size for row in exports),
            'reached_parent59':any(row['parent']==59 for row in stats['attempts']),
            'scope':'Single real input fixed original23 incumbent, no DP fallback/composition. All complete and actual raw diagnostics saved. Timings not isolation; synthetic controls separate.'}
    write(folder/'report.json',report)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in folder.glob('*') if p.is_file()}
    write(folder/'evidence-provenance.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence})
    print(json.dumps({k:v for k,v in report.items() if k!='stats'})); print(json.dumps({'synthetic_tests':result.testsRun,'synthetic_sink_outputs':len(synthetic_paths),'actual_outcome':stats['outcome'],'attempted_parents':[r['parent'] for r in stats['attempts']],'outlet_limited_parents':stats['outlet_limited_parents'],'processed_states':stats['processed_states']}))


if __name__=='__main__': main()
