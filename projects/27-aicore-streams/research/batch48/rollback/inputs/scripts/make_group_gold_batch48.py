"""Independent direct-user recognition, stable block move and bigint profile.

Static preparation only until the coordinated CPU window is released.
No witness, dataset name or feasibility result selects the candidate algorithm.
"""
import hashlib,json,random
from pathlib import Path
from make_projection_gold_batch45 import reference,MAX

def groups(nodes,targets):
    index={v['id']:i for i,v in enumerate(nodes)}
    children={v['id']:[] for v in nodes}
    for c in nodes:
        for p in c['inputs']:children[p].append(c['id'])
    targetset=set(targets);weights={}
    for p in nodes:
        cs=children[p['id']]
        if p['id'] in targetset or p['output_memory']==0 or not 2<=len(cs)<=4 or not set(cs)<=targetset:continue
        key=tuple(sorted(cs,key=index.__getitem__))
        weights[key]=min(MAX,weights.get(key,0)+p['output_memory'])
    return [dict(members=list(cs),weight=str(w)) for cs,w in sorted(weights.items(),key=lambda x:(-x[1],tuple(index[c] for c in x[0])))]

def move(permutation,members,pivot):
    selected=set(members);block=[v for v in permutation if v in selected]
    # Independent description: insert before the first unselected element at
    # or after the original boundary, or at the end if none remains.
    before=[v for v in permutation[:max(0,pivot)] if v not in selected]
    after=[v for v in permutation[max(0,pivot):] if v not in selected]
    return before+block+after

def explicit(maximum=False,zero=False):
    # Five low-workspace producers keep median threshold independent of the
    # five anchors. C1 -> P3 -> C4/C5 creates group-crossing precedence.
    # P1/P2 overlap in C1, P1/P4 duplicate the direct-user set. A sink-only
    # producer and a producer with an outside consumer are negative controls.
    records=[(11,0,17,[]),(13,0,19,[]),
      (101,1,41,[11]),(103,2,43,[13]),(105,1,47,[11,13]),
      (107,1,53,[11]),(109,2,59,[13]),(111,1,61,[11]),
      (201,100,7,[101,103]),(203,101,11,[101,105]),
      (205,102,13,[103,105]),(113,1,67,[201,107]),
      (207,103,17,[103,113]),(209,104,19,[101,113]),
      (401,0,23,[201,203,205,207,209]),(403,0,29,[107,109])]
    # P4 shares P1's consumer set and therefore tests weight aggregation.
    for q,(i,w,o,ps) in enumerate(records):
        if i in (201,203,209):records[q]=(i,w,o,ps+[111])
    nodes=[]
    for q,(i,w,o,ps) in enumerate(records):
        if maximum:o=MAX//2+q if i in (101,111) else MAX//31+q;w=w*(MAX//512)
        if zero:o=0
        nodes.append(dict(id=i,core_type='AIC' if q%2 else 'AIV',core_num=1,exec_time=q+1,workspace_memory=w,output_memory=o,inputs=ps))
    return nodes

def main():
    rng=random.Random(203448001);cases=[]
    base=json.loads(Path('data/projection-gold-batch45.json').read_text())['cases']
    inputs=[explicit(),explicit(True),explicit(False,True)]
    # Keep all first 80 existing input controls irrespective of groups; a
    # no-group control still checks that recognition rejects unsafe fusion.
    inputs += [x['nodes'] for x in base[:80]]
    for q,nodes in enumerate(inputs):
        nodes=[dict(v,inputs=list(v['inputs'])) for v in nodes];rng.shuffle(nodes)
        initial=reference(nodes,MAX,[])
        if initial is None:raise AssertionError('Preselected interface must exist')
        expected_groups=groups(nodes,initial['targets'])
        requests=[]
        for group in expected_groups:
            for trial in range(2):
                permutation=initial['targets'][:];rng.shuffle(permutation)
                for pivot in (0,len(permutation)//2,len(permutation)):
                    changed=move(permutation,group['members'],pivot)
                    cap=MAX if q==1 else 500
                    gold=reference(nodes,cap,changed)
                    requests.append(dict(permutation=permutation,members=group['members'],pivot=pivot,moved=changed,gold=gold))
        cases.append(dict(name=f'group_control_{q}',hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=MAX if q==1 else 500,event_record_time=0,event_wait_time=0),nodes=nodes,groups=expected_groups,requests=requests))
    p=Path('data/group-gold-batch48.json');p.write_text(json.dumps(dict(format='aicore-local-group-gold-v1',cases=cases)),encoding='utf-8')
    summary=dict(seed=203448001,cases=len(cases),requests=sum(len(c['requests']) for c in cases),no_group_controls=sum(not c['groups'] for c in cases),input_sha=hashlib.sha256(p.read_bytes()).hexdigest(),reference='Original direct-consumer sets; independent stable boundary insertion; full ancestors and prefix/future live-set bigint profile',explicit=['crossed group dependency','overlapping members','duplicate user-set priority saturation','last DIRECT release','MAX and above-MAX profile','zero outputs','multiple roots/sinks'])
    Path('reports/group-gold-generation-batch48.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
