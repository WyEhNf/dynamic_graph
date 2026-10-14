"""Literal original-DAG plans only. Never calls a solver or uses saved witnesses."""
from pathlib import Path
import json,hashlib
MAX=(1<<63)-1
nodes=[dict(id=0,core_type='AIC',core_num=1,exec_time=1,workspace_memory=0,output_memory=30,inputs=[]),
       dict(id=1,core_type='AIC',core_num=1,exec_time=1,workspace_memory=0,output_memory=50,inputs=[]),
       dict(id=2,core_type='AIC',core_num=1,exec_time=1,workspace_memory=50,output_memory=0,inputs=[1]),
       dict(id=3,core_type='AIC',core_num=1,exec_time=1,workspace_memory=0,output_memory=0,inputs=[0,2])]
specs=[('premature-P',100,nodes,[0,1,2,3],False),('delay-P',100,nodes,[1,2,0,3],True),
       ('wide-original-order',130,nodes,[0,1,2,3],True),('narrow-fixed-plan-only',99,nodes,[1,2,0,3],False)]
equal=json.loads(json.dumps(nodes));equal[1]['output_memory']=40;equal[2]['workspace_memory']=30
specs.append(('equal-not-strict',100,equal,[0,1,2,3],True))
zero=json.loads(json.dumps(nodes));zero[0]['output_memory']=0
specs.append(('zero-producer-ineligible',100,zero,[0,1,2,3],True))
huge=json.loads(json.dumps(nodes));huge[0]['output_memory']=MAX//4;huge[1]['output_memory']=MAX//2;huge[2]['workspace_memory']=MAX-MAX//2
specs.extend([('MAX-delay-P',MAX,huge,[1,2,0,3],True),('MAX-premature-P',MAX,huge,[0,1,2,3],False)])
sink=json.loads(json.dumps(nodes));sink[3]['inputs']=[2]
specs.extend([('sink-original-block',100,sink,[0,1,2,3],False),('sink-last-is-legal-not-eligible-top24',100,sink,[1,2,3,0],True)])
shared=json.loads(json.dumps(nodes));shared.append(dict(id=4,core_type='AIV',core_num=1,exec_time=1,workspace_memory=0,output_memory=0,inputs=[1,2]))
specs.extend([('external-Q-user-original-block',100,shared,[0,1,2,4,3],False),('external-Q-user-legal',100,shared,[1,2,4,0,3],True)])
rows=[]
for name,cap,vs,order,expected in specs:
    by={v['id']:v for v in vs};users={i:set() for i in by}
    for v in vs:
        for p in v['inputs']:users[p].add(v['id'])
    D=set();held=set();live=0;peak=0;elapsed=0;trace=[];valid=True
    for i in order:
        v=by[i];assert i not in D and set(v['inputs'])<=D
        begin=live+v['workspace_memory']+v['output_memory']
        trace.append(dict(phase='BEGIN',id=i,time=elapsed,live=live,workspace=v['workspace_memory'],output=v['output_memory'],memory=begin,held=sorted(held),fits=begin<=cap))
        if begin>cap:valid=False;break
        peak=max(peak,begin);held.add(i);D.add(i);elapsed+=v['exec_time']
        held={p for p in held if not users[p] or users[p]-D};live=sum(by[p]['output_memory'] for p in held)
        trace.append(dict(phase='END',id=i,time=elapsed,live=live,held=sorted(held)))
    assert valid==expected
    rows.append(dict(name=name,hardware=dict(aic_core_num=1,aiv_core_num=1,stream_num=1,memory_limit=cap,event_record_time=0,event_wait_time=0),
                     nodes=vs,deadline_us=len(vs),fixed_plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])]),
                     expected_valid=expected,T=elapsed if valid else None,peak=peak if valid else None,trace=trace,
                     claim='Literal fixed-plan physical control; no whole-default outcome or arbitrary infeasibility claim.'))
p=Path('research/batch56/causal-deferral-manual-original.json');p.write_text(json.dumps(dict(status='STATIC_LITERAL_WHOLE_ORIGINAL_PLANS',cases=rows),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(cases=len(rows),legal=sum(r['expected_valid'] for r in rows),invalid=sum(not r['expected_valid'] for r in rows),sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
