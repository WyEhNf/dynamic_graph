"""Independent raw-set/history emitter and replay; no scheduler imports.

Used to construct first functional incumbents and replay all diagnostic paths.
No production graph, state, transition, parser, or cache is trusted.
"""
import re
from time import perf_counter
from scripts.raw_general_region_oracle import raw_problem


def problem(data):
    # Hand11 is a functional witness, outside the tiny optimal oracle cap.
    if len(data['instructions'])<=9: rows,args,deps,w=raw_problem(data)
    else:
        rows=data['instructions']; w=2**data['bit_width']; args=[]; deps=[]; writes={}; readers={}
        for i,row in enumerate(rows):
            sources=tuple(i-int(token[2:]) for token in row.get('inputs',[])); previous=set(sources)
            if any(source<0 or rows[source]['op']=='SET' for source in sources): raise ValueError('Raw source error')
            if row['op'] in ('GET','SET'):
                reg=row['reg']
                if reg in writes: previous.add(writes[reg])
                if row['op']=='GET': readers.setdefault(reg,set()).add(i)
                else: previous.update(readers.get(reg,set())); readers[reg]=set(); writes[reg]=i
            args.append(sources); deps.append(previous)
    users=[set() for _ in rows]
    for index,sources in enumerate(args):
        for source in set(sources): users[source].add(index)
    return rows,args,deps,w,users


def replay(data, output, order, *, full=True):
    originals,args,deps,w,users=problem(data); physical=output['optimized_instructions']
    if output['block_id']!=data['block_id']: raise AssertionError('Wrong raw output block id')
    if len(set(order))!=len(order) or any(type(index)is not int or not 0<=index<len(originals) for index in order):
        raise AssertionError('Invalid raw original permutation')
    if full and set(order)!=set(range(len(originals))): raise AssertionError('Missing originals')
    history=[]; completed=set(); cursor=0; copies=0
    for position,row in enumerate(physical):
        if type(row.get('id'))is not int or row['id']!=position: raise AssertionError('Invalid physical id')
        op=row['op']; tokens=[row.get('source')] if op=='COPY' else row.get('inputs',[])
        if op not in ('COPY','GET','SET','ADD','MULW'): raise AssertionError('Unknown physical operation')
        if not isinstance(tokens,list) or len(tokens)!={'COPY':1,'GET':0,'SET':1,'ADD':2,'MULW':2}[op]:
            raise AssertionError('Raw physical arity')
        sources=[]
        for token in tokens:
            if not isinstance(token,str) or not re.fullmatch(r't#[1-9][0-9]*',token): raise AssertionError('Raw token grammar')
            distance=int(token[2:])
            if not 1<=distance<=min(position,w): raise AssertionError('Raw physical age')
            source=history[-distance]
            if source is None: raise AssertionError('SET has no output identity')
            sources.append(source)
        if op=='COPY': identity=sources[0]; copies+=1
        else:
            if cursor>=len(order): raise AssertionError('Unexpected original operation')
            identity=order[cursor]; cursor+=1; original=originals[identity]
            if original['op']!=op or tuple(sources)!=args[identity] or not deps[identity]<=completed:
                raise AssertionError('Raw original ordered args / hazard mismatch')
            if op in ('GET','SET') and row.get('reg')!=original['reg']: raise AssertionError('Original register changed')
            completed.add(identity)
            if op=='SET': identity=None
        history.append(identity)
    if cursor!=len(order): raise AssertionError('Missing physical original')
    roles=[]
    for source in completed:
        if users[source]-completed:
            positions=[i for i,value in enumerate(history) if value==source]
            if not positions: raise AssertionError('Missing live representative')
            age=len(history)-positions[-1]
            if age>w: raise AssertionError('Expired raw future identity')
            roles.append((source,age))
    return {'done':completed,'roles':tuple(sorted(roles)),'history':tuple(history[-w:]),'copies':copies}


