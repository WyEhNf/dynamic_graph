"""40 fixed branching/external cases: independent all-order gold plus bounds.

Gold uses a separate raw graph/emitter and enumerates original merges only.
The candidate's500ms/20k/16 bound is distinct from offline exhaustive cost.
"""
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
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_subtree_interleave import schedule_fixed_tree_pair
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check
from scripts.tree_branch_context_cases import generated,interleavings
from tests import test_tree_subtree_interleave as boundary


def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--round',required=True); options=parser.parse_args()
    folder=ROOT/'experiments'/options.round; folder.mkdir(exist_ok=False)
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'scripts/tree_branch_context_cases.py',
        ROOT/'scripts/diagnose_tree_dfs_gap.py',ROOT/'scripts/tree_raw_oracles.py',ROOT/'scripts/research_spine_age_probe.py',
        ROOT/'tests/test_tree_subtree_interleave.py',ROOT/'research/level-stage/tree-subtree-12-input.json',
        ROOT/'research/level-stage/tree-subtree-interleave-proof.md',ROOT/'research/level-stage/tree-subtree-phase2-plan.md']
    manifest={}
    for source in sources:
        target=folder/'src'/source.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
        manifest[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':manifest,
        'aggregate_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
        'scope':'Actual whole source snapshot before gold/boundary execution. Default and all historical sources untouched.'}
    (folder/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    cases=[generated(i) for i in range(40)]
    (folder/'inputs.jsonl').write_text(''.join(json.dumps(case)+'\n' for case in cases))
    started=perf_counter(); records=[]
    for case in cases:
        data=case['input']; key=fingerprint(data); parent=case['parent']; gold_tick=perf_counter()
        baseline={'output':materialize(data,case['baseline_order']),'original_order':case['baseline_order']}
        (folder/(key[:16]+'-baseline-output.json')).write_text(json.dumps(baseline)+'\n')
        gold_best=None; gold_rows=[]; statuses=Counter()
        for local_order in interleavings(*case['side_orders']):
            order=case['prefix']+local_order+[parent]+case['suffix']
            try: output=materialize(data,order)
            except ValueError as error:
                if str(error)!='Restricted relay cannot progress': raise
                gold_rows.append({'original_order':order,'status':'restricted_fixed_order_failure','copies':None})
                statuses['restricted_fixed_order_failure']+=1; continue
            copies=sum(row['op']=='COPY' for row in output['optimized_instructions'])
            gold_rows.append({'original_order':order,'status':'verified_fixed_order','copies':copies})
            statuses['verified_fixed_order']+=1
            if gold_best is None or copies<gold_best['copies']:
                gold_best={'output':output,'original_order':order,'copies':copies}
        if gold_best is None: raise AssertionError('All fixed merges failed despite legal serial incumbent')
        (folder/(key[:16]+'-gold-orders.jsonl')).write_text(''.join(json.dumps(row)+'\n' for row in gold_rows))
        (folder/(key[:16]+'-gold-best-output.json')).write_text(json.dumps(gold_best)+'\n')
        gold_seconds=perf_counter()-gold_tick; emitted=[]; attempt_tick=perf_counter(); phase='schedule'
        def sink(candidate):
            target=folder/(key[:16]+f'-candidate-outlet{len(emitted)}-output.json')
            target.write_text(json.dumps(candidate)+'\n'); emitted.append(candidate)
        try:
            result=schedule_fixed_tree_pair(data,baseline,parent,time_budget_ms=500,max_states=20000,max_outcomes=16,on_completed=sink)
            phase='independent_verify'; outcome='completed'; best=result['best']; stats=result['stats']
        except (BudgetExceeded,InfeasibleSchedule) as error:
            if phase=='independent_verify': raise
            outcome='unknown_budget' if isinstance(error,BudgetExceeded) else 'restricted_candidate_failure'
            best=min(emitted,key=lambda row:row['copies']) if emitted else None
            stats={'message':str(error),'partial_complete_outlets':len(emitted)}
        candidate_seconds=perf_counter()-attempt_tick; verify_tick=perf_counter()
        for candidate in emitted: check(data,candidate['output'],candidate['original_order'])
        if outcome=='completed' and stats['truncated_outlets']==0 and best['copies']!=gold_best['copies']:
            raise AssertionError('Untruncated fixed-order candidate contradicts independent all-merge gold')
        record={'case_id':case['case_id'],'input_sha256':key,'family':case['family'],'window':2**data['bit_width'],
            'external_count':case['external_count'],'nodes':len(data['instructions']),'parent':parent,
            'gold_orders':len(gold_rows),'gold_statuses':dict(statuses),'gold_copies':gold_best['copies'],
            'outcome':outcome,'candidate_copies':best['copies'] if best else None,'completed_outlets':len(emitted),
            'stats':stats,'gold_seconds':gold_seconds,'candidate_seconds':candidate_seconds,
            'verify_seconds':perf_counter()-verify_tick}
        records.append(record); (folder/'partial-records.json').write_text(json.dumps(records,indent=2)+'\n')
    # Boundary test outputs (including an injected deadline partial) are all
    # retained and then independently replayed as real full physical programs.
    boundary.EMITTED.clear(); stream=io.StringIO(); suite=unittest.defaultTestLoader.loadTestsFromModule(boundary)
    test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (folder/'boundary-tests.txt').write_text(stream.getvalue())
    for index,emitted in enumerate(boundary.EMITTED):
        candidate=emitted['candidate']; check(emitted['input'],candidate['output'],candidate['original_order'])
        (folder/f'boundary-{index}-complete-output.json').write_text(json.dumps(emitted)+'\n')
    if not test_result.wasSuccessful(): raise AssertionError('Boundary tests failed; do not advance')
    report={'count':len(records),'records':records,'outcomes':dict(Counter(row['outcome'] for row in records)),
        'total_gold_orders':sum(row['gold_orders'] for row in records),
        'gold_statuses':dict(sum((Counter(row['gold_statuses']) for row in records),Counter())),
        'completed_outlets':sum(row['completed_outlets'] for row in records),'boundary_tests':test_result.testsRun,
        'boundary_actual_complete_outputs':len(boundary.EMITTED),
        'boundary_scope':'Real1state and1e-9ms unknown; deterministically injected deadline after1 real full outlet proves sink preservation, not measured performance timeout.',
        'elapsed_seconds':perf_counter()-started,'parameters':{'candidate_time_budget_ms':500,'max_states':20000,'max_outcomes':16},
        'scope':'Complete fixed-side merge family with deadline COPY. Offline exhaustive raw gold timing separate; every original/orderedarg retained. Not global arbitrary-order/COPY optimum or Level score. Old48/new36 not run.'}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    evidence={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence},indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='records'}))


if __name__=='__main__': main()
