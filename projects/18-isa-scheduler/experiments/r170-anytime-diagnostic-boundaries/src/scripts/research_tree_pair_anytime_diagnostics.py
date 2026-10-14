"""Only authorized boundary diagnostic supplement; never rerun40/84/gold."""
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
from isa_scheduler.tree_pair_anytime import iter_anytime_frontier
from scripts.research_spine_age_probe import check
from tests import test_tree_pair_anytime as boundary


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder=ROOT/'experiments/r170-anytime-diagnostic-boundaries'; folder.mkdir(exist_ok=False)
    old=ROOT/'experiments/r168-tree-pair-anytime-gold/src/isa_scheduler/tree_pair_anytime.py'
    new=ROOT/'isa_scheduler/tree_pair_anytime.py'
    before=old.read_text(); after=new.read_text()
    fragments={
        'heap_queue':(before[before.index('class _Agenda:'):before.index('class _Stop')],after[after.index('class _Agenda:'):after.index('class _Stop')]),
        'complete_physical_restore':(before[before.index('        def restore_goal'):before.index('        initial =')],after[after.index('        def restore_goal'):after.index('        initial =')]),
        'search_goal_prune_interrupt':(before[before.index('        initial ='):before.index('    # No lower-bound')],after[after.index('        initial ='):after.index('    # Capture stop')])}
    if any(left!=right for left,right in fragments.values()): raise AssertionError('Search/heap/restore text changed')
    proof={'before_core_sha256':digest(old),'after_core_sha256':digest(new),
           'exact_equal_fragments':{key:hashlib.sha256(left.encode()).hexdigest() for key,(left,right) in fragments.items()},
           'scope':'Exact source text equality heap/whole restoration/search+f-prune+interruption, no search change. Only metadata ownership/export and initial empty active cache preparation change.'}
    (folder/'unchanged-search-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'tests/test_tree_pair_anytime.py',
        ROOT/'scripts/research_spine_age_probe.py',ROOT/'scripts/diagnose_tree_dfs_gap.py',ROOT/'scripts/tree_raw_oracles.py',
        ROOT/'research/level-stage/tree-pair-anytime-plan.md',ROOT/'research/level-stage/tree-pair-anytime-budget-boundary.md',
        ROOT/'research/level-stage/tree-subtree-12-input.json']
    source_hashes={}
    for path in sources:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        source_hashes[str(path.relative_to(ROOT))]=digest(path)
    (folder/'source-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':source_hashes,'aggregate_sha256':hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest(),
        'scope':'Frozen before only boundary execution; oldR168 evidence/timing untouched, no40gold/84/default run.'},indent=2)+'\n')
    boundary.EMITTED.clear(); boundary.RESULTS.clear(); stream=io.StringIO(); started=perf_counter()
    tested=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(boundary))
    boundary_seconds=perf_counter()-started; (folder/'boundary-tests.txt').write_text(stream.getvalue())
    for index,emitted in enumerate(boundary.EMITTED):
        candidate=emitted['candidate']; check(emitted['input'],candidate['output'],candidate['original_order'])
        (folder/f'boundary-{index}-complete-output.json').write_text(json.dumps(emitted)+'\n')
    if not tested.wasSuccessful(): raise AssertionError('Diagnostic boundary failed')
    records=[]
    for index,item in enumerate(boundary.RESULTS):
        result=item['result']; iterator=iter(iter_anytime_frontier(result['diagnostics']))
        export_seconds=json_io_seconds=0.0; counts=Counter(); path=folder/f'boundary-{index}-frontier.jsonl'
        # Stream one record at a time, do not embed all frontiers in report.
        with path.open('w',encoding='utf-8') as target:
            while True:
                tick=perf_counter()
                try: record=next(iterator)
                except StopIteration:
                    export_seconds+=perf_counter()-tick; break
                export_seconds+=perf_counter()-tick; counts[record['kind']]+=1
                tick=perf_counter(); target.write(json.dumps(record)+'\n'); json_io_seconds+=perf_counter()-tick
        if counts['open']!=result['stats']['actual_open_count']: raise AssertionError('Wrong actual OPEN export')
        best=result['best']; check(item['input'],best['output'],best['original_order'])
        saved={'input':item['input'],'baseline':item['baseline'],'parent':item['parent'],'options':item['options'],
               'best':best,'stats':result['stats'],'frontier_file':str(path.relative_to(ROOT)),
               'diagnostic_export_seconds':export_seconds,'diagnostic_json_io_seconds':json_io_seconds,
               'frontier_record_counts':dict(counts),
               'scope':'Actual returned boundary stats and complete best, exported afterwards. Injected clock deadline tests are contracts, not measured timeout performance.'}
        output=folder/f'boundary-{index}-returned-result.json'; output.write_text(json.dumps(saved,indent=2)+'\n')
        records.append({'index':index,'outcome':result['stats']['outcome'],'processed_states':result['stats']['processed_states'],
            'search_emit_ms':result['stats']['search_emit_ms'],'returned_result_file':str(output.relative_to(ROOT)),
            'diagnostic_export_seconds':export_seconds,'diagnostic_json_io_seconds':json_io_seconds,'frontier_record_counts':dict(counts)})
    report={'boundary_tests':tested.testsRun,'boundary_seconds':boundary_seconds,'actual_complete_proposals':len(boundary.EMITTED),
        'actual_returned_results':len(records),'outcomes':dict(Counter(row['outcome'] for row in records)),
        'diagnostic_export_seconds':sum(row['diagnostic_export_seconds'] for row in records),
        'diagnostic_json_io_seconds':sum(row['diagnostic_json_io_seconds'] for row in records),
        'records':records,'scope':'Diagnostic-only supplement; exact search/heap/physical restore unchanged; no old clock or old partial filled, no40gold/84/full336/default run. Frontiers streamed outside search budget.'}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    evidence={str(p.relative_to(ROOT)):digest(p) for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__': main()
