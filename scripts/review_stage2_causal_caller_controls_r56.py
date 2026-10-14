"""Independent small original-DAG fee and physical audit before candidate execution."""
import hashlib,json
from pathlib import Path
from review_stage2_causal_reference_gold_r56 import model,physics
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def graph(nodes):
    ix={v['id']:i for i,v in enumerate(nodes)}
    ins=[[ix[p] for p in v['inputs']] for v in nodes];out=[[] for _ in nodes]
    for i,ps in enumerate(ins):
        for p in ps:out[p].append(i)
    deg=list(map(len,ins));topo=[i for i in range(len(nodes)) if not deg[i]]
    for i in topo:
        for c in out[i]:
            deg[c]-=1
            if not deg[c]:topo.append(c)
    return ix,ins,out,topo
def basic_whole(f):
    nodes=f['nodes'];ix,ins,out,topo=graph(nodes);done=set();users=list(map(len,out));degree=list(map(len,ins))
    live=0;events=[('initialize',3*len(nodes))];order=[]
    while len(done)<len(nodes):
        ready=[];safe=[];held=[]
        for i,v in enumerate(nodes):
            events.append(('visit',1))
            if i in done:
                if users[i] and v['output_memory']:held.append(i)
                continue
            events.append(('guard',2))
            if i==0 and 2 not in done:continue
            if degree[i] or live+v['workspace_memory']+v['output_memory']>f['hardware']['memory_limit']:continue
            events.extend(('impact',1) for _ in ins[i])
            freed=sum(nodes[p]['output_memory'] for p in ins[i] if users[p]==1)
            net=v['output_memory']-freed
            ready.append(((net,v['workspace_memory']+v['output_memory'],v['id']),i))
            if net<=0:safe.append(i)
        if safe:i=min(safe,key=lambda i:nodes[i]['id'])
        else:
            # This independently reviewed fixture never needs a held cut/sort.
            assert not held
            i=min(ready)[1]
        events.extend([('apply_original',1+len(ins[i])+len(out[i])),('apply_guard',2)])
        order.append(nodes[i]['id']);done.add(i);live+=nodes[i]['output_memory']
        for p in ins[i]:
            users[p]-=1
            if not users[p]:live-=nodes[p]['output_memory']
        for c in out[i]:degree[c]-=1
    return events,order
def shared_probe(f,limit):
    nodes=f['nodes'];ix,ins,out,topo=graph(nodes);done={ix[p] for p in f['prefix']};users=[len(set(x)-done) for x in out];degree=[len(set(x)-done) for x in ins]
    live=sum(nodes[p]['output_memory'] for p in done if not out[p] or set(out[p])-done)
    initial=live;peak=live;work=0;order=[];events=[]
    class Stop(Exception):pass
    def pay(op,n):
        nonlocal work
        okay=n<=limit-work;events.append(dict(operation=op,amount=n,work_before=work,paid=okay))
        work=work+n if okay else limit
        if not okay:raise Stop
    try:
        pay('entry',1);pay('copy',4*len(nodes));stack=[];included=set()
        for c in out[ix[f['producer']]]:
            pay('direct_user',1)
            if c not in done:stack.append(c)
        while stack:
            i=stack.pop();pay('closure_pop',1)
            if i in done or i in included:continue
            included.add(i)
            for p in ins[i]:
                pay('closure_parent',1)
                if p not in done:stack.append(p)
        pending=[]
        for i in topo:
            pay('topo_visit',1)
            if i in included:pending.append(i)
        while len(order)<len(pending):
            ready=[]
            for i in pending:
                pay('pending_visit',1)
                if i in done or degree[i]:continue
                pay('guard',2)
                if nodes[i]['id']==f['delayed'] and ix[f['target']] not in done:continue
                v=nodes[i]
                if live+v['workspace_memory']+v['output_memory']>f['hardware']['memory_limit']:continue
                freed=0
                for p in ins[i]:
                    pay('impact_parent',1)
                    if users[p]==1:freed+=nodes[p]['output_memory']
                ready.append(((v['output_memory']-freed,v['workspace_memory']+v['output_memory'],v['id']),i))
            i=min(ready)[1];v=nodes[i];peak=max(peak,live+v['workspace_memory']+v['output_memory']);live+=v['output_memory'];done.add(i);order.append(v['id'])
            for p in ins[i]:
                pay('apply_parent',1);users[p]-=1
                if not users[p]:live-=nodes[p]['output_memory']
            for c in out[i]:pay('apply_original_successor',1);degree[c]-=1
        assert users[ix[f['producer']]]==0
        return dict(valid=True,exhausted=False,work=work,order=order,peak=peak,final_live=live),events
    except Stop:return dict(valid=False,exhausted=True,work=work,order=order,peak=peak,final_live=initial),events
def main():
    freeze=read(D/'compiler-controls-plan-freeze.json')
    for r in freeze['files']:
        p=Path(r['path']);p=p if p.is_absolute() else P/p
        assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
    controls=read(D/'caller-guard-controls16.json');hand=read(D/'caller-guard-hand-fees.json')
    basic=controls['fixtures']['basic'];events,order=basic_whole(basic)
    assert order==[1,2,0,3] and sum(n for _,n in events)==69
    detector,pair,_=model(basic['nodes'],basic['prefix'],100)
    assert pair==(0,2,0) and sum(n for _,n in detector)==127
    total=3+127+2+2+69+4;assert total==207
    for name,f in controls['fixtures'].items():
        p=physics(f['nodes'],f['fixed_order'],100,True)
        assert p['valid'] and (p['T'],p['peak'])==(f['fixed_T'],f['fixed_peak'])
    records=[]
    for c in controls['cases']:
        if c['routine']=='restart':
            needed=c['initial_work']+total;valid=c['limit']>=needed
            e=dict(valid=valid,exhausted=not valid,work=min(needed,c['limit']),order=order if valid else [])
            if valid:e.update(T=4,peak=100)
        else:e,trace=shared_probe(controls['fixtures']['shared-external'],c['limit'])
        assert c['expected']==e,c['name'];records.append(dict(name=c['name'],derived=e))
    probe,trace=shared_probe(controls['fixtures']['shared-external'],1000)
    assert probe==dict(valid=True,exhausted=False,work=67,order=[1,2,0],peak=100,final_live=30)
    for k in ('basic_guarded_whole','basic_restart','shared_external_guarded_probe'):
        stages=hand[k]['stages'];running=0
        for _,fee,cum in stages:running+=fee;assert running==cum
        assert running==hand[k]['total']
    assert [hand[k]['total'] for k in ('basic_guarded_whole','basic_restart','shared_external_guarded_probe')]==[69,207,67]
    doc=dict(passed=True,scope='static independent original-DAG model; no candidate/compiler invocation',frozen_files=len(freeze['files']),caller_controls=16,guard_work=69,restart_work=207,initial_shared7_total=214,shared_external_probe_work=67,records=records,basic_events=events,probe_events=trace,controls_sha256=sha(D/'caller-guard-controls16.json'),source_sha256=sha(D/'solution.cpp'),freeze_sha256=sha(D/'compiler-controls-plan-freeze.json'),compiler_gate_not_executed=True)
    target=ROOT/'outputs/stage2-root-causal-caller-controls-r56.json';target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in doc.items() if k not in ('records','basic_events','probe_events')}))
if __name__=='__main__':main()
