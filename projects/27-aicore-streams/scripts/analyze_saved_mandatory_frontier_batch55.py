"""Static necessary-bound review on already recorded R52 prefixes ONLY.

No completion search or candidate source implementation. Diagnose the FIRST
irreversible overlap introduced on a stored original Compute sequence and
whether another already-ready original task would avoid that necessary bound.
"""
from pathlib import Path
import hashlib,json
P=Path('research/batch55');P.mkdir(exist_ok=True)
inputs='research/batch52/observer-selected12-input-only.json';observer='reports/observer-observed-batch52.json';cases={c['name']:c for c in json.loads(Path(inputs).read_text())['cases']};rows=[]
for record in json.loads(Path(observer).read_text())['cases']:
    c=cases[record['name']];by={v['id']:v for v in c['nodes']};out={i:set() for i in by};cap=c['hardware']['memory_limit']
    for v in c['nodes']:
        for p in v['inputs']:out[p].add(v['id'])
    def live(D):return sum(by[p]['output_memory'] for p in D if not out[p] or out[p]-D)
    for index,s in enumerate(record['helper_observer']['snapshots']):
        if s['kind']!='probe' or s['reason']!='ready_but_no_fit' or s['transition_may_be_incomplete'] or not s['probe_completed_order']:continue
        C=set(s['closure_construction_seen_ids']);path=s['probe_completed_order'];endD={i for i,d in zip(s['node_ids'],s['done']) if d};D=endD-set(path)
        descendants={j:{j} for j in C}
        # Set fixed point is static reachability inside complete ancestor C.
        changed=True
        while changed:
            changed=False
            for j in C:
                updated={j}.union(*(descendants[x] for x in out[j]&C))
                if updated!=descendants[j]:descendants[j]=updated;changed=True
        pinned={p:{j for j in C if out[p]&descendants[j] and p not in by[j]['inputs']} for p in by if by[p]['output_memory'] and out[p]}
        def bound(D,j):
            value=by[j]['workspace_memory']+by[j]['output_memory']+sum(by[p]['output_memory'] for p in by[j]['inputs'])
            value+=sum(by[p]['output_memory'] for p in D if not out[p] or j in pinned.get(p,set()))
            return value
        def violations(D):return [(j,bound(D,j)) for j in C-D if bound(D,j)>cap]
        def options(D):
            L=live(D);return [i for i in C-D if set(by[i]['inputs'])<=D and L+by[i]['workspace_memory']+by[i]['output_memory']<=cap]
        initial_bad=violations(D);first=None
        for k,chosen in enumerate(path):
            assert chosen in options(D)
            after=D|{chosen};bad=violations(after)
            if not violations(D) and bad:
                alternatives=[dict(id=i,post_lower_bound_max=max((bound(D|{i},j) for j in C-(D|{i})),default=0)) for i in options(D) if i!=chosen and not violations(D|{i})]
                first=dict(probe_step=k,original_choice=chosen,choice_workspace=by[chosen]['workspace_memory'],choice_output=by[chosen]['output_memory'],before_done=len(D),before_live=live(D),bad_future_targets=[dict(id=j,necessary_overlap=value,capacity=cap) for j,value in bad],preserving_alternatives=alternatives)
                break
            D=after
        rows.append(dict(name=c['name'],saved_snapshot_index=index,partition='failed' if not record['whole']['valid'] else 'old_recovered',producer_id=s['producer_id'],closure=len(C),initial_already_necessary_invalid=[dict(id=j,necessary_overlap=v) for j,v in initial_bad],first_irreversible_original_transition=first,whole_recovery_claim=False))
outdoc=dict(status='STATIC_FROZEN_PREFIX_NECESSARY_BOUND_REVIEW',stored_no_fit_snapshots=len(rows),initial_necessary_invalid=sum(bool(r['initial_already_necessary_invalid']) for r in rows),first_irreversible_transitions=sum(r['first_irreversible_original_transition'] is not None for r in rows),transitions_with_preserving_alternative=sum(bool((r['first_irreversible_original_transition'] or {}).get('preserving_alternatives')) for r in rows),failed_case_names_with_alternative=sorted({r['name'] for r in rows if r['partition']=='failed' and (r['first_irreversible_original_transition'] or {}).get('preserving_alternatives')}),rows=rows,formula='Wj+Oj+all original direct parent outputs + completed original sinks + completed nonparent p outputs if p has originalDIRECT consumer in C-reach(j). Counts distinct p once, parents excluded from extra sum;outside C descendant pins omitted conservatively.',limits='Only fixed already stored prefix arithmetic. Alternative poststate bound<=capacity is necessary,never proof of full completion. Not all probe failures retained;no newsolver/fullgraphs/witnessread/sourcechanges.',sources=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in (inputs,observer,'solution/solution.cpp',__file__)])
(P/'saved-mandatory-frontier-static.json').write_text(json.dumps(outdoc,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in outdoc.items() if k not in ('rows','sources')},indent=2))
