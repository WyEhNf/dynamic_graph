"""Root full-output review of fixed-family AWA* and saved independent gold."""
import json
import subprocess
import time
from review_stage2_tree_branch_context_gold import ROOT,P,read_lines,replay,fingerprint,sha


def main():
    d=P/'experiments/r168-tree-pair-anytime-gold';read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    source=read(d/'source-provenance.json')
    for name,digest in source['source_sha256'].items():assert sha(d/'src'/name)==digest
    for name,digest in source['frozen_gold_sha256'].items():assert sha(d/'frozen-gold'/__import__('pathlib').Path(name).name)==sha(P/name)==digest
    for name,digest in read(d/'evidence-provenance.json')['evidence_sha256'].items():assert sha(P/name)==digest
    report=read(d/'report.json');cases={c['case_id']:c for c in read_lines(d/'frozen-gold/inputs.jsonl')}
    assert len(cases)==len(report['records'])==40
    oldroot=read(ROOT/'outputs/stage2-root-tree-branch-context-gold.json');assert oldroot['passed'] and oldroot['independently_enumerated_full_orders']==8960
    frozenold=read(d/'frozen-gold/report.json');old={r['case_id']:r for r in frozenold['records']}
    replays=outlets=states=before=after=0;zero12=0
    def check(data,record):
        nonlocal replays
        cost=replay(data,dict(record,input_sha256=fingerprint(data)));replays+=1
        if 'copies' in record:assert cost==record['copies']
        return cost
    for row in report['records']:
        c=cases[row['case_id']];data=c['input'];key=fingerprint(data);prefix=key[:16]
        assert key==row['input_sha256'] and row['parent']==c['parent']
        baseline=read(d/'frozen-gold'/(prefix+'-baseline-output.json'));b=check(data,baseline)
        gold=read(d/'frozen-gold'/(prefix+'-gold-best-output.json'));g=check(data,gold)
        saved=read_lines(d/'frozen-gold'/(prefix+'-gold-orders.jsonl'));bank={tuple(r['original_order']):r for r in saved}
        assert len(saved)==len(bank)==old[c['case_id']]['gold_orders']==row['gold_orders']
        assert min(r['copies'] for r in saved if r['copies'] is not None)==g==row['gold_copies']
        assert row['gold_statuses']==old[c['case_id']]['gold_statuses']
        files=sorted(d.glob(prefix+'-candidate-outlet*-output.json'));assert len(files)==row['completed_outlets']
        costs=[]
        for path in files:
            record=read(path);order=record['original_order'];start=len(c['prefix']);stop=len(order)-len(c['suffix'])-1
            assert order[:start]==c['prefix'] and order[stop]==c['parent'] and order[stop+1:]==c['suffix']
            middle=order[start:stop];left,right=c['side_orders']
            assert [v for v in middle if v in left]==left and [v for v in middle if v in right]==right
            cost=check(data,record);costs.append(cost)
            assert bank[tuple(order)]['status']=='verified_fixed_order' and bank[tuple(order)]['copies']==cost
        best=read(d/(prefix+'-best-output.json'));a=check(data,best)
        assert a==min([b]+costs)==min(b,g)==row['retained_copies'] and b==row['baseline_copies']
        stats=row['stats'];assert stats['weight']==2 and stats['outcome']==row['outcome']=='exhausted_improvement_search'
        assert stats['processed_states']==stats['states']==sum(stats['expanded_by_progress'].values())<=20000
        assert stats['complete_outputs']==len(files)<=16 and stats['actual_open_count']==0 and stats['actual_open_frontier']==[] and stats['unfinished_expansion'] is None
        assert stats['reopens']==stats['stale_entries']==0
        assert stats['parameters']==dict(total_time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96)
        if stats['first_complete'] is not None:assert stats['first_complete']['processed_states']<=stats['processed_states'] and stats['first_complete']['elapsed_ms']<=stats['elapsed_ms']
        states+=stats['processed_states'];outlets+=len(files);before+=b;after+=a
    boundary=sorted(d.glob('boundary-*-complete-output.json'));assert len(boundary)==5
    for path in boundary:
        row=read(path);cost=check(row['input'],row['candidate'])
        if len(row['input']['instructions'])==12 and cost==0:zero12+=1
    assert zero12 and (outlets,states,before,after)==(38,2461,89,53)
    assert report['matches_frozen_retained_gold']==40 and report['frozen_gold_orders']==8960
    # Frozen tests exercise tiny budgets and synthetic agenda labels; they do
    # not imply actual physical schedules exercised reopen/stale branches.
    folder=ROOT/'outputs/stage2-root-tree-pair-anytime-gold';folder.mkdir(exist_ok=True)
    program="import sys,unittest;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import tests.test_tree_pair_anytime as t;t.ROOT=Path(sys.argv[2]);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(t));sys.exit(not r.wasSuccessful())"
    proc=subprocess.run(['python','-c',program,str(d/'src'),str(P)],capture_output=True,text=True,timeout=30)
    (folder/'boundary-root.stdout').write_text(proc.stdout,encoding='utf-8');(folder/'boundary-root.stderr').write_text(proc.stderr,encoding='utf-8')
    assert proc.returncode==0 and 'Ran 6 tests' in proc.stderr and '\nOK\n' in proc.stderr
    result=dict(passed=True,reviewed_unix=time.time(),source_provenance_sha256=sha(d/'source-provenance.json'),report_sha256=sha(d/'report.json'),
        frozen_source_files=len(source['source_sha256']),frozen_gold_files=len(source['frozen_gold_sha256']),original_gold_cases=40,
        reused_independent_full_merge_gold=8960,actual_new_outlets_replayed=38,actual_boundary_outputs_replayed=5,
        actual_full_replay_instances=replays,processed_states=2461,before_copies=89,after_copies=53,
        actual_graph_reopens=0,actual_graph_stale_entries=0,synthetic_queue_contracts_separate=True,root_actual_boundary_tests=6,root_actual_exit_code=proc.returncode,
        scope='All40 original fixed-merge inputs/cached baselines and independently verified8960 order gold retained. All38 new full outlets,40 bests,5 boundary programs and frozen baselines/golds independently replayed;40 retained minima equal min(baseline,fixed-family gold). All40 OPEN exhausted. Synthetic-only reopen/stale contract rerun, no real-graph coverage claim. No84/full336/default/official Level result.',
        limitation='R168 returns materialized diagnostic frontier after search/emit stop and does not separately time that export;40 real gold OPENs are empty, so no active-state export occurred there. Partial boundary frontiers not archived. Correct budget/export accounting and saved partial boundaries required before84.')
    (ROOT/'outputs/stage2-root-tree-pair-anytime-gold.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
