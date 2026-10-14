"""Arithmetic attribution of frozen R52 states; no schedule/search execution.

Witness is used ONLY as diagnostic comparison and separately labelled. The
mechanism evidence below uses original input plus recorded physical states.
"""
from pathlib import Path
import hashlib,json,heapq
dest=Path('research/batch56');dest.mkdir(exist_ok=True)
input_path='research/batch52/observer-selected12-input-only.json'
observer_path='reports/observer-observed-batch52.json'
inputs=json.loads(Path(input_path).read_text())['cases']
observed={c['name']:c for c in json.loads(Path(observer_path).read_text())['cases']}
original_paths=['data/hard-corpus-resumed.json','data/projection-retention-heldout-batch45.json']
original={c['name']:(p,c) for p in original_paths for c in json.loads(Path(p).read_text())['cases']}
rows=[]
for case in inputs:
    name=case['name'];record=observed[name];by={v['id']:v for v in case['nodes']};ids=list(by);out={i:set() for i in ids}
    for v in by.values():
        for p in v['inputs']:out[p].add(v['id'])
    degree={i:len(by[i]['inputs']) for i in ids};ready=[i for i in ids if not degree[i]];heapq.heapify(ready);topo=[]
    while ready:
        i=heapq.heappop(ready);topo.append(i)
        for c in out[i]:
            degree[c]-=1
            if not degree[c]:heapq.heappush(ready,c)
    assert len(topo)==len(ids)
    pos={i:k for k,i in enumerate(topo)};bit={i:1<<pos[i] for i in ids};desc={};anc={}
    for i in reversed(topo):desc[i]=bit[i]|sum([],0) if False else bit[i]
    for i in reversed(topo):
        for c in out[i]:desc[i]|=desc[c]
    for i in topo:
        anc[i]=0
        for p in by[i]['inputs']:anc[i]|=anc[p]|bit[p]
    pinned={j:[p for p in ids if p!=j and by[p]['output_memory'] and (not out[p] or any(desc[j]&bit[c] for c in out[p]))] for j in ids}
    cap=case['hardware']['memory_limit']
    def held(D):return {p for p in D if not out[p] or out[p]-D}
    def live(D):return sum(by[p]['output_memory'] for p in held(D))
    def physical(D,i):return set(by[i]['inputs'])<=D and live(D)+by[i]['workspace_memory']+by[i]['output_memory']<=cap
    def forced(D,j):
        # At j BEGIN all strict ancestors have completed. A completed producer
        # with an original DIRECT user at/after j cannot be freed before j.
        h=[p for p in pinned[j] if p in D or anc[j]&bit[p]]
        return by[j]['workspace_memory']+by[j]['output_memory']+sum(by[p]['output_memory'] for p in h),h
    def bad(D):
        return [dict(node=j,bound=b,held=h) for j in ids if j not in D for b,h in [forced(D,j)] if b>cap]
    def closure(D,p):
        C=set();stack=list(out[p]-D)
        while stack:
            i=stack.pop()
            if i in D or i in C:continue
            C.add(i);stack.extend(by[i]['inputs'])
        return C
    outer=next(s for s in record['helper_observer']['snapshots'] if s['kind']=='outer')
    prefix=outer['outer_completed_order'];D=set();first_bad=None;prefix_physics=[]
    for k,i in enumerate(prefix):
        assert i not in D and physical(D,i)
        oldbad=bad(D);D.add(i);newbad=bad(D)
        prefix_physics.append(dict(id=i,live=live(D)))
        if not oldbad and newbad and first_bad is None:first_bad=dict(step=k,choice=i,bad=newbad)
    endD={i for i,d in zip(outer['node_ids'],outer['done']) if d}
    if prefix:assert endD==D
    hp=sorted((p for p in held(endD) if out[p]-endD and by[p]['output_memory']),key=lambda p:(-by[p]['output_memory'],p))
    closure_rows=[]
    for rank,p in enumerate(hp):
        C=closure(endD,p)
        closure_rows.append(dict(producer=p,rank=rank,size=len(C),within128=len(C)<=128,within_top24=rank<24,held_output=by[p]['output_memory']))
    # Original serial witness: diagnostic only, never selected algorithm orders.
    origin_path,orig=original[name]
    for key in ('hardware','nodes','deadline_us'):assert case[key]==orig[key]
    streams=[s for s in orig['witness_plan']['streams'] if s['tasks']];assert len(streams)==1
    w=[t['op_id'] for t in streams[0]['tasks']];assert len(w)==len(set(w))==len(ids)
    WD=set();wpeak=0;elapsed=0
    for i in w:
        assert physical(WD,i)
        wpeak=max(wpeak,live(WD)+by[i]['workspace_memory']+by[i]['output_memory']);WD.add(i);elapsed+=by[i]['exec_time']
    assert elapsed<=case['deadline_us']
    common=0
    while common<min(len(prefix),len(w)) and prefix[common]==w[common]:common+=1
    probes=[]
    for index,s in enumerate(record['helper_observer']['snapshots']):
        if s['kind']!='probe' or s['reason']!='ready_but_no_fit' or s['transition_may_be_incomplete']:continue
        SD={i for i,d in zip(s['node_ids'],s['done']) if d};C=set(s['closure_construction_seen_ids']);initial=SD-set(s['probe_completed_order'])
        assert live(SD)==s['live']
        outside_fit=[i for i in ids if i not in SD and i not in C and physical(SD,i)]
        assists=[]
        for i in outside_fit:
            released=[p for p in by[i]['inputs'] if out[p]-SD=={i}]
            net=by[i]['output_memory']-sum(by[p]['output_memory'] for p in released)
            newly_fit=[j for j in C-SD if physical(SD|{i},j)]
            if newly_fit:
                # Propose complete ORIGINAL closure union, not dropping external
                # direct users or treating arbitrary fit i as data predecessor.
                bridges=[]
                for p in released:
                    C2=closure(initial,p);union=C|C2
                    bridges.append(dict(producer=p,second_closure=len(C2),union_size=len(union),within128=len(union)<=128,
                                        original_outer_rank=hp.index(p) if p in hp else None))
                assists.append(dict(outside_node=i,net=net,released=sorted(released),newly_fit=sorted(newly_fit),bridges=bridges))
        probes.append(dict(snapshot=index,producer=s['producer_id'],C=len(C),initial_D=len(initial),terminal_D=len(SD),
                           initial_live=live(initial),terminal_live=live(SD),external_held=s['held_external_cut_output'],
                           initial_forced_violations=bad(initial),terminal_forced_violations=bad(SD),
                           global_outside_fit=len(outside_fit),one_external_step_opens_cut=assists,
                           limits='A feasible next BEGIN is not a complete cut or whole recovery; observer retains at most2 snapshots/reason.'))
    rows.append(dict(name=name,whole_valid=record['whole']['valid'],outer_reason=outer['reason'],outer_prefix=len(prefix),
                     end_done=len(endD),end_live=live(endD),prefix_first_forced_overlap=first_bad,terminal_forced_violations=bad(endD),
                     held_producer_count=len(hp),terminal_closure_coverage=closure_rows,probes=probes,
                     diagnostic_witness_only=dict(source=origin_path,peak=wpeak,T=elapsed,common_order_prefix=common,
                       first_witness_node=w[common] if common<len(w) else None,first_actual_node=prefix[common] if common<len(prefix) else None,
                       forbidden_for_solver=True)))
sources=[input_path,observer_path,*original_paths,__file__,'solution/solution.cpp','research/batch55/negative-checkpoint.json']
doc=dict(status='STATIC_RECORDED_STATE_ORIGINAL_GRAPH_ATTRIBUTION',scope='same R52twelve only, not all63; no solver or search',rows=rows,
 summary=dict(cases=len(rows),failed=sum(not r['whole_valid'] for r in rows),
  failed_terminal_forced=sum(bool(r['terminal_forced_violations']) and not r['whole_valid'] for r in rows),
  probes=sum(len(r['probes']) for r in rows),probe_external_assists=sum(len(p['one_external_step_opens_cut']) for r in rows for p in r['probes']),
  failed_probe_external_assists=sum(len(p['one_external_step_opens_cut']) for r in rows if not r['whole_valid'] for p in r['probes'])),
 sources=[dict(path=p,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in sources])
target=dest/'external-release-static.json';target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(doc['summary']));print('sha256',hashlib.sha256(target.read_bytes()).hexdigest())
