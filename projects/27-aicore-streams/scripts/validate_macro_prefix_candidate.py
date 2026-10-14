"""Independent Python-bigint subset DP and original DIRECT lifetime controls."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time


def replay(nodes,order,cap):
    by={n['id']:n for n in nodes};done=set();users={i:0 for i in by};live=peak=0
    for n in nodes:
        for p in n['inputs']:users[p]+=1
    for i in order:
        if i not in by or i in done or not set(by[i]['inputs'])<=done:return None
        n=by[i];allocation=live+n['workspace_memory']+n['output_memory']
        if allocation>cap:return None
        peak=max(peak,allocation);live+=n['output_memory'];done.add(i)
        for p in n['inputs']:
            users[p]-=1
            if not users[p]:live-=by[p]['output_memory']
    return peak if len(done)==len(nodes) else None


def exact_peak(nodes):
    count=len(nodes);index={n['id']:i for i,n in enumerate(nodes)}
    parents=[sum(1<<index[p] for p in n['inputs']) for n in nodes];users=[0]*count
    for i,ps in enumerate(parents):
        for p in range(count):
            if ps>>p&1:users[p]|=1<<i
    best={0:0}
    for mask in range(1<<count):
        if mask not in best:continue
        live=sum(n['output_memory'] for i,n in enumerate(nodes) if mask>>i&1 and (not users[i] or users[i]&~mask))
        for i,n in enumerate(nodes):
            if mask>>i&1 or parents[i]&~mask:continue
            new=mask|1<<i;peak=max(best[mask],live+n['workspace_memory']+n['output_memory'])
            if new not in best or peak<best[new]:best[new]=peak
    return best[(1<<count)-1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(20261013);cases=[];gold=[]
    for q in range(400):
        n=rng.randrange(3,11);ids=rng.sample(range(1,2147483000),n)
        nodes=[{'id':ids[i],'core_type':'AIC','core_num':1,'exec_time':1,'workspace_memory':rng.randrange(30),
                'output_memory':rng.randrange(13),'inputs':[ids[j] for j in range(i) if rng.random()<.37]} for i in range(n)]
        peak=exact_peak(nodes);cap=max(0,peak+rng.randrange(-3,5));rng.shuffle(nodes)
        cases.append({'name':f'dp{q}','hardware':{'aic_core_num':1,'aiv_core_num':1,'stream_num':1,'memory_limit':cap,'event_record_time':0,'event_wait_time':0},'nodes':nodes,'deadline_us':1000});gold.append(peak)
    # W+O allocation and retained sink outputs near INT64_MAX.
    for q in range(20):
        nodes=[{'id':10+i*7,'core_type':'AIC','core_num':1,'exec_time':1,'workspace_memory':0,
                'output_memory':0,'inputs':[]} for i in range(5)]
        nodes[0]['output_memory']=(1<<63)-10
        nodes[1].update(inputs=[10],workspace_memory=5,output_memory=2)
        nodes[2].update(inputs=[10],workspace_memory=4,output_memory=1)
        nodes[3].update(inputs=[17,24],workspace_memory=7,output_memory=3)
        nodes[4].update(inputs=[31],workspace_memory=6,output_memory=2)
        cap=(1<<63)-1-q;peak=exact_peak(nodes)
        cases.append({'name':f'int64-{q}','hardware':{'aic_core_num':1,'aiv_core_num':1,'stream_num':1,'memory_limit':cap,'event_record_time':0,'event_wait_time':0},'nodes':nodes,'deadline_us':1000});gold.append(peak)
    src=a.out/'controls-input.json';dst=a.out/'controls-output.json';src.write_text(json.dumps({'cases':cases}));started=time.perf_counter()
    process=subprocess.run([str(a.exe),str(src),str(dst),'helper-only'],capture_output=True,text=True,check=True)
    records=json.loads(dst.read_text())['cases'];assert len(records)==len(cases)
    returned=feasible=0
    for case,row,peak in zip(cases,records,gold):
        assert case['name']==row['name'];h=row['helper'];cap=case['hardware']['memory_limit'];feasible+=peak<=cap
        if h['valid']:
            actual=replay(case['nodes'],h['order_ids'],cap);assert actual is not None and actual==h['peak'];assert peak<=cap;returned+=1
        else:assert not h['order_ids']
        assert 0<=h['work']<=128000000
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'passed':True,'controls':len(cases),'exact_serial_feasible':feasible,'candidate_returned':returned,
            'unknown_feasible':feasible-returned,'oracle':'independent Python arbitrary precision exact subset DP, original direct-user release',
            'no_completeness_claim':True,'elapsed_seconds':time.perf_counter()-started,
            'sha256':{str(p):sha(p) for p in [a.exe,src,dst,Path(__file__)]}}
    (a.out/'controls-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
