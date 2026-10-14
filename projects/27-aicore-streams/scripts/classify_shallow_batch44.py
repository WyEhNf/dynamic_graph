"""Input-only role audit; never access plans, witnesses, names for recognition."""
import collections, hashlib, json
from pathlib import Path

def classify(nodes):
    index={v['id']:i for i,v in enumerate(nodes)}
    parents=[[index[x] for x in v['inputs']] for v in nodes]
    children=[[] for _ in nodes]
    for i,ps in enumerate(parents):
        for p in ps:children[p].append(i)
    degree=list(map(len,parents));topo=[i for i,d in enumerate(degree) if d==0]
    levels=[0]*len(nodes)
    for p in topo:
        for c in children[p]:
            levels[c]=max(levels[c],levels[p]+1);degree[c]-=1
            if degree[c]==0:topo.append(c)
    assert len(topo)==len(nodes)
    roots={i for i,ps in enumerate(parents) if not ps}
    # A common zero/one-node prefix can precede an independent producer layer.
    prefix=next(iter(roots)) if len(roots)==1 else None
    producers={i for i,ps in enumerate(parents) if not ps or (prefix is not None and ps==[prefix])}
    if prefix is not None:producers.discard(prefix)
    consumers={i for i,ps in enumerate(parents) if ps and set(ps)<=producers}
    tail=set(range(len(nodes)))-producers-consumers-({prefix} if prefix is not None else set())
    shallow=bool(producers and consumers) and all(set(parents[i])<=consumers for i in tail) and all(not children[i] for i in tail)
    return dict(n=len(nodes),edges=sum(map(len,parents)),max_level=max(levels,default=0),level_counts=dict(collections.Counter(levels)),
        roots=len(roots),prefix=prefix is not None,producers=len(producers),consumers=len(consumers),tail=len(tail),strict_shallow=shallow,
        producer_workspace_values=sorted({nodes[i]['workspace_memory'] for i in producers}),
        producer_max_fanout=max((len(children[i]) for i in producers),default=0),consumer_max_inputs=max((len(parents[i]) for i in consumers),default=0))

if __name__=='__main__':
    p=Path('data/hard-corpus-resumed.json');cases=json.loads(p.read_text())['cases']
    failed={c['name'] for c in json.loads(Path('reports/paired-hard-batch43-1-after.json').read_text())['cases'] if not c['pass']}
    result=[dict(name=c['name'],failed=c['name'] in failed,**classify(c['nodes'])) for c in cases]
    summary={key:dict(records=len(rows),strict_shallow=sum(x['strict_shallow'] for x in rows),varying_producer_workspace=sum(x['strict_shallow'] and len(x['producer_workspace_values'])>1 for x in rows),max_level_counts=dict(collections.Counter(x['max_level'] for x in rows))) for key,rows in [('all',result),('failed',[x for x in result if x['failed']])]}
    out=dict(input_sha=hashlib.sha256(p.read_bytes()).hexdigest(),recognition='nodes and original inputs only, no witness/order/family trigger',summary=summary,cases=result)
    Path('reports/shallow-window-classification-batch44.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
