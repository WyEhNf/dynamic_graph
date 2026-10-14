"""Original-input-only maximal isolated chain *candidate* block audit.

This is not a graph rewrite for submission, an optimum-preservation claim or
a source of memory release credit. Each block's members must later execute
on the original graph; outside inputs end at the HEAD and sink holds remain.
"""
import collections,hashlib,json
from pathlib import Path
def topo_of(ins,outs):
    d=list(map(len,ins));topo=[i for i,x in enumerate(d) if not x]
    for i in topo:
        for c in outs[i]:
            d[c]-=1
            if not d[c]:topo.append(c)
    assert len(topo)==len(ins);return topo
def shape(ins,outs):
    topo=topo_of(ins,outs);roots=[i for i in topo if not ins[i]]
    for prefix in [True,False]:
        role={i:1 if prefix else 2 for i in roots}
        if prefix:
            for i in topo:
                if i not in role and ins[i] and all(role.get(p)==1 for p in ins[i]):role[i]=2
        for i in topo:
            if i not in role and ins[i] and all(role.get(p)==2 for p in ins[i]):role[i]=3
        valid=True
        for i in topo:
            if i not in role:
                if ins[i] and not outs[i] and all(role.get(p)==3 for p in ins[i]):role[i]=4
                else:valid=False;break
        counts=collections.Counter(role.values())
        if valid and counts[2] and 2<=counts[3]<=512:return dict(roles=dict(counts),prefix=prefix)
    return None
def classify(nodes):
    index={v['id']:i for i,v in enumerate(nodes)};ins=[[index[p] for p in v['inputs']] for v in nodes];outs=[[] for v in nodes]
    for i,ps in enumerate(ins):
        for p in ps:outs[p].append(i)
    topo=topo_of(ins,outs);groups=[];owner=[-1]*len(nodes)
    for i in topo:
        if owner[i]>=0:continue
        group=[];u=i
        while True:
            assert owner[u]<0;owner[u]=len(groups);group.append(u)
            if len(outs[u])!=1 or len(ins[outs[u][0]])!=1:break
            u=outs[u][0]
        groups.append(group)
    bins=[[] for _ in groups];bouts=[[] for _ in groups]
    for i,ps in enumerate(ins):
        for p in ps:
            if owner[p]!=owner[i]:
                assert p==groups[owner[p]][-1] and i==groups[owner[i]][0]
                bins[owner[i]].append(owner[p]);bouts[owner[p]].append(owner[i])
    # Check every original node/edge remains represented exactly.
    assert sum(map(len,groups))==len(nodes)
    assert sum(map(len,bins))+sum(len(g)-1 for g in groups)==sum(map(len,ins))
    return dict(n=len(nodes),edges=sum(map(len,ins)),blocks=len(groups),maximum_block_length=max(map(len,groups),default=0),nontrivial_blocks=sum(len(g)>1 for g in groups),chain_internal_nodes=sum(len(g)-1 for g in groups),direct_shallow=shape(ins,outs),block_shallow=shape(bins,bouts))
if __name__=='__main__':
    p=Path('data/hard-corpus-resumed.json');cases=json.loads(p.read_text())['cases'];failed={x['name'] for x in json.loads(Path('reports/hard-functional-batch44.json').read_text())['cases'] if not x['pass']}
    rows=[dict(name=c['name'],failed=c['name'] in failed,**classify(c['nodes'])) for c in cases]
    summaries={}
    for label,rs in [('all',rows),('failed',[r for r in rows if r['failed']])]:
        summaries[label]=dict(records=len(rs),direct_shallow=sum(r['direct_shallow'] is not None for r in rs),block_shallow=sum(r['block_shallow'] is not None for r in rs),newly_supported=sum(r['direct_shallow'] is None and r['block_shallow'] is not None for r in rs),chain_internal_nodes=sum(r['chain_internal_nodes'] for r in rs))
    report=dict(input_sha=hashlib.sha256(p.read_bytes()).hexdigest(),recognition='Only original nodes and input IDs; no witness/order or family-name triggers',summary=summaries,cases=rows)
    Path('reports/chain-window-classification-batch45.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(summaries,indent=2))
