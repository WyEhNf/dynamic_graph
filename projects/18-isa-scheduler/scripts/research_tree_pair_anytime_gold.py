"""Authorized40 frozen gold replay; no old oracle/baseline/84 scheduling."""
import argparse
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
from isa_scheduler.tree_pair_anytime import schedule_fixed_tree_pair_anytime
from scripts.research_spine_age_probe import check
from tests import test_tree_pair_anytime as boundary


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--round',required=True); options=parser.parse_args()
    folder=ROOT/'experiments'/options.round; folder.mkdir(exist_ok=False)
    origin=ROOT/'experiments/r163-tree-branch-context-gold'
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'tests/test_tree_pair_anytime.py',
        ROOT/'scripts/research_spine_age_probe.py',ROOT/'scripts/diagnose_tree_dfs_gap.py',ROOT/'scripts/tree_raw_oracles.py',
        ROOT/'research/level-stage/tree-pair-anytime-plan.md',ROOT/'research/level-stage/tree-subtree-12-input.json']
    source_hashes={}
    for path in sources:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        source_hashes[str(path.relative_to(ROOT))]=sha(path)
    gold_report=json.loads((origin/'report.json').read_text()); gold_bank={r['input_sha256']:r for r in gold_report['records']}
    frozen_hashes=json.loads((origin/'evidence-provenance.json').read_text())['evidence_sha256']
    cases=[json.loads(line) for line in (origin/'inputs.jsonl').read_text().splitlines()]
    copied=[]
    for path in [origin/'report.json',origin/'inputs.jsonl']+list(origin.glob('*-baseline-output.json'))+list(origin.glob('*-gold-best-output.json'))+list(origin.glob('*-gold-orders.jsonl')):
        if sha(path)!=frozen_hashes[str(path.relative_to(ROOT))]: raise AssertionError('Historical evidence changed')
        target=folder/'frozen-gold'/path.name; target.parent.mkdir(exist_ok=True); shutil.copy2(path,target); copied.append(path)
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source_hashes,
        'aggregate_sha256':hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest(),
        'frozen_gold_sha256':{str(p.relative_to(ROOT)):sha(p) for p in copied},
        'parameters':{'fixed_weight':2,'total_time_budget_ms':500,'max_states':20000,'max_outcomes':16,'max_parent_nodes':96},
        'scope':'Source/gold frozen before execution. Only40 existing gold cases and boundary tests. No old baseline/oracle/84/default/full336 run.'}
    (folder/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    stream=io.StringIO(); boundary.EMITTED.clear()
    test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(boundary))
    (folder/'boundary-tests.txt').write_text(stream.getvalue())
    for index,emitted in enumerate(boundary.EMITTED):
        candidate=emitted['candidate']; check(emitted['input'],candidate['output'],candidate['original_order'])
        (folder/f'boundary-{index}-complete-output.json').write_text(json.dumps(emitted)+'\n')
    if not test_result.wasSuccessful(): raise AssertionError('Boundary failed,40 not started')
    started=perf_counter(); records=[]
    for case in cases:
        data=case['input']; key=fingerprint(data); old=gold_bank[key]
        baseline=json.loads((origin/(key[:16]+'-baseline-output.json')).read_text())
        gold=json.loads((origin/(key[:16]+'-gold-best-output.json')).read_text())
        check(data,baseline['output'],baseline['original_order']); check(data,gold['output'],gold['original_order'])
        rows=[json.loads(line) for line in (origin/(key[:16]+'-gold-orders.jsonl')).read_text().splitlines()]
        if len(rows)!=old['gold_orders'] or dict(Counter(r['status'] for r in rows))!=old['gold_statuses']:
            raise AssertionError('Frozen gold coverage mismatch')
        baseline_cost=sum(row['op']=='COPY' for row in baseline['output']['optimized_instructions'])
        emitted=[]; tick=perf_counter()
        def sink(candidate):
            path=folder/(key[:16]+f'-candidate-outlet{len(emitted)}-output.json')
            path.write_text(json.dumps(candidate)+'\n'); emitted.append(candidate)
        result=schedule_fixed_tree_pair_anytime(data,baseline,case['parent'],time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96,on_completed=sink)
        candidate_seconds=perf_counter()-tick; verify_tick=perf_counter()
        for candidate in emitted:
            check(data,candidate['output'],candidate['original_order'])
            if candidate['copies']<old['gold_copies']: raise AssertionError('Candidate beat independent fixed-family gold')
        best=result['best']; check(data,best['output'],best['original_order'])
        target=min(baseline_cost,old['gold_copies'])
        if result['stats']['outcome']=='exhausted_improvement_search' and best['copies']!=target:
            raise AssertionError('Completed improvement search disagrees with frozen gold')
        if best['copies']>baseline_cost or best['copies']<target: raise AssertionError('Fallback/independent lower-cost bound violated')
        if result['stats']['processed_states']>20000: raise AssertionError('State budget exceeded')
        (folder/(key[:16]+'-best-output.json')).write_text(json.dumps(best)+'\n')
        record={'case_id':case['case_id'],'input_sha256':key,'nodes':len(data['instructions']),'window':2**data['bit_width'],
            'external_count':case['external_count'],'parent':case['parent'],'baseline_copies':baseline_cost,
            'gold_copies':old['gold_copies'],'retained_copies':best['copies'],'matches_retained_gold':best['copies']==target,
            'outcome':result['stats']['outcome'],'completed_outlets':len(emitted),'stats':result['stats'],
            'gold_orders':old['gold_orders'],'gold_statuses':old['gold_statuses'],
            'candidate_seconds':candidate_seconds,'verify_seconds':perf_counter()-verify_tick}
        records.append(record); (folder/'partial-records.json').write_text(json.dumps(records,indent=2)+'\n')
    report={'count':len(records),'outcomes':dict(Counter(r['outcome'] for r in records)),
        'matches_frozen_retained_gold':sum(r['matches_retained_gold'] for r in records),
        'frozen_gold_orders':sum(r['gold_orders'] for r in records),'frozen_gold_statuses':dict(sum((Counter(r['gold_statuses']) for r in records),Counter())),
        'candidate_complete_outputs':sum(r['completed_outlets'] for r in records),
        'before_copies':sum(r['baseline_copies'] for r in records),'after_copies':sum(r['retained_copies'] for r in records),
        'boundary_tests':test_result.testsRun,'boundary_actual_complete_outputs':len(boundary.EMITTED),
        'elapsed_seconds':perf_counter()-started,'records':records,'parameters':provenance['parameters'],
        'scope':'40 frozen independent gold without rerunning old gold/baselines. Complete original+COPY objective, no COPY multiplicative guarantee. No84/default/full336 change. Frontier metadata and external serialization are not hard wall guarantees.'}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    evidence={str(p.relative_to(ROOT)):sha(p) for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__': main()
