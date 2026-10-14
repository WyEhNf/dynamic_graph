"""Read ONLY frozen R52 states; no solver, branch implementation or new graph.

Recover the state before the last stored successful Compute action and count
original next-ready/fit sets. This is a static applicability check, NOT an
attempt to complete a cut and NOT a recovery certificate.
"""
from pathlib import Path
import hashlib,json
P=Path('research/batch55');P.mkdir(exist_ok=True)
source='reports/observer-observed-batch52.json';inputs='research/batch52/observer-selected12-input-only.json'
records=json.loads(Path(source).read_text())['cases'];bycase={c['name']:c for c in json.loads(Path(inputs).read_text())['cases']};rows=[]
for record in records:
    c=bycase[record['name']];by={v['id']:v for v in c['nodes']};children={i:set() for i in by}
    for v in c['nodes']:
        for p in v['inputs']:children[p].add(v['id'])
    capacity=c['hardware']['memory_limit']
    def live(D):return sum(by[i]['output_memory'] for i in D if not children[i] or children[i]-D)
    def fits(D,C):
        L=live(D)
        return [i for i in C-D if set(by[i]['inputs'])<=D and L+by[i]['workspace_memory']+by[i]['output_memory']<=capacity]
    def net(D,i):return by[i]['output_memory']-sum(by[p]['output_memory'] for p in by[i]['inputs'] if children[p]-D=={i})
    for sn,s in enumerate(record['helper_observer']['snapshots']):
        if s['kind']!='probe' or s['reason']!='ready_but_no_fit' or s['transition_may_be_incomplete'] or not s['probe_completed_order']:continue
        D={i for i,d in zip(s['node_ids'],s['done']) if d};C=set(s['closure_construction_seen_ids']);last=s['probe_completed_order'][-1];before=D-{last};available=fits(before,C)
        assert last in available and not fits(D,C)
        score=lambda i:(net(before,i),min(2**63-1,by[i]['workspace_memory']+by[i]['output_memory']),i)
        assert min(available,key=score)==last
        alternatives=[]
        for i in sorted(available,key=score):
            if i==last:continue
            after=before|{i};nextfit=fits(after,C)
            if nextfit:alternatives.append(dict(id=i,after_live=live(after),next_original_ready_fit_ids=sorted(nextfit),net=net(before,i)))
        rows.append(dict(name=c['name'],saved_snapshot_index=sn,partition='old_failed' if not record['whole']['valid'] else 'old_recovered_control',producer_id=s['producer_id'],closure_count=len(C),done_before=len(before),initial_available_ids=sorted(available),last_greedy_choice=last,net_last=net(before,last),before_live=live(before),stored_after_live=s['live'],after_original_cut_ready_fit_empty=True,proposed_cheap_trigger=len(available)>=2 and net(before,last)>0,preserving_other_candidates=alternatives,meaning='Only one hypothetical original-DAG END state per available candidate;nextfit existence is not complete cut/whole feasibility. No witness read or plan completed.'))
out=dict(status='STATIC_SAVED_STATE_APPLICABILITY_ONLY',states=len(rows),failed_states=sum(r['partition']=='old_failed' for r in rows),cheap_trigger_states=sum(r['proposed_cheap_trigger'] for r in rows),alternative_preserving_next_fit_states=sum(bool(r['preserving_other_candidates']) for r in rows),failed_alternative_states=sum(r['partition']=='old_failed' and bool(r['preserving_other_candidates']) for r in rows),input_sources=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in (source,inputs,'solution/solution.cpp',__file__)],rows=rows,limits='R52 retains at most two greedy-no-fit snapshots per reason;not all probe failures or all63. No complete future order/solver or quality claim. Snapshot budgets stop earlier in other states;this analysis does not attribute budget failure to capacity.')
(P/'saved-frontier-static.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('rows','input_sources')},indent=2));
for r in rows:print(r['name'],r['saved_snapshot_index'],'available',len(r['initial_available_ids']),'net',r['net_last'],'alternatives',len(r['preserving_other_candidates']))
