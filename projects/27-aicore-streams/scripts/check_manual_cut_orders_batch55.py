"""Independent bigint replay of explicitly hand-written R55 small DAG orders.

Not a solver, candidate implementation, or full default test. It verifies only
the supplied full orders and original BEGIN/last-DIRECT-consumer END physics.
"""
from pathlib import Path
import json,hashlib,copy
base=dict(name='cut-two-orders',hardware=dict(aic_core_num=1,aiv_core_num=1,stream_num=1,memory_limit=100,event_record_time=0,event_wait_time=0),deadline_us=5,nodes=[dict(id=i,core_type='AIC',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=ps) for i,w,o,ps in [(0,0,50,[]),(1,0,20,[0]),(2,20,30,[0]),(3,50,0,[1]),(4,0,0,[2])]])
cases=[]
def add(name,transform,order,valid):
    c=copy.deepcopy(base);c['name']=name;transform(c)
    cases.append(dict(case=c,original_completed_prefix=[0],cut_producer=0,original_complete_cut=[1,2],supplied_full_order=order,expected_valid=valid))
add('outside-user-obstruction-correct',lambda c:None,[0,2,1,4,3],True)
add('outside-user-obstruction-wrong',lambda c:None,[0,1,2,3,4],False)
def equal(c):
    c['hardware']['memory_limit']=110;c['nodes'][2]['workspace_memory']=40;c['nodes'][2]['output_memory']=20;c['nodes'][3]['workspace_memory']=60
add('equal-live-distinct-identity-correct',equal,[0,2,1,4,3],True)
add('equal-live-distinct-identity-wrong',equal,[0,1,2,3,4],False)
add('wide-capacity-original-cut-legal',lambda c:c['hardware'].update(memory_limit=130),[0,1,2,3,4],True)
add('one-below-minimum-peak',lambda c:c['hardware'].update(memory_limit=99),[0,2,1,4,3],False)
def sinks(c):c['nodes'][3]['output_memory']=1;c['nodes'][4]['output_memory']=1
add('two-sinks-retained',sinks,[0,2,1,4,3],True)
def external(c):
    c['deadline_us']=6;c['nodes'][3]['inputs']=[1,5];c['nodes'].append(dict(id=5,core_type='AIC',core_num=1,exec_time=1,workspace_memory=0,output_memory=0,inputs=[1]))
add('two-external-direct-users',external,[0,2,1,4,5,3],True)
def replay(c,order):
    by={n['id']:n for n in c['nodes']};out={i:set() for i in by}
    for n in by.values():
        for p in n['inputs']:out[p].add(n['id'])
    held={};done=set();peak=0;t=0;rows=[];valid=True;why=None
    assert len(order)==len(by) and set(order)==set(by)
    for i in order:
        n=by[i];assert set(n['inputs'])<=done
        L=sum(held.values());allocated=L+n['workspace_memory']+n['output_memory'];peak=max(peak,allocated)
        rows.append(dict(id=i,begin_time=t,live_before=L,workspace=n['workspace_memory'],new_output=n['output_memory'],compute_overlap=allocated))
        if allocated>c['hardware']['memory_limit']:
            valid=False;why='memory_limit';break
        t+=n['exec_time'];done.add(i);held[i]=n['output_memory'];released=[]
        for p in n['inputs']:
            if out[p]<=done:released.append(p);held.pop(p,None)
        rows[-1].update(end_time=t,released_original_direct_parent_outputs=released,live_after=sum(held.values()),held_output_ids=sorted(held))
    if valid and t>c['deadline_us']:valid=False;why='deadline'
    return dict(valid=valid,reason=why,complete=len(done)==len(by),T=t if len(done)==len(by) else None,peak=peak,rows=rows,terminal_held_sink_outputs=sum(held.values()) if len(done)==len(by) else None)
results=[]
for item in cases:
    r=replay(item['case'],item['supplied_full_order']);assert r['valid']==item['expected_valid'];results.append(dict(name=item['case']['name'],**r))
P=Path('research/batch55');P.mkdir(exist_ok=True)
(P/'manual-original-orders.json').write_text(json.dumps(dict(format='manual-full-original-dag-orders-only',controls=cases),indent=2)+'\n',encoding='utf-8')
doc=dict(status='STATIC_HAND_WRITTEN_WHOLE_PLAN_BIGINT_REPLAY',controls=len(results),passed=len(results),candidate_executed=False,whole_default_failure_claim=False,results=results,notes=['Each cut contains ALL remaining DIRECT users A/B of P. Outside users C/D are not removed or released early.','Equal-live variants hold 70 after P,A or P,B, but have different identities: A-side cannot compute B or C; B-side can compute A then D/C.','Capacity99 only supplied-plan-invalid here; no generic infeasibility claim or solver search.','These are full original plans, not reduced profiles or private test witness fed to production.'],sources=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in ('solution/solution.cpp',__file__,str(P/'manual-original-orders.json'))])
(P/'manual-original-physics.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=doc['status'],controls=len(results),passed=len(results),legal=sum(r['valid'] for r in results))))
