"""Once-only same84/same initial baselines; explicit AWA*, no old reruns."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.tree_pair_anytime import iter_anytime_frontier
from isa_scheduler.tree_pair_anytime_refine import refine_fixed_tree_pairs_anytime
from scripts.research_spine_age_probe import check


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def summarize(records):
    legal=[r for r in records if r['after_copies'] is not None]
    metrics={'count':len(records),'successful_count':len(legal),
        'before_statuses':dict(Counter(r['before_status'] for r in records)),
        'after_statuses':dict(Counter(r['after_status'] for r in records)),
        'before_copies':sum(r['before_copies'] or 0 for r in records),
        'dp_actual_copies':sum(r['dp_actual_copies'] or 0 for r in records),
        'after_copies':sum(r['after_copies'] or 0 for r in records),
        'improved_vs_initial':sum(r['after_copies']<r['before_copies'] for r in legal),
        'improved_vs_dp':sum(r['after_copies']<r['dp_actual_copies'] for r in legal),
        'worse_vs_dp':sum(r['after_copies']>r['dp_actual_copies'] for r in legal),
        'attempt_outcomes':dict(Counter(r['attempt']['outcome'] for r in records)),
        'actual_complete_proposals':sum(r['attempt'].get('completed_output_files',0) for r in records)}
    for field,label in [('before_copies','initial'),('dp_actual_copies','dp'),('after_copies','awa')]:
        metrics[label+'_success_copy_output_mean']=sum(r[field]/(r['node_count']+r[field]) for r in legal)/len(legal)
        metrics[label+'_success_copy_original_mean']=sum(r[field]/r['node_count'] for r in legal)/len(legal)
    return metrics


def export_diagnostics(result,folder,key):
    snapshots=result.pop('diagnostics'); exports=[]; attempts=result['stats']['attempts']
    for index,snapshot in enumerate(snapshots):
        attempt=next(item for item in attempts if item.get('diagnostic_reference')==index)
        path=folder/(key[:16]+f'-pair{index}-parent{attempt["parent"]}-frontier.jsonl')
        iterator=iter(iter_anytime_frontier(snapshot)); export_seconds=json_io_seconds=0.0; counts=Counter()
        tick=perf_counter(); target=path.open('w',encoding='utf-8'); json_io_seconds+=perf_counter()-tick
        try:
            while True:
                tick=perf_counter()
                try: item=next(iterator)
                except StopIteration:
                    export_seconds+=perf_counter()-tick; break
                export_seconds+=perf_counter()-tick; counts[item['kind']]+=1
                tick=perf_counter(); target.write(json.dumps(item)+'\n'); json_io_seconds+=perf_counter()-tick
        finally:
            tick=perf_counter(); target.close(); json_io_seconds+=perf_counter()-tick
        if counts['open']!=attempt['stats']['actual_open_count']: raise AssertionError('Actual frontier export mismatch')
        exported={'parent':attempt['parent'],'path':str(path.relative_to(ROOT)),
            'diagnostic_export_seconds':export_seconds,'diagnostic_json_io_seconds':json_io_seconds,
            'record_counts':dict(counts)}
        exports.append(exported); attempt['diagnostic_export']=exported
        snapshots[index]=None; del iterator,snapshot
    snapshots.clear()
    return exports


def main():
    folder=ROOT/'experiments/r172-tree-pair-anytime-84'; folder.mkdir(exist_ok=False)
    old_folder=ROOT/'experiments/r164-tree-pair-warmstart-84'
    old_wrapper=old_folder/'src/isa_scheduler/tree_pair_refine.py'; new_wrapper=ROOT/'isa_scheduler/tree_pair_anytime_refine.py'
    old_text=old_wrapper.read_text(); new_text=new_wrapper.read_text()
    old_selection=old_text[old_text.index('        block=parse_block'):old_text.index('        for parent,child_copies')]
    new_selection=new_text[new_text.index('        block=parse_block'):new_text.index('        for parent,child_copies')]
    if old_selection!=new_selection: raise AssertionError('FrozenR164 selector text changed')
    proof={'frozen_r164_wrapper_sha256':sha(old_wrapper),'current_wrapper_sha256':sha(new_wrapper),
        'selector_fragment_exact_equal_sha256':hashlib.sha256(old_selection.encode()).hexdigest(),
        'scope':'Exact identical parse/matcher/closure/COPY attribution/eligible filter/ranking; only isolated child search and diagnostics handling differ.'}
    (folder/'unchanged-selector-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    old_report=json.loads((old_folder/'report.json').read_text()); dp_bank={r['sha256']:r for r in old_report['records']}
    cases=[json.loads(line) for line in (old_folder/'inputs.jsonl').read_text().splitlines()]
    if len(cases)!=84: raise AssertionError('Must retain all84')
    source_names={'old48':'r155-tree-pipeline-old48','new36':'r156-tree-pipeline-heldout36'}
    banks={}; baselines={}; historical={}
    for group,name in source_names.items():
        origin=ROOT/'experiments'/name; banks[group]={r['sha256']:r for r in json.loads((origin/'report.json').read_text())['records']}
    for case in cases:
        key=fingerprint(case['input']); group=case['group']; origin=ROOT/'experiments'/source_names[group]
        before=banks[group][key]; dp=dp_bank[key]
        if before['after_status']!=dp['before_status'] or before['after_copies']!=dp['before_copies']:
            raise AssertionError('R164 did not start from exact original baseline')
        path=origin/(key[:16]+'-output.json')
        if path.exists():
            baseline=json.loads(path.read_text()); old_baseline=json.loads((old_folder/(key[:16]+'-baseline-output.json')).read_text())
            if baseline!=old_baseline: raise AssertionError('Saved baseline changed')
            baselines[key]=baseline
            target=folder/(key[:16]+'-baseline-output.json'); shutil.copy2(path,target)
            historical[str(path.relative_to(ROOT))]=sha(path)
            dp_path=old_folder/(key[:16]+'-output.json'); shutil.copy2(dp_path,folder/(key[:16]+'-dp-actual-output.json'))
            historical[str(dp_path.relative_to(ROOT))]=sha(dp_path)
        elif before['after_status']=='verified': raise AssertionError('Legal baseline file missing')
    for path in [old_folder/'report.json',old_folder/'inputs.jsonl',old_folder/'source-provenance.json']:
        historical[str(path.relative_to(ROOT))]=sha(path)
    shutil.copy2(old_folder/'inputs.jsonl',folder/'inputs.jsonl')
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'scripts/research_spine_age_probe.py',
        ROOT/'scripts/diagnose_tree_dfs_gap.py',ROOT/'scripts/tree_raw_oracles.py',
        ROOT/'research/level-stage/tree-pair-anytime-plan.md',ROOT/'research/level-stage/tree-pair-anytime-84-plan.md']
    hashes={}
    for path in sources:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        hashes[str(path.relative_to(ROOT))]=sha(path)
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,
        'aggregate_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
        'saved_baseline_dp_evidence_sha256':historical,'frozen_inputs_sha256':sha(folder/'inputs.jsonl'),
        'parameters':{'fixed_weight':2,'total_time_budget_ms_each_input':500,'total_processed_states_each_input':20000,'complete_outlets_each_pair':16,'parent_nodes_max':96},
        'scope':'Before any candidate execution, freeze all84 original inputs/initial saved baselines, oldDP actual outputs and selector. Single run/no old scheduler/oracle/gold/336/default.'}
    (folder/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    records=[]; started=perf_counter()
    for case in cases:
        data=case['input']; key=fingerprint(data); group=case['group']; old=banks[group][key]; dp=dp_bank[key]
        baseline=baselines.get(key); before=old['after_copies']; best=None; exported=[]; paths=[]
        if baseline is not None: check(data,baseline['output'],baseline['original_order'])
        attempt={'outcome':'not_attempted_zero_or_no_incumbent'}; tick=perf_counter()
        if baseline is not None and before:
            def sink(parent,candidate):
                path=folder/(key[:16]+f'-parent{parent}-candidate{len(paths)}-output.json')
                path.write_text(json.dumps({'input_sha256':key,'parent':parent,**candidate})+'\n'); paths.append(path)
            result=refine_fixed_tree_pairs_anytime(data,baseline,time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96,on_completed=sink)
            candidate_seconds=perf_counter()-tick; best=result['best']; attempt={'outcome':result['stats']['outcome'],'stats':result['stats']}
            # Whole input search stopped before this first diagnostics export.
            export_tick=perf_counter(); exported=export_diagnostics(result,folder,key); diagnostic_flow_seconds=perf_counter()-export_tick
            del result
        else:
            candidate_seconds=perf_counter()-tick; diagnostic_flow_seconds=0.0
            if baseline is not None: best={'output':baseline['output'],'original_order':baseline['original_order'],'copies':before}
        verify_tick=perf_counter()
        for path in paths:
            candidate=json.loads(path.read_text()); check(data,candidate['output'],candidate['original_order'])
        if best is not None:
            check(data,best['output'],best['original_order'])
            if best['copies']>before: raise AssertionError('Original incumbent lost')
            (folder/(key[:16]+'-best-output.json')).write_text(json.dumps({'input_sha256':key,**best})+'\n')
        attempt.update({'candidate_seconds_before_export':candidate_seconds,'diagnostic_flow_seconds':diagnostic_flow_seconds,
            'diagnostic_export_seconds':sum(e['diagnostic_export_seconds'] for e in exported),
            'diagnostic_json_io_seconds':sum(e['diagnostic_json_io_seconds'] for e in exported),
            'diagnostic_files':len(exported),'verify_seconds':perf_counter()-verify_tick,'completed_output_files':len(paths)})
        record={'group':group,'sha256':key,'family':case['family'],'node_count':len(data['instructions']),'bit_width':data['bit_width'],
            'before_status':old['after_status'],'after_status':old['after_status'] if best is None else 'verified',
            'before_copies':before,'dp_actual_copies':dp['after_copies'],'after_copies':None if best is None else best['copies'],'attempt':attempt}
        records.append(record); (folder/'partial-records.json').write_text(json.dumps(records,indent=2)+'\n')
        # Only compact record/filepaths survive. All current-input diagnostics
        # references have been released before this next-input boundary.
    report={**summarize(records),'groups':{group:summarize([r for r in records if r['group']==group]) for group in source_names},
        'records':records,'elapsed_seconds':perf_counter()-started,'source_parameters':provenance['parameters'],
        'scope':'All84 statuses retained. Initial baselines are exactR155/R156, R164 best only oldDP comparison. Success means not all84/officialLevel. No gain composition, no336/default. Search stops before diagnostics streamed/released perpair; all full candidate sinks inside deadline, export/JSONIO/verification outside and separately measured.'}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    evidence={str(p.relative_to(ROOT)):sha(p) for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','groups')})); print(json.dumps(report['groups']))


if __name__=='__main__': main()
