"""A complete original-DAG counterexample; no synthetic profile-only strings.

Independent BEGIN/END set liveness and Python bigint totals. The group is
identified solely from ALL original direct consumers; no witness enters solver.
"""
import hashlib,json
from pathlib import Path
from make_projection_gold_batch45 import reference
from make_group_gold_batch48 import groups,move

def replay(nodes,order):
    by={v['id']:v for v in nodes}; children={i:set() for i in by}
    for v in nodes:
        for p in v['inputs']:children[p].add(v['id'])
    done=set(); timeline=[];peak=0;time=0
    assert len(order)==len(by) and set(order)==set(by)
    for i in order:
        v=by[i];assert set(v['inputs'])<=done
        held={p for p in done if not children[p] or children[p]-done}
        before=sum(by[p]['output_memory'] for p in held)
        beginning=before+v['workspace_memory']+v['output_memory']
        peak=max(peak,beginning);time+=v['exec_time'];done.add(i)
        afterheld={p for p in done if not children[p] or children[p]-done}
        timeline.append(dict(id=i,start=time-v['exec_time'],end=time,held_before=sorted(held),live_before=before,begin_allocation=beginning,held_after=sorted(afterheld),live_after=sum(by[p]['output_memory'] for p in afterheld)))
    return dict(T=time,peak=peak,timeline=timeline)

def main():
    records=[(11,0,0,[]),(13,0,0,[]),(101,100,80,[11]),
        (103,1,0,[13]),(105,1,0,[13]),(201,101,0,[101,103]),
        (203,101,0,[101,105]),(207,5,100,[11,13]),
        (209,5,100,[11,13]),(211,101,0,[207,209]),
        (301,1,0,[203,211,207,209])]
    records += [(10001+i,1,0,[]) for i in range(10)]
    nodes=[dict(id=i,core_type='AIC' if q%2 else 'AIV',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=ps) for q,(i,w,o,ps) in enumerate(records)]
    hw=dict(aic_core_num=2,aiv_core_num=2,stream_num=2,memory_limit=301,event_record_time=0,event_wait_time=0)
    original=[201,207,209,211,203];profile=reference(nodes,301,original)
    assert set(profile['targets'])=={201,203,207,209,211}
    recognized=groups(nodes,profile['targets']);assert recognized==[dict(members=[201,203],weight='80')]
    assert profile['critical']==3 and int(profile['peak'])==381
    controls=[];results=[];grouprequests=[]
    for label,pivot in [('critical',3),('after-critical',4),('first-member',0)]:
        permutation=move(original,[201,203],pivot)
        gold=reference(nodes,301,permutation);full=replay(nodes,gold['order'])
        expected=301 if pivot==0 else 381
        assert full['peak']==expected and full['T']==21 and int(gold['peak'])==expected
        plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in gold['order']])])
        results.append(dict(label=label,pivot=pivot,permutation=permutation,full_schedule=full,fixed_plan=plan,original_capacity_feasible=full['peak']<=301))
        grouprequests.append(dict(permutation=original,members=[201,203],pivot=pivot,moved=permutation,gold=gold))
        for cap in (301,381):
            controls.append(dict(name=f'first_pivot_{label}_capacity{cap}',hardware=dict(hw,memory_limit=cap),nodes=nodes,deadline_us=21,fixed_plan=plan,gold_valid=expected<=cap,gold_T=str(full['T']),gold_peak=str(full['peak'])))
    Path('research/batch50').mkdir(exist_ok=True)
    files={'data/first-pivot-fixed-gold-batch50.json':dict(format='aicore-local-fixed-plan-bigint-v1',cases=controls),
           'data/first-pivot-group-gold-batch50.json':dict(format='aicore-local-group-gold-v1',cases=[dict(name='first_member_counterexample',hardware=hw,nodes=nodes,groups=recognized,requests=grouprequests)]),
           'research/batch50/first-pivot-counterexample.json':dict(hardware=hw,nodes=nodes,deadline_us=21,original_interface=original,group=recognized,original_profile=profile,results=results,explanation='P survives until B END; S1/S2 survive through C END until original DIRECT consumer F END. Non-target ancestors are scheduled from the full original DAG. All 21 tasks execute once, one stream, no events; BEGIN includes workspace plus output. Dummy roots retain median1 so interface threshold4; they are executed as real tasks.')}
    for f,data in files.items():Path(f).write_text(json.dumps(data,indent=2),encoding='utf-8')
    summary=dict(cases=6,T=21,capacity=301,critical_peak=381,after_critical_peak=381,first_member_peak=301,first_member_full_schedule_feasible=True,sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},reference='Independent prefix/future DIRECT-user sets, complete BEGIN/END original-DAG timeline; no C++ profile arithmetic reuse')
    Path('reports/first-pivot-gold-generation-batch50.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
