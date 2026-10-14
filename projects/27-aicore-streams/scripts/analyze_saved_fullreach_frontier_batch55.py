"""Static comparison of mandatory memory bounds on frozen R52 paths only.

No scheduling/search/compiled candidate. Original graph reachability includes
outside-cut DIRECT consumers; this can strengthen the earlier C-only bound.
"""
from pathlib import Path
import json,hashlib
inputs='research/batch52/observer-selected12-input-only.json'
observer='reports/observer-observed-batch52.json'
cases={c['name']:c for c in json.loads(Path(inputs).read_text())['cases']}
rows=[]
for record in json.loads(Path(observer).read_text())['cases']:
    c=cases[record['name']];by={v['id']:v for v in c['nodes']};out={i:set() for i in by};cap=c['hardware']['memory_limit']
    for v in c['nodes']:
        for p in v['inputs']:out[p].add(v['id'])
    reach={}
    def descendants(j):
        if j not in reach:
            seen={j};todo=[j]
            while todo:
                for x in out[todo.pop()]:
                    if x not in seen:seen.add(x);todo.append(x)
            reach[j]=seen
        return reach[j]
    def live(D):return sum(by[p]['output_memory'] for p in D if not out[p] or out[p]-D)
    for index,s in enumerate(record['helper_observer']['snapshots']):
        if s['kind']!='probe' or s['reason']!='ready_but_no_fit' or s['transition_may_be_incomplete'] or not s['probe_completed_order']:continue
        C=set(s['closure_construction_seen_ids']);path=s['probe_completed_order'];endD={i for i,d in zip(s['node_ids'],s['done']) if d};D=endD-set(path)
        pinned={p:{j for j in C if out[p]&descendants(j) and p not in by[j]['inputs']} for p in by if by[p]['output_memory'] and out[p]}
        def bound(D,j):
            return by[j]['workspace_memory']+by[j]['output_memory']+sum(by[p]['output_memory'] for p in by[j]['inputs'])+sum(by[p]['output_memory'] for p in D if not out[p] or j in pinned.get(p,set()))
        def violations(D):return [(j,bound(D,j)) for j in C-D if bound(D,j)>cap]
        def options(D):
            L=live(D);return [i for i in C-D if set(by[i]['inputs'])<=D and L+by[i]['workspace_memory']+by[i]['output_memory']<=cap]
        initial_bad=violations(D);first=None
        for k,chosen in enumerate(path):
            assert chosen in options(D)
            bad=violations(D|{chosen})
            if not violations(D) and bad:
                alternatives=[dict(id=i,post_lower_bound_max=max((bound(D|{i},j) for j in C-(D|{i})),default=0)) for i in options(D) if i!=chosen and not violations(D|{i})]
                first=dict(probe_step=k,original_choice=chosen,before_live=live(D),bad_future_targets=[dict(id=j,necessary_overlap=v,capacity=cap) for j,v in bad],preserving_alternatives=alternatives)
                break
            D.add(chosen)
        rows.append(dict(name=c['name'],snapshot=index,partition='failed' if not record['whole']['valid'] else 'old_recovered',closure=len(C),initial_invalid=[dict(id=j,bound=v) for j,v in initial_bad],first=first,terminal_lower_bound_max=max((bound(endD,j) for j in C-endD),default=0),capacity=cap))
doc=dict(status='STATIC_ORIGINAL_FULL_REACH_PREFIX_REVIEW',snapshots=len(rows),initial_invalid=sum(bool(r['initial_invalid']) for r in rows),transitions=sum(bool(r['first']) for r in rows),alternative_transitions=sum(bool((r['first'] or {}).get('preserving_alternatives')) for r in rows),failed_with_alternative=sorted({r['name'] for r in rows if r['partition']=='failed' and (r['first'] or {}).get('preserving_alternatives')}),rows=rows,limits='Stored paths only; no full completion search or actual recovery proof. Full ORIGINAL DAG descendants, not changed/reduced edges. Bound<=cap is only necessary.',sources=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in (inputs,observer,'solution/solution.cpp',__file__)])
Path('research/batch55/saved-fullreach-frontier-static.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in doc.items() if k not in ('rows','sources')},indent=2))
