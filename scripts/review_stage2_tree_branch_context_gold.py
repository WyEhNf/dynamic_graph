"""Recompute every fixed merge independently and replay all actual outlets."""
import itertools
import json
import time
from collections import Counter
from review_stage2_tree_pair_serial_controls import ROOT,P,emit,replay,fingerprint,read_lines,sha

D=P/'experiments/r163-tree-branch-context-gold'


def main():
    evidence={}
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        return json.loads(path.read_text(encoding='utf-8'))
    source=read(D/'source-provenance.json')
    for name,digest in source['source_sha256'].items():assert sha(D/'src'/name)==digest
    manifest=read(D/'evidence-provenance.json')
    for name,digest in manifest['evidence_sha256'].items():assert sha(P/name)==digest
    report=read(D/'report.json')
    cases={c['case_id']:c for c in read_lines(D/'inputs.jsonl')}
    assert len(cases)==len(report['records'])==40
    assert report['parameters']==dict(candidate_time_budget_ms=500,max_states=20000,max_outcomes=16)
    replays,orders,outlets=0,0,0;statuses=Counter()
    def check(data,record):
        nonlocal replays
        record=dict(record,input_sha256=fingerprint(data))
        cost=replay(data,record);replays+=1
        if 'copies' in record:assert cost==record['copies']
        return cost
    for row in report['records']:
        case=cases[row['case_id']];data=case['input'];key=fingerprint(data)
        assert key==row['input_sha256']
        baseline=read(D/(key[:16]+'-baseline-output.json'));check(data,baseline)
        assert emit(data,case['baseline_order'])['optimized_instructions']==baseline['output']['optimized_instructions']
        saved=read_lines(D/(key[:16]+'-gold-orders.jsonl'))
        bank={tuple(r['original_order']):r for r in saved};assert len(bank)==len(saved)
        left,right=case['side_orders'];expected_count=0;costs=[];localstatuses=Counter()
        for left_positions in itertools.combinations(range(len(left)+len(right)),len(left)):
            chosen=set(left_positions);a,b=iter(left),iter(right)
            middle=[next(a) if i in chosen else next(b) for i in range(len(left)+len(right))]
            order=case['prefix']+middle+[case['parent']]+case['suffix']
            record=bank.pop(tuple(order));result=emit(data,order)
            if result is None:
                status='restricted_fixed_order_failure';assert record['copies'] is None
            else:
                status='verified_fixed_order';cost=sum(r['op']=='COPY' for r in result['optimized_instructions'])
                assert cost==record['copies'];costs.append(cost)
            assert status==record['status'];statuses[status]+=1;localstatuses[status]+=1
            expected_count+=1
        assert not bank and expected_count==row['gold_orders'] and dict(localstatuses)==row['gold_statuses']
        assert min(costs)==row['gold_copies']==row['candidate_copies']
        best=read(D/(key[:16]+'-gold-best-output.json'));assert check(data,best)==min(costs)
        assert row['outcome']=='completed' and row['stats']['truncated_outlets']==0
        actualcosts=[]
        for i in range(row['completed_outlets']):
            record=read(D/(key[:16]+f'-candidate-outlet{i}-output.json'))
            order=record['original_order'];start=len(case['prefix']);stop=len(order)-len(case['suffix'])-1
            assert order[:start]==case['prefix'] and order[stop+1:]==case['suffix'] and order[stop]==case['parent']
            middle=order[start:stop]
            assert [x for x in middle if x in left]==left and [x for x in middle if x in right]==right
            actualcosts.append(check(data,record))
        assert min(actualcosts)==min(costs)
        outlets+=len(actualcosts);orders+=expected_count
    assert (orders,outlets,statuses['verified_fixed_order'],statuses['restricted_fixed_order_failure'])==(8960,372,6602,2358)
    boundarypaths=sorted(D.glob('boundary-*-complete-output.json'))
    assert len(boundarypaths)==report['boundary_actual_complete_outputs']==17
    zero12=0
    for path in boundarypaths:
        record=read(path);cost=check(record['input'],record['candidate'])
        if len(record['input']['instructions'])==12 and cost==0:zero12+=1
    assert zero12>0 and 'Ran 4 tests' in (D/'boundary-tests.txt').read_text() and '\nOK\n' in (D/'boundary-tests.txt').read_text()
    result=dict(passed=True,reviewed_unix=time.time(),cases=40,independently_enumerated_full_orders=orders,
        independently_emitted_legal_orders=6602,independently_reproduced_restricted_failures=2358,
        all_actual_candidate_outlets_replayed=outlets,actual_boundary_outputs_replayed=17,
        actual_full_output_replay_instances=replays,frozen_sources=len(source['source_sha256']),evidence=evidence,
        scope='Independent combinations-based complete fixed-side enumeration and set-based physical emitter agree with all8960 saved order/status/cost records;372actual candidate outlets+17boundaries+40baselines+40gold outputs replayed. All40 complete untruncated candidates match local fixedmerge optimum. Restricted order failures are not graph infeasibility;12node zeroCOPY is localcontrol, injected deadline tests preservation only. Not global arbitraryorder/earlyCOPY optimum, default/full336 or officialLevel result.')
    (ROOT/'outputs/stage2-root-tree-branch-context-gold.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))


if __name__=='__main__':main()
