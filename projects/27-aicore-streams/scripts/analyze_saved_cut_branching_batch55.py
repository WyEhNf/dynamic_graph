"""Input-only arithmetic on already recorded R52 cut paths, no new search."""
from pathlib import Path
import json,hashlib
inputs='research/batch52/observer-selected12-input-only.json';observer='reports/observer-observed-batch52.json'
cases={c['name']:c for c in json.loads(Path(inputs).read_text())['cases']};rows=[]
for r in json.loads(Path(observer).read_text())['cases']:
    c=cases[r['name']];by={v['id']:v for v in c['nodes']};out={i:set() for i in by};cap=c['hardware']['memory_limit']
    for v in by.values():
        for p in v['inputs']:out[p].add(v['id'])
    def live(D):return sum(by[p]['output_memory'] for p in D if not out[p] or out[p]-D)
    for k,s in enumerate(r['helper_observer']['snapshots']):
        if s['kind']!='probe' or s['reason']!='ready_but_no_fit' or s['transition_may_be_incomplete'] or not s['probe_completed_order']:continue
        C=set(s['closure_construction_seen_ids']);D={i for i,d in zip(s['node_ids'],s['done']) if d}-set(s['probe_completed_order']);forks=[]
        for depth,i in enumerate(s['probe_completed_order']):
            L=live(D);options=[j for j in C-D if set(by[j]['inputs'])<=D and L+by[j]['workspace_memory']+by[j]['output_memory']<=cap]
            assert i in options
            if len(options)>1:forks.append(dict(depth=depth,physical_options=len(options),old_chosen=i,old_choice_output=by[i]['output_memory'],old_choice_workspace=by[i]['workspace_memory']))
            D.add(i)
        U=C|set(p for i in C for p in by[i]['inputs']);Ein=sum(len(by[i]['inputs']) for i in C);Einternal=sum(len(out[i]&C) for i in C)
        # Predeclared loose bound, not actual charge or observed wall/CPU. The
        # compact state-copy term alone is enough to expose potential costs.
        copy_upper=4*len(C)*(len(U)+len(C)+6)
        rows.append(dict(name=c['name'],snapshot=k,partition='failed' if not r['whole']['valid'] else 'old_recovered',cut=len(C),touched_original_producers=len(U),input_edges=Ein,internal_output_edges=Einternal,recorded_steps=len(s['probe_completed_order']),fork_steps=len(forks),earliest_fork_depth=forks[0]['depth'] if forks else None,latest_fork_depth=forks[-1]['depth'] if forks else None,max_options=max((f['physical_options'] for f in forks),default=1),maximum_state_copy_logical_work=copy_upper,first_three_forks=forks[:3],limits='A fork is a real alternative at a stored state, not proof of a completing branch. At most4 children/depth is a width2/branching2 envelope, not an executed beam.'))
doc=dict(status='STATIC_STORED_CUT_BRANCHING',snapshots=len(rows),with_earlier_fork=sum(bool(x['fork_steps']) for x in rows),failed_snapshots=sum(x['partition']=='failed' for x in rows),failed_with_fork=sum(x['partition']=='failed' and bool(x['fork_steps']) for x in rows),failed_case_names_with_fork=sorted({x['name'] for x in rows if x['partition']=='failed' and x['fork_steps']}),rows=rows,sources=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in (inputs,observer,'solution/solution.cpp',__file__)])
Path('research/batch55/saved-cut-branching-static.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in doc.items() if k not in ('rows','sources')},indent=2))
