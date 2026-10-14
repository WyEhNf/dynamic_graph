"""Root all67 terminal outcomes and independent helper/whole plan physics."""
import json
import time
from collections import Counter
from review_stage2_observer_r52 import ROOT,P,sha,simulate

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    d=P/'research/batch54';completion=read(d/'completion.json')
    negative=read(d/'negative-checkpoint.json')
    for row in negative['files']:assert sha(P/row['path'])==row['sha256']
    for row in completion['files']:assert sha(P/row['path'])==row['sha256']
    plan=read(d/'functional-plan.json')
    assert completion['plan_sha256']==sha(d/'functional-plan.json')
    for row in plan['files']:assert sha(P/row['path'])==row['sha256']
    status=read(d/'execution-status.json');assert status['actual_exit_code']==status['verifier_actual_exit_code']==0
    cases=read(d/'remaining67-input-only.json')['cases'];before=read(d/'baseline-saved67.json')['cases'];after=read(P/'reports/final-live-remaining67-batch54.json')['cases']
    summary=read(P/'reports/final-live-remaining67-summary-batch54.json')
    assert len(cases)==len(before)==len(after)==67
    complete=failed=helper=plans=oldsum=newsum=0;work=Counter();comparisons=[]
    for data,b,a in zip(cases,before,after):
        assert data['name']==b['name']==a['name'];w=a['whole'];h=a['helper']
        assert 0<=h['work']<=16000000
        for role in ('whole','helper'):
            result=a[role]
            if result['valid']:
                T,peak=simulate(data,result['plan']);assert T==result['T'] and peak==result['peak'];plans+=1
            else:assert result['plan'] is None
        if w['valid']:complete+=1
        else:
            failed+=1;assert not w['returned'] and w['error']==b['whole']['error'] and w['T']==w['peak']==0
        helper+=h['valid'];assert w['valid']==b['whole']['valid'] and h['valid']==b['helper']['valid']
        assert w['plan']==b['whole']['plan'] and (w['T'],w['peak'])==(b['whole']['T'],b['whole']['peak'])
        old=b['helper']['work'];new=h['work'];oldsum+=old;newsum+=new
        direction='increased' if new>old else 'decreased' if new<old else 'equal';work[direction]+=1
        comparisons.append(dict(name=a['name'],whole_valid=w['valid'],helper_valid=h['valid'],old_work=old,new_work=new,helper_exhausted=h['exhausted']))
    assert (complete,failed,helper,plans,oldsum,newsum)==(4,63,4,8,636931404,637093426)
    assert dict(work)==dict(increased=16,decreased=11,equal=40)
    assert summary['restored']==summary['lost']==summary['common_quality_changes']==[]
    assert summary['logical_work']['before_sum']==oldsum and summary['logical_work']['after_sum']==newsum
    assert sum(a['helper']['exhausted'] for a in after)==sum(b['helper']['exhausted'] for b in before)==35
    result=dict(passed=True,reviewed_unix=time.time(),completion_sha256=sha(d/'completion.json'),raw_report_sha256=sha(P/'reports/final-live-remaining67-batch54.json'),
        negative_checkpoint_sha256=sha(d/'negative-checkpoint.json'),negative_frozen_files=len(negative['files']),
        actual_session=29846,actual_exit_code=0,original_inputs=67,known_feasible_remaining=63,recovery_controls=4,
        before_whole_success=4,after_whole_success=4,helper_success=4,new_whole_recoveries=0,new_helper_recoveries=0,lost=0,
        independently_replayed_actual_whole_and_helper_plans=8,all_common_whole_plans_identical=True,
        before_logical_work=oldsum,after_logical_work=newsum,logical_work_delta=newsum-oldsum,logical_work_cases=dict(work),helper_exhausted=35,
        scope='All67 original source-only cases terminal and all8 actual complete helper/whole plans independently heap-replayed. Remaining63 still fail,4controls identical T/peak/fullplan; all original failures/errors/nullplans retained. Logical work total increases162022 with16increases/11decreases/40same; no matched CPU measurement. Freeze negative result and stop this single filter direction; actualdefaultR51 unchanged, no full250/regression/performance promotion.')
    (ROOT/'outputs/stage2-root-remaining-r54.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
