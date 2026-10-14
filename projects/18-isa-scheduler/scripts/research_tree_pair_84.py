"""One declared84 fixed-incumbent batch; no old scheduler run or promotion."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter
import unittest

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.tree_pair_refine import refine_fixed_tree_pairs
from scripts.research_spine_age_probe import check
from tests import test_tree_pair_refine as boundary


def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def summary(records):
    successful=[r for r in records if r['after_copies'] is not None]
    return {'count':len(records),'before_statuses':dict(Counter(r['before_status'] for r in records)),
        'after_statuses':dict(Counter(r['after_status'] for r in records)),
        'before_copies':sum(r['before_copies'] or 0 for r in records),'after_copies':sum(r['after_copies'] or 0 for r in records),
        'improved':sum(r['after_copies'] is not None and r['after_copies']<r['before_copies'] for r in records),
        'attempt_outcomes':dict(Counter(r['attempt']['outcome'] for r in records)),
        'successful_count':len(successful),
        'before_success_copy_output_mean':sum(r['before_copies']/(r['node_count']+r['before_copies']) for r in successful)/len(successful),
        'after_success_copy_output_mean':sum(r['after_copies']/(r['node_count']+r['after_copies']) for r in successful)/len(successful),
        'before_success_copy_original_mean':sum(r['before_copies']/r['node_count'] for r in successful)/len(successful),
        'after_success_copy_original_mean':sum(r['after_copies']/r['node_count'] for r in successful)/len(successful)}


def main():
    folder=ROOT/'experiments/r164-tree-pair-warmstart-84'; folder.mkdir(exist_ok=False)
    paths=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'tests/test_tree_pair_refine.py',
        ROOT/'scripts/research_spine_age_probe.py',ROOT/'scripts/diagnose_tree_dfs_gap.py',ROOT/'scripts/tree_raw_oracles.py',
        ROOT/'research/level-stage/tree-pair-84-execution-plan.md',ROOT/'research/level-stage/tree-subtree-12-input.json']
    sources={}
    for path in paths:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    source_names={'old48':'r155-tree-pipeline-old48','new36':'r156-tree-pipeline-heldout36'}; cases=[]; banks={}; origin={}
    for group,name in source_names.items():
        source=ROOT/'experiments'/name
        text=(source/'inputs.jsonl').read_text(); (folder/(group+'-inputs.jsonl')).write_text(text)
        banks[group]={r['sha256']:r for r in json.loads((source/'report.json').read_text())['records']}
        cases.extend((group,case) for case in map(json.loads,text.splitlines()))
        for p in [source/'report.json',source/'inputs.jsonl']+list(source.glob('*-output.json')):
            # Record the actual saved-output baseline files, not rescheduling.
            origin[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (folder/'inputs.jsonl').write_text(''.join(json.dumps({'group':group,**case})+'\n' for group,case in cases))
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sources,'baseline_evidence_sha256':origin,
        'aggregate_sha256':hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        'parameters':{'total_time_budget_ms_each_input':500,'total_processed_states_each_input':20000,'outlets_each_pair':16,'parent_nodes_max':96},
        'scope':'Actual source/input/baseline plan frozen before tests/candidates. All84 denominator retained. Same initial incumbent per proposal.'}
    (folder/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    test_stream=io.StringIO(); boundary.EMITTED.clear()
    suite=unittest.defaultTestLoader.loadTestsFromModule(boundary)
    test_result=unittest.TextTestRunner(stream=test_stream,verbosity=2).run(suite)
    (folder/'boundary-tests.txt').write_text(test_stream.getvalue())
    for index,emitted in enumerate(boundary.EMITTED):
        candidate=emitted['candidate']; check(emitted['input'],candidate['output'],candidate['original_order'])
        (folder/f'boundary-{index}-output.json').write_text(json.dumps(emitted)+'\n')
    if not test_result.wasSuccessful(): raise AssertionError('Wrapper boundary failed;84 not started')
    records=[]; started=perf_counter()
    for group,case in cases:
        data=case['input']; key=fingerprint(data); old=banks[group][key]
        source=ROOT/'experiments'/source_names[group]; path=source/(key[:16]+'-output.json')
        incumbent=json.loads(path.read_text()) if path.exists() else None; before=old['after_copies']
        best=None if incumbent is None else {'output':incumbent['output'],'original_order':incumbent['original_order'],'copies':before}
        if incumbent is not None:
            check(data,incumbent['output'],incumbent['original_order'])
            assert sum(row['op']=='COPY' for row in incumbent['output']['optimized_instructions'])==before
            (folder/(key[:16]+'-baseline-output.json')).write_text(json.dumps(incumbent)+'\n')
        emitted_paths=[]; attempt={'outcome':'not_attempted_zero_or_no_incumbent'}; tick=perf_counter()
        if incumbent is not None and before:
            def sink(parent,candidate):
                target=folder/(key[:16]+f'-parent{parent}-candidate{len(emitted_paths)}-output.json')
                target.write_text(json.dumps({'input_sha256':key,'parent':parent,**candidate})+'\n'); emitted_paths.append(target)
            result=refine_fixed_tree_pairs(data,incumbent,time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96,on_completed=sink)
            best=result['best']; attempt={'outcome':result['stats']['outcome'],'stats':result['stats']}
            if result['stats']['processed_states']>20000: raise AssertionError('Cumulative budget violation')
        candidate_seconds=perf_counter()-tick; verify_tick=perf_counter()
        for emitted_path in emitted_paths:
            candidate=json.loads(emitted_path.read_text()); check(data,candidate['output'],candidate['original_order'])
        if best is not None:
            check(data,best['output'],best['original_order'])
            if best['copies']>before: raise AssertionError('Lost incumbent')
            (folder/(key[:16]+'-output.json')).write_text(json.dumps({'input_sha256':key,**best})+'\n')
        attempt.update({'candidate_seconds':candidate_seconds,'verify_seconds':perf_counter()-verify_tick,'completed_output_files':len(emitted_paths)})
        record={'group':group,'sha256':key,'family':case['family'],'node_count':len(data['instructions']),'bit_width':data['bit_width'],
            'before_status':old['after_status'],'after_status':old['after_status'] if best is None else 'verified',
            'before_copies':before,'after_copies':None if best is None else best['copies'],'attempt':attempt}
        records.append(record); (folder/'partial-records.json').write_text(json.dumps(records,indent=2)+'\n')
    result={**summary(records),'records':records,'groups':{group:summary([r for r in records if r['group']==group]) for group in source_names},
        'elapsed_seconds':perf_counter()-started,'boundary_tests':test_result.testsRun,'boundary_complete_outputs':len(boundary.EMITTED),
        'source_parameters':provenance['parameters'],
        'scope':'Fixed84 full input status denominator. Success-only means clearly separate; no whole336 or officialLevel claim.500ms candidate includes sink, not old incumbent creation/independentverify/whole CLI wall. All complete worse and partial outputs saved; proposals not composed.'}
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    evidence={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence},indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('records','groups')})); print(json.dumps(result['groups']))


if __name__=='__main__': main()
