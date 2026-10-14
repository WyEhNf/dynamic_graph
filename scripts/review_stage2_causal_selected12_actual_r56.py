"""Original twelve quality evidence, independent heap full-plan replay."""
import hashlib,json
from collections import Counter
from pathlib import Path
from review_stage2_release_cut_gold_r51 import simulate
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56';G=Path('G:/Hackathon-project27-owned/batch56-selected12-79cecf')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    frozen=read(D/'selected12-completion-freeze.json');assert sha(D/'selected12-completion-freeze.json')=='03bd41c183530df2b447df66c1f02e724c9f0a214e6d958835174f869abae8c7'
    assert frozen['status']=='ACTUAL_TERMINAL_EXIT0_ORIGINAL12_NO_PROMOTION'
    for manifest in [frozen,read(D/'selected12-plan-freeze.json')]:
        for f in manifest['files']:
            p=Path(f['path']);p=p if p.is_absolute() else P/p;assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes']
    assert len(frozen['statuses'])==2 and all(r['actual_exit_code']==0 for r in frozen['statuses'])
    for r in frozen['preflights']:
        assert r['passed'] and all(r['checks'].values());assert sha(P/r['raw_path'])==r['raw_sha256']
    data=read(G/'outputs/selected12.json');cases={c['name']:c for c in read(P/'research/batch52/observer-selected12-input-only.json')['cases']};before={c['name']:c for c in read(P/'reports/observer-baseline-batch52.json')['cases']}
    assert data['count']==len(data['cases'])==len(cases)==12 and {c['name'] for c in data['cases']}==set(cases)
    totals=Counter();plans=0;changed=[];all_common_equal=True
    for c in data['cases']:
        original=cases[c['name']];old=before[c['name']]
        for stage in ('helper','whole'):
            a=c[stage];b=old[stage]
            totals[stage+'_success']+=a['valid'];totals[stage+'_recovered']+=a['valid'] and not b['valid'];totals[stage+'_lost']+=b['valid'] and not a['valid']
            if a['valid']:
                T,peak=simulate(original,a['plan']);assert (T,peak)==(a['T'],a['peak']) and T<=original['deadline_us'] and peak<=original['hardware']['memory_limit'];plans+=1
                if b['valid']:
                    assert (T,peak)==(b['T'],b['peak']);all_common_equal &= a['plan']==b['plan']
            else:
                assert a['plan'] is None
                if stage=='whole':assert not a['returned'] and a['error']==b['error']
        h=c['helper'];assert 0<=h['work']<=16000000;totals['new_work']+=h['work'];totals['old_work']+=old['helper']['work'];totals['new_exhausted']+=h['exhausted'];totals['old_exhausted']+=old['helper']['exhausted']
        changed.append(dict(name=c['name'],new_valid=c['whole']['valid'],work_delta=h['work']-old['helper']['work'],error=c['whole']['error']))
    assert plans==8 and totals['helper_success']==totals['whole_success']==4 and totals['new_work']==55988059 and totals['old_work']==54717560
    assert not any(totals[k] for k in ['helper_recovered','whole_recovered','helper_lost','whole_lost']) and totals['new_exhausted']==totals['old_exhausted']==2
    doc=dict(passed=True,actual_terminal_exit_code=0,actual_owner_PID=frozen['owner_pid'],actual_tool_chunk='c7e2fe',original_inputs=12,whole_before_success=4,whole_after_success=4,remaining_failed=8,new_recoveries=0,lost=0,independent_actual_full_plan_replays=plans,common_complete_plans_identical=all_common_equal,before_logical_work=totals['old_work'],after_logical_work=totals['new_work'],logical_work_delta=1270499,logical_work_increase_percent=1270499/54717560*100,exhausted_before_after=[2,2],records=changed,completion_freeze_sha256=sha(D/'selected12-completion-freeze.json'),source_sha256=frozen['source_sha256'],scope='Actual original12 negative: all8 failed retained; eight complete helper/whole plans independently heap-replayed. Single causal deferral did not recover real cases and adds2.32% chargedwork; no CPU speed or63/full/default promotion claim. Freeze and diagnose this negative before further expansion.')
    (ROOT/'outputs/stage2-root-causal-selected12-actual-r56.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in doc.items() if k!='records'}))
if __name__=='__main__':main()
