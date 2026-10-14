"""Readonly saved-state bigint/reachability attribution; no schedule search or solver."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rawpath=Path('G:/Hackathon-project27-owned/batch56-observer-c1ea2391/outputs/observer12.json')
assert sha(rawpath)=='a9132ba8f21898b7b9e85827d2024aad134ae5c0b69156a2869cbd4dda654f65'
cases={c['name']:c for c in json.loads(rawpath.read_text())['cases']}
inputpath=Path('research/batch52/observer-selected12-input-only.json');inputs={c['name']:c for c in json.loads(inputpath.read_text())['cases']}
rows=[]
for name in ('projection_retention_seed203451023','projection_retention_seed203451018'):
    c=cases[name];f=inputs[name];v={n['id']:n for n in f['nodes']};ids=[n['id'] for n in f['nodes']];out={i:[] for i in ids}
    for n in f['nodes']:
        for p in n['inputs']:out[p].append(n['id'])
    def reach(start,edges):
        seen={start};todo=[start]
        while todo:
            i=todo.pop()
            for q in edges[i]:
                if q not in seen:seen.add(q);todo.append(q)
        return seen
    ins={i:v[i]['inputs'] for i in ids};o=c['helper_observer'];labels={s['id']:s['label'] for s in o['stage_counts']}
    pair=next(x for x in o['metadata'] if labels[x['stage']]=='restart-detector-return-before-status-charge');j=pair['target_id'];pdelayed=pair['producer_id']
    old,guard=o['states'];prefix=guard['prefix_ids'];D=set(prefix);desc=reach(j,out);anc=reach(j,ins)-{j}
    pinned={p for p in ids if p!=j and (not out[p] or any(q in desc for q in out[p]))}
    base=v[j]['workspace_memory']+v[j]['output_memory']+sum(v[p]['output_memory'] for p in anc & pinned)
    forced=base;first=None;trace=[]
    for k,p in enumerate(prefix):
        add=v[p]['output_memory'] if p in pinned and p not in anc else 0
        before=forced;forced+=add;trace.append(dict(step=k,id=p,added=add,before=before,after=forced))
        if j not in prefix[:k] and first is None and before<=f['hardware']['memory_limit']<forced:
            first=dict(step=k,id=p,output=v[p]['output_memory'],bound_before=before,bound_after=forced,original_inputs=v[p]['inputs'],original_DIRECT_users=out[p],pinned_DIRECT_users=[q for q in out[p] if q in desc],is_sink=not out[p],in_old_cut_prefix=p in old['prefix_ids'],producer_is_strict_ancestor=p in anc,producer_is_descendant=p in desc)
    ready=[]
    for i in ids:
        if i not in D and all(p in D for p in v[i]['inputs']):
            demand=guard['live']+v[i]['workspace_memory']+v[i]['output_memory'];free=sum(v[p]['output_memory'] for p in v[i]['inputs'] if sum(q not in D for q in out[p])==1)
            ready.append(dict(id=i,W=v[i]['workspace_memory'],O=v[i]['output_memory'],inputs=v[i]['inputs'],BEGIN_memory=demand,deficit=demand-f['hardware']['memory_limit'],memory_fit=demand<=f['hardware']['memory_limit'],output_freed_at_Compute_END=free,net_output=v[i]['output_memory']-free,guard_blocks=i==pdelayed and j not in D))
    held=[]
    for p in ids:
        rem=[q for q in out[p] if q not in D]
        if p in D and v[p]['output_memory'] and (rem or not out[p]):
            closure=set()
            for q in rem:closure|=reach(q,ins)-D
            heads=[q for q in closure if all(a in D for a in ins[q])]
            held.append(dict(id=p,O=v[p]['output_memory'],sink_retained=not out[p],remaining_original_DIRECT_users=rem,closure_original_ids=sorted(closure),closure_size=len(closure),within128=len(closure)<=128,ready_original_heads=[dict(id=q,BEGIN_memory=guard['live']+v[q]['workspace_memory']+v[q]['output_memory'],memory_fit=guard['live']+v[q]['workspace_memory']+v[q]['output_memory']<=f['hardware']['memory_limit']) for q in heads]))
    violations=[]
    for t in ids:
        if t in D:continue
        a=reach(t,ins)-{t};d=reach(t,out);heldforced=[]
        for p in ids:
            if p!=t and (p in a or p in D) and v[p]['output_memory'] and (not out[p] or any(q in d for q in out[p])):heldforced.append(p)
        b=v[t]['workspace_memory']+v[t]['output_memory']+sum(v[p]['output_memory'] for p in heldforced)
        if b>f['hardware']['memory_limit']:violations.append(dict(target=t,bound=b,pinned=heldforced))
    assert not any(x['memory_fit'] for x in ready)
    assert sum(x['O'] for x in held)==guard['live']
    rows.append(dict(name=name,n=len(ids),hardware=f['hardware'],deadline_us=f['deadline_us'],actual_pair=pair,selected_J_completed=j in D,selected_P_completed=pdelayed in D,old_cut_prefix=old['prefix_ids'],actual_guard_prefix=prefix,guard_live=guard['live'],strict_ancestors=sorted(anc),descendants_including_J=sorted(desc),target_base_bound=base,target_final_bound=forced if j not in D else None,target_completed_scope='Bound applies only before selected J Compute; selected J already completed so no final bound claim' if j in D else 'Selected J remains unfinished; final bound is a necessary future Compute bound',first_new_guard_bound_crossing=first,prefix_bound_trace=trace,all_unfinished_target_pin_violations=violations,all_ready_original_nodes=ready,original_held_outputs=held,scope='Exact saved guard prefix only; no hypothetical continuation, oracle or solver. Closures static original remaining DIRECT-user ancestor sets, not feasible-cut claims.'))
doc=dict(status='READONLY_ACTUAL_GUARD_PREFIX_BIGINT_ATTRIBUTION_REVISION1_FUTURE_TARGET_SCOPE',prior_report_sha256=sha(P/'actual-guard-prefix-attribution.json'),erratum='Initial fixed-J arithmetic after J completed is not a necessary future bound; all-unfinished-target checks were correct and stay unchanged.',source_raw_path=str(rawpath),source_raw_sha256=sha(rawpath),input_sha256=sha(inputpath),root_observer_audit_path='F:/Hackathon/outputs/stage2-root-causal-observer-actual-r56.json',root_observer_audit_sha256=sha('F:/Hackathon/outputs/stage2-root-causal-observer-actual-r56.json'),rows=rows,solver_executed=False,graph_or_budget_changed=False,default_changed=False)
target=P/'actual-guard-prefix-attribution-revision1.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(target),sha256=sha(target),cases=[dict(name=r['name'],prefix=len(r['actual_guard_prefix']),live=r['guard_live'],base=r['target_base_bound'],final=r['target_final_bound'],first_cross=r['first_new_guard_bound_crossing'],ready=len(r['all_ready_original_nodes']),pin_violations=len(r['all_unfinished_target_pin_violations']),held=len(r['original_held_outputs']),closure_above128=sum(not h['within128'] for h in r['original_held_outputs'])) for r in rows],solver_executed=False),indent=2))
