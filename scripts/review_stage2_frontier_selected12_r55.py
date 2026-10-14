"""Independently review source-only original12 outcomes and full-plan physics."""
import json,time
from collections import Counter
from review_stage2_observer_r52 import ROOT,P,sha,simulate

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
    d=P/'research/batch55';m=read(d/'selected12-completion.json')
    assert sha(d/'selected12-completion.json')=='6c1eb29f34a0509488aa75fc39c2733f244417103fea863a03899166b48ff2fb'
    assert m['actual_exit_code']==0 and not m['default_changed']
    for row in m['files']:assert sha(P/row['path'])==row['sha256']
    assert sha(d/'solution.cpp')==m['source_sha256']and sha(d/'selected12-gcc.exe')==m['exe_sha256']
    cases=read(P/'research/batch52/observer-selected12-input-only.json')['cases']; before=read(P/'reports/observer-baseline-batch52.json')['cases']; after=read(P/'reports/cut-repair-selected12-batch55.json')['cases']
    assert len(cases)==len(before)==len(after)==12;plans=success=oldsum=newsum=0;direction=Counter()
    for data,b,a in zip(cases,before,after):
        assert data['name']==b['name']==a['name']
        for role in ['helper','whole']:
            old=b[role];new=a[role];assert new['valid']==old['valid']
            if new['valid']:
                T,peak=simulate(data,new['plan']);assert T==new['T']==old['T'] and peak==new['peak']==old['peak'];plans+=1
                assert new['plan']==old['plan']
            else:assert new['plan']is None
        success+=a['whole']['valid'];assert 0<=a['helper']['work']<=16000000
        if not a['whole']['valid']:assert not a['whole']['returned']and a['whole']['error']==b['whole']['error']
        old=b['helper']['work'];new=a['helper']['work'];oldsum+=old;newsum+=new;direction['increase'if new>old else 'decrease'if new<old else 'equal']+=1
    assert (plans,success,oldsum,newsum)==(8,4,54717560,60829525)
    assert sum(a['helper']['exhausted']for a in after)==sum(b['helper']['exhausted']for b in before)==2
    result=dict(passed=True,reviewed_unix=time.time(),completion_sha256=sha(d/'selected12-completion.json'),actual_exit_code=0,original_inputs=12,whole_before_success=4,whole_after_success=4,remaining_failed=8,new_recoveries=0,lost=0,independent_actual_full_plan_replays=8,common_complete_plans_identical=True,before_logical_work=oldsum,after_logical_work=newsum,logical_work_delta=newsum-oldsum,logical_work_cases=dict(direction),before_exhausted=2,after_exhausted=2,scope='Alloriginal12 outcomes retained and all8 actual helper/whole plans independently heap-replayed. R55 branch repair proves smallcontrols but recoversnone of original8failed;common4 completeplans/T/peak identical. Logicalwork+6111965(11.17%) with no CPUmeasurement. Keep isolatednegative/defaultR51; no63/67/full/performance promotion. Next static attribution must explain missing real recovery before any expansion.')
    (ROOT/'outputs/stage2-root-frontier-selected12-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
