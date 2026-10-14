"""Independent4/5/16/17 DIRECT-set controls and original wide profiles."""
import hashlib,json,random
from pathlib import Path
from make_projection_gold_batch45 import reference,MAX
from make_group_gold_batch48 import move

def groups(nodes,targets):
    index={v['id']:i for i,v in enumerate(nodes)};children={v['id']:[] for v in nodes}
    for c in nodes:
        for p in c['inputs']:children[p].append(c['id'])
    targetset=set(targets);weights={}
    for p in nodes:
        cs=children[p['id']]
        if p['id'] in targetset or p['output_memory']==0 or not 2<=len(cs)<=16 or not set(cs)<=targetset:continue
        key=tuple(sorted(cs,key=index.__getitem__));weights[key]=min(MAX,weights.get(key,0)+p['output_memory'])
    return [dict(members=list(cs),weight=str(w)) for cs,w in sorted(weights.items(),key=lambda x:(-x[1],tuple(index[c] for c in x[0])))]

def boundary(size,maximum=False,zero=False):
    rootA,rootB=13,17;P,Q,L,R,B=101,103,105,107,109;Cs=[1001+i*37 for i in range(size)];Ps=[2003+i*41 for i in range(size)]
    records=[(rootA,0,7,[]),(rootB,0,11,[]),(P,1,MAX//2+20 if maximum else 51,[rootA]),(Q,1,MAX//2+40 if maximum else 53,[rootB]),(L,1,77,[rootA]),(R,1,88,[rootB]),(B,1,55,[rootA,rootB])]
    records += [(p,1,31+i,[rootA if i%2 else rootB]) for i,p in enumerate(Ps)]
    for i,c in enumerate(Cs):
        parents=[P,Q,Ps[i]]
        if i<size-1:parents.append(L)
        if i>0:parents.append(R)
        if i<2:parents.append(B)
        if i and i%3==1:parents.append(Cs[i-1])
        records.append((c,100+i,3+i,parents))
    records += [(501,0,5,[Cs[0],Cs[-1]]),(503,0,10,[B,Cs[0]])]
    return [dict(id=i,core_type='AIC' if q%2 else 'AIV',core_num=1,exec_time=q+1,workspace_memory=w,output_memory=0 if zero else o,inputs=ps) for q,(i,w,o,ps) in enumerate(records)]

def main():
    rng=random.Random(203449001);cases=[];existing=json.loads(Path('data/group-gold-batch48.json').read_text())['cases']
    inputs=[c['nodes'] for c in existing]+[boundary(s,maximum=m,zero=z) for s in (4,5,16,17) for m,z in ((False,False),(True,False),(False,True))]
    for q,nodes in enumerate(inputs):
        nodes=[dict(v,inputs=list(v['inputs'])) for v in nodes];rng.shuffle(nodes);initial=reference(nodes,MAX,[]);assert initial is not None
        expected=groups(nodes,initial['targets']);requests=[]
        for group in expected:
            for trial in range(2):
                permutation=initial['targets'][:];rng.shuffle(permutation)
                for pivot in (0,len(permutation)//2,len(permutation)):
                    changed=move(permutation,group['members'],pivot);capacity=MAX if q>=len(existing) and (q-len(existing))%3==1 else 500
                    requests.append(dict(permutation=permutation,members=group['members'],pivot=pivot,moved=changed,gold=reference(nodes,capacity,changed)))
        cases.append(dict(name=f'group_size_control_{q}',hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=MAX if q>=len(existing) and (q-len(existing))%3==1 else 500,event_record_time=0,event_wait_time=0),nodes=nodes,groups=expected,requests=requests))
    p=Path('data/group-gold-batch49.json');p.write_text(json.dumps(dict(format='aicore-local-group-gold-v1',cases=cases)),encoding='utf-8')
    summary=dict(seed=203449001,cases=len(cases),requests=sum(len(c['requests']) for c in cases),no_group_controls=sum(not c['groups'] for c in cases),large_groups=sum(len(g['members'])>4 for c in cases for g in c['groups']),input_sha=hashlib.sha256(p.read_bytes()).hexdigest(),reference='Original full DIRECT-user set2..16;stable boundary slicing;full ancestors and prefix/future live-set bigint profile',explicit=['size4 old boundary','size5 new','size16 inclusive','size17 rejected whole-user set','dependency crossings','overlaps','outside direct consumer','MAX and saturated priority','O0','all original roots/sinks'])
    Path('reports/group-gold-generation-batch49.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
