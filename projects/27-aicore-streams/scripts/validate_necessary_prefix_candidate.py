"""Independent bigint serial feasibility oracle for bounded candidate controls."""
import itertools
import json
from pathlib import Path
import random
import subprocess
import hashlib

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/Hackathon-stage2-artifacts/project27/r57-necessary-prefix')


def replay(nodes, order, limit):
    by_id={n['id']:n for n in nodes};users={i:0 for i in by_id}
    for n in nodes:
        for p in n['inputs']:users[p]+=1
    done=set();live=peak=0
    for i in order:
        n=by_id[i]
        if i in done or not set(n['inputs'])<=done:return None
        allocation=live+n['workspace_memory']+n['output_memory']
        if allocation>limit:return None
        peak=max(peak,allocation);live+=n['output_memory'];done.add(i)
        for p in n['inputs']:
            users[p]-=1
            if not users[p]:live-=by_id[p]['output_memory']
    return peak if len(done)==len(nodes) else None


def main():
    rng=random.Random(20261012);cases=[];gold=[]
    for index in range(96):
        count=rng.randint(2,7);ids=rng.sample(range(1,10000),count)
        nodes=[{'id':ids[i],'core_type':'AIC','core_num':1,'exec_time':1,
            'workspace_memory':rng.randrange(9),'output_memory':rng.randrange(7),
            'inputs':[ids[j] for j in range(i) if rng.random()<.32]} for i in range(count)]
        cap=rng.randrange(4,26)
        feasible=any(replay(nodes,order,cap) is not None for order in itertools.permutations(ids))
        rng.shuffle(nodes)
        cases.append({'name':f'random{index}','hardware':{'aic_core_num':1,'aiv_core_num':1,'stream_num':1,
            'memory_limit':cap,'event_record_time':0,'event_wait_time':0},'nodes':nodes,'deadline_us':1000})
        gold.append(feasible)
    # Near INT64_MAX, check subtraction arithmetic and sink retention.
    for suffix,cap in [('fits',(1<<63)-1),('over',(1<<63)-2)]:
        nodes=[{'id':1,'core_type':'AIC','core_num':1,'exec_time':1,'workspace_memory':0,'output_memory':(1<<63)-2,'inputs':[]},
            {'id':2,'core_type':'AIC','core_num':1,'exec_time':1,'workspace_memory':1,'output_memory':0,'inputs':[1]}]
        cases.append({'name':suffix,'hardware':{'aic_core_num':1,'aiv_core_num':1,'stream_num':1,'memory_limit':cap,
            'event_record_time':0,'event_wait_time':0},'nodes':nodes,'deadline_us':1000});gold.append(suffix=='fits')
    source=OUT/'controls-input.json';source.write_text(json.dumps({'cases':cases},indent=2))
    output=OUT/'controls-output.json'
    p=subprocess.run([str(OUT/'selected-driver.exe'),str(source),str(output),'helper-only'],capture_output=True,text=True,check=True)
    results=json.loads(output.read_text())['cases']
    assert len(results)==len(cases)==98
    positives=0
    for c,r,expected in zip(cases,results,gold):
        order=r['helper']['order_ids'];actual=replay(c['nodes'],order,c['hardware']['memory_limit'])
        assert r['helper']['valid']==expected,(c['name'],expected,r)
        assert not r['helper']['exhausted']
        if expected:assert actual is not None;positives+=1
        else:assert not order
        assert r['helper']['work']<=2000000
    report={'passed':True,'controls':98,'feasible_controls':positives,'integer_model':'Python bigint',
        'oracle':'all ID permutations, original DIRECT edges and original BEGIN lifetime',
        'scope':'serial small controls only; selected12 failures remain unknown',
        'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,output,Path(__file__)]}}
    (OUT/'controls-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