def issue(raw, physical, done, history, index):
    """Raw physical ring: relay only a uniquely retained endangered identity."""
    originals,args,deps,w,users=raw
    if index in done or not deps[index]<=done: return None
    result=[dict(row) for row in physical]; ring=list(history); after=done|{index}; rotations=0
    last={source for source in args[index] if not (users[source]-after)}
    while len(ring)>=w:
        oldest=ring[-w]
        must_keep=oldest is not None and bool(users[oldest]-done) and oldest not in last
        sole=oldest not in ring[-w+1:]
        if not (must_keep and sole): break
        if rotations>=w: return None
        result.append({'id':len(result),'op':'COPY','source':f't#{w}'})
        ring=(ring+[oldest])[-w:]; rotations+=1
    if any(source not in ring for source in args[index]): return None
    row={'id':len(result),'op':originals[index]['op']}
    if 'reg' in originals[index]: row['reg']=originals[index]['reg']
    if args[index]: row['inputs']=[f't#{len(ring)-max(i for i,value in enumerate(ring) if value==source)}' for source in args[index]]
    result.append(row); ring=(ring+[None if row['op']=='SET' else index])[-w:]
    if any(source not in ring for source in after if users[source]-after): return None
    return result,after,tuple(ring)


def construct_initial(data, *, max_states=20000, time_budget_ms=500):
    """Bounded iterative raw feasibility DFS, original-rank priority, no cost claim."""
    raw=problem(data); n=len(raw[0]); started=perf_counter(); stack=[([],set(),(),[])]; seen=set(); processed=0
    while stack:
        if processed>=max_states or (perf_counter()-started)*1000>=time_budget_ms:
            return {'outcome':'initial_unknown_budget','processed':processed,'remaining_stack':len(stack)}
        physical,done,history,order=stack.pop(); state=(frozenset(done),history)
        if state in seen: continue
        seen.add(state); processed+=1
        if len(done)==n:
            return {'outcome':'constructed','processed':processed,'candidate':{
                'output':{'block_id':data['block_id'],'optimized_instructions':physical},
                'original_order':order,'copies':len(physical)-n}}
        for index in reversed(range(n)):
            if index in done or not raw[2][index]<=done: continue
            moved=issue(raw,physical,done,history,index)
            if moved is not None: stack.append((*moved,order+[index]))
    return {'outcome':'initial_restricted_exhausted','processed':processed,'remaining_stack':0,
            'scope':'Not a global infeasibility certificate: latest/deadline physical emitter restriction.'}


def raw_prefix(data,initial,start):
    rows=[]; issued=[]; cursor=0
    for row in initial['output']['optimized_instructions']:
        if row['op']!='COPY' and cursor==start: break
        rows.append(dict(row))
        if row['op']!='COPY': issued.append(initial['original_order'][cursor]); cursor+=1
    observed=replay(data,{'block_id':data['block_id'],'optimized_instructions':rows},issued,full=False)
    return rows,observed['done'],observed['history']


def replay_label(data,initial,start,labels,record):
    version=record['label_version']; chain=[]; cursor=version; seen=set()
    while labels[cursor]['predecessor_label'] is not None:
        if cursor in seen: raise AssertionError('Predecessor cycle')
        seen.add(cursor); label=labels[cursor]; chain.append(label['action']); cursor=label['predecessor_label']
    chain.reverse(); physical,done,history=raw_prefix(data,initial,start); raw=problem(data)
    for index in chain:
        moved=issue(raw,physical,done,history,index)
        if moved is None: raise AssertionError('Immutable label path cannot physically replay')
        physical,done,history=moved
    prefix_order=initial['original_order'][:start]+chain
    observed=replay(data,{'block_id':data['block_id'],'optimized_instructions':physical},prefix_order,full=False)
    members=initial['original_order'][start:start+32]
    mask=sum(1<<members.index(index) for index in chain)
    roles=tuple(tuple(pair) for pair in record['roles'])
    if mask!=record['done_mask'] or observed['roles']!=roles or len(physical)!=record['g'] or len(data['instructions'])-len(done)!=record['h']:
        raise AssertionError('Raw physical done_mask/roles/g/h differs')
    return {'rows':len(physical),'original_prefix_count':len(done),'copies':observed['copies']}
