"""Root saved12 equality, original physical states and full plan simulation."""
import hashlib,json
from pathlib import Path
from review_stage2_release_cut_gold_r51 import simulate
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56';G=Path('G:/Hackathon-project27-owned/batch56-observer-c1ea2391')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    complete=read(D/'observer-completion-freeze.json');assert sha(D/'observer-completion-freeze.json')=='f58a06730dfbf4696f2f32cf087acffa338c4e3391990ccaec815f546aacd01c'
    assert complete['owner_pid']==137004 and complete['status']=='ACTUAL_TERMINAL_EXIT0_ORIGINAL12_NO_PROMOTION'
    for f in complete['files']:
        p=Path(f['path']);p=p if p.is_absolute() else P/p;assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes']
    assert len(complete['statuses'])==3 and all(r['actual_exit_code']==0 for r in complete['statuses'])
    assert len(complete['preflights'])==4 and all(r['passed'] and all(r['checks'].values()) for r in complete['preflights'])
    before={c['name']:c for c in read('G:/Hackathon-project27-owned/batch56-selected12-79cecf/outputs/selected12.json')['cases']}
    cases={c['name']:c for c in read(P/'research/batch52/observer-selected12-input-only.json')['cases']};actual=read(G/'outputs/observer12.json');inv=read(D/'observer-return-inventory.json')
    assert len(actual['cases'])==actual['count']==12 and {c['name'] for c in actual['cases']}==set(before)==set(cases)
    plans=states=prefixrows=scopes=0;details=[];guarded=entries=0
    for row in actual['cases']:
        core={k:v for k,v in row.items() if k not in ['helper_observer','whole_observer']};assert core==before[row['name']]
        c=cases[row['name']];by={n['id']:n for n in c['nodes']};users={i:set() for i in by};cap=c['hardware']['memory_limit']
        for i,n in by.items():
            for j in n['inputs']:users[j].add(i)
        def reach(i,reverse=False):
            seen=set();todo=list(by[i]['inputs'] if reverse else users[i])
            while todo:
                j=todo.pop()
                if j not in seen:seen.add(j);todo.extend(by[j]['inputs'] if reverse else users[j])
            return seen
        ancestor={i:reach(i,True) for i in by};descendant={i:reach(i)|{i} for i in by}
        def violations(done):
            out=[]
            for j in by.keys()-done:
                pinned=[i for i in done|ancestor[j] if i!=j and (not users[i] or users[i]&descendant[j])]
                bound=sum(by[i]['output_memory'] for i in pinned)+by[j]['workspace_memory']+by[j]['output_memory']
                if bound>cap:out.append(dict(target_id=j,bound=bound,cap=cap,pinned_ids=sorted(pinned)))
            return sorted(out,key=lambda x:(x['target_id'],x['bound']))
        for scope in ['helper','whole']:
            result=row[scope]
            if result['valid']:
                T,peak=simulate(c,result['plan']);assert (T,peak)==(result['T'],result['peak']) and T<=c['deadline_us'] and peak<=cap;plans+=1
            o=row[scope+'_observer'];scopes+=1
            assert not o['counter_overflow'] and not o['state_shape_error'] and o['metadata_dropped']==o['states_dropped']==0
            assert len(o['metadata'])<=16 and len(o['states'])<=2 and o['metadata_seen']==len(o['metadata']) and o['states_seen']==len(o['states'])
            assert [s['label'] for s in o['stage_counts']]==inv['stage_labels']
            counter={s['label']:s['count'] for s in o['stage_counts']};entry=counter['restart-before-entry-charge'];dispatch=counter['restart-status-dispatch-paid-before-guard'];entries+=entry;guarded+=dispatch
            assert entry<=1 and dispatch<=entry
            pairs=[m for m in o['metadata'] if inv['stage_labels'][m['stage']]=='restart-detector-return-before-status-charge']
            pair=pairs[0] if pairs else None;savedstates=[]
            for state in o['states']:
                assert state['original_ids']==[n['id'] for n in c['nodes']] and state['n']==len(by)
                done=set();live=0;peak=0
                for i in state['prefix_ids']:
                    assert i in by and i not in done and set(by[i]['inputs'])<=done
                    assert live+by[i]['workspace_memory']+by[i]['output_memory']<=cap
                    peak=max(peak,live+by[i]['workspace_memory']+by[i]['output_memory']);live+=by[i]['output_memory'];done.add(i)
                    for p in by[i]['inputs']:
                        if not(users[p]-done):live-=by[p]['output_memory']
                    prefixrows+=1
                ids=state['original_ids'];assert state['done']==[int(i in done) for i in ids] and state['live']==live
                assert state['users']==[len(users[i]-done) for i in ids]
                assert state['degree']==[len(set(by[i]['inputs'])-done) for i in ids]
                held=sorted([i for i in done if users[i]-done and by[i]['output_memory']],key=lambda i:(-by[i]['output_memory'],i))[:24]
                if state['held_provided']:assert state['held_ids']==held
                else:assert not state['held_ids']
                ready=[i for i in by.keys()-done if set(by[i]['inputs'])<=done]
                fits=[i for i in ready if live+by[i]['workspace_memory']+by[i]['output_memory']<=cap]
                label=inv['stage_labels'][state['stage']];guardfits=fits
                if 'release_cut_order_guarded' in label:
                    assert pair is not None and dispatch==1 and pair['producer_id'] in by and pair['target_id'] in by
                    guardfits=[i for i in fits if i!=pair['producer_id'] or pair['target_id'] in done]
                    if ':return-19:' in label:assert not guardfits # Distinguishes actual no-fit from apply failure.
                if 'release_cut_order:return-16:' in label:assert not fits
                savedstates.append(dict(stage=label,prefix_length=len(done),live=live,ready_count=len(ready),memory_fit_ids=sorted(fits),guard_policy_fit_ids=sorted(guardfits),forced_overlap_violations=violations(done)))
                states+=1
            cutreturns=[s for s in o['stage_counts'] if s['count'] and s['label'].startswith('release_cut_order:return')]
            details.append(dict(name=row['name'],scope=scope,entry=entry,guard_dispatch=dispatch,pair=pair,cut_returns=cutreturns,states=savedstates))
    assert plans==8 and scopes==24 and entries==16 and guarded==8
    result=dict(passed=True,actual_terminal_exit_code=0,actual_owner_session=73424,actual_owner_PID=137004,completion_sha256=sha(D/'observer-completion-freeze.json'),actual_original_inputs=12,all_nonobserver_fields_identical=True,independent_complete_plan_replays=plans,scopes=scopes,physical_states_replayed=states,prefix_original_operations_replayed=prefixrows,restart_entry_scopes=entries,guard_dispatch_scopes=guarded,metadata_drops=0,state_drops=0,details=details,scope='Every saved original-DAG state independently reconstructed from original direct consumers/workspace/output/sink retention; all8 complete plans independently simulated. Observation leaves all outcomes/fees/plans unchanged. Guard return19 has zero eligible memory-fitting original nodes, so this actual return is no-fit. No recovery/performance/default/63 improvement claim.')
    (ROOT/'outputs/stage2-root-causal-observer-actual-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='details'}))
if __name__=='__main__':main()
