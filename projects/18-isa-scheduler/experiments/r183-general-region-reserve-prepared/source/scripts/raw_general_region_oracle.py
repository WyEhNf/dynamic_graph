"""Independent tiny raw physical-history 0/1 oracle, N<=9; no project imports.

COPY may use ANY available old or newest identity representative, including
dead identities; early COPY is allowed. This is broader than production.
All original operations are emitted exactly once. No alias/recompute/GET read.
"""
import heapq
import re
from time import perf_counter


def raw_problem(data):
    rows=data['instructions']; n=len(rows)
    if n>9 or data['bit_width'] not in (2,3,4,5): raise ValueError('raw oracle N<=9/bits2..5')
    args=[]; deps=[]; writes={}; readers={}
    for index,row in enumerate(rows):
        op=row['op']
        if op not in ('GET','SET','ADD','MULW'): raise ValueError('Unsupported original opcode')
        tokens=row.get('inputs',[]); expected={'GET':0,'SET':1,'ADD':2,'MULW':2}[op]
        if len(tokens)!=expected: raise ValueError('Invalid original arity')
        sources=[]
        for token in tokens:
            if not isinstance(token,str) or not re.fullmatch(r't#[1-9][0-9]*',token): raise ValueError('Invalid raw token')
            source=index-int(token[2:])
            if source<0 or rows[source]['op']=='SET': raise ValueError('Invalid original source')
            sources.append(source)
        previous=set(sources)
        if op in ('GET','SET'):
            reg=row['reg']
            if reg in writes: previous.add(writes[reg])
            if op=='GET': readers.setdefault(reg,set()).add(index)
            else:
                previous.update(readers.get(reg,set())); readers[reg]=set(); writes[reg]=index
        args.append(tuple(sources)); deps.append(previous)
    return rows,args,deps,2**data['bit_width']


def solve_raw(data, *, max_states=20000, max_discovered=20000, time_budget_ms=500):
    started=perf_counter(); rows,args,deps,w=raw_problem(data); n=len(rows)
    initial=(0,()); distance={initial:0}; predecessor={initial:None}; queue=[(0,0,initial)]
    serial=0; expanded=0; goal=None; outcome='closed_infeasible'
    while queue:
        if expanded>=max_states or (perf_counter()-started)*1000>=time_budget_ms:
            outcome='unknown_budget'; break
        cost,_,state=heapq.heappop(queue)
        if distance.get(state)!=cost: continue
        mask,history=state
        if mask==(1<<n)-1: goal=state; outcome='optimal'; break
        expanded+=1
        completed={i for i in range(n) if mask&(1<<i)}
        actions=[]
        for index in range(n):
            if index in completed or not deps[index]<=completed: continue
            if any(source not in history for source in args[index]): continue
            # All old-representative combinations affect output tokens but not
            # next history; latest tokens are one equivalent emit witness.
            tokens=[f't#{len(history)-max(j for j,value in enumerate(history) if value==source)}' for source in args[index]]
            physical={'op':rows[index]['op']}
            if rows[index]['op'] in ('GET','SET'): physical['reg']=rows[index]['reg']
            if tokens: physical['inputs']=tokens
            identity=None if rows[index]['op']=='SET' else index
            actions.append(((mask|(1<<index),(history+(identity,))[-w:]),0,physical,index))
        for offset,identity in enumerate(history):
            if identity is None: continue
            physical={'op':'COPY','source':f't#{len(history)-offset}'}
            actions.append(((mask,(history+(identity,))[-w:]),1,physical,None))
        discovery_limit=False
        for after,delta,physical,index in actions:
            candidate=cost+delta
            if distance.get(after,10**30)<=candidate: continue
            if after not in distance and len(distance)>=max_discovered:
                discovery_limit=True; break
            distance[after]=candidate; predecessor[after]=(state,physical,index)
            serial+=1; heapq.heappush(queue,(candidate,serial,after))
        if discovery_limit: outcome='unknown_discovery_budget'; break
    output=None; order=[]
    if goal is not None:
        physical=[]; state=goal
        while predecessor[state] is not None:
            state,row,index=predecessor[state]; physical.append(row)
            if index is not None: order.append(index)
        physical.reverse(); order.reverse()
        output={'block_id':data['block_id'],'optimized_instructions':[dict(row,id=i) for i,row in enumerate(physical)]}
    return {'outcome':outcome,'copies':None if goal is None else distance[goal],
            'output':output,'original_order':order,'expanded_states':expanded,
            'discovered_states':len(distance),'remaining_queue':len(queue),
            'elapsed_ms':(perf_counter()-started)*1000,
            'scope':'Exact strict identities/raw physical histories, all old/early COPY, N<=9. Only optimal/closed exhaustion are proofs; budget is unknown.'}
