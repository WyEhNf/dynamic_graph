"""Independent exact original-identity replay from untrusted emission witness.

The witness is a proposed permutation, never scheduler state. Rebuild every
original ordered dependency from raw JSON. Map each physical output slot to
its exact original index, propagate COPY, and require non-COPY operations to
match the next original node and its ordered identity arguments. Register
access traces prove same-register hazards independently. No hashes, DAG model,
prepared graph, algorithm state or arithmetic semantics are used.

Original COPY inputs are explicitly unsupported: non-COPY positions alone
cannot identify which COPY was original. Quality-bound inputs exclude them.
Semantic symbol/numeric checking remains a separate requirement.
"""
from collections import defaultdict
from .raw_pure import dependencies
from .verify import _reference_distance
from .model import InvalidBlock


def check_identity_witness(original,optimized,original_order,*,memory_order='hazard'):
    args=dependencies(original);originals=original['instructions'];count=len(originals)
    if memory_order not in ('hazard','conservative'):raise InvalidBlock('Unknown memory order proof mode')
    if not isinstance(original_order,list) or len(original_order)!=count or any(type(index)is not int for index in original_order) or set(original_order)!=set(range(count)):
        raise InvalidBlock('Original emission witness must be a complete exact permutation')
    if not isinstance(optimized,dict) or not optimized.keys()<={'block_id','optimized_instructions','stats'} or type(optimized.get('block_id')) is not type(original['block_id']) or optimized.get('block_id')!=original['block_id'] or not isinstance(optimized.get('optimized_instructions'),list):
        raise InvalidBlock('Invalid identity proof output header')
    rows=optimized['optimized_instructions'];window=2**original['bit_width'];history=[None]*window;cursor=0;copies=0
    expected_writes=defaultdict(list);actual_writes=defaultdict(list);expected_reads={};last_write={};actual_last_write={};expected_all=[];actual_all=[]
    for index,row in enumerate(originals):
        if row['op']=='GET':expected_reads[index]=last_write.get(row['reg']);expected_all.append(index)
        elif row['op']=='SET':last_write[row['reg']]=index;expected_writes[row['reg']].append(index);expected_all.append(index)
    allowed={'GET':{'id','op','reg','inputs'},'SET':{'id','op','reg','inputs'},'ADD':{'id','op','inputs'},'MULW':{'id','op','inputs'},'COPY':{'id','op','source'}}
    arities={'GET':0,'SET':1,'ADD':2,'MULW':2,'COPY':1}
    for position,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('op'),str) or row['op'] not in allowed or not row.keys()<=allowed[row['op']] or type(row.get('id'))is not int or row['id']!=position:
            raise InvalidBlock('Malformed identity proof output row')
        op=row['op'];tokens=[row.get('source')] if op=='COPY' else row.get('inputs',[])
        if not isinstance(tokens,list) or len(tokens)!=arities[op]:raise InvalidBlock('Invalid identity proof arity')
        sources=[]
        for token in tokens:
            distance=_reference_distance(token)
            if distance>window or distance>position:raise InvalidBlock('Illegal identity proof relative reference')
            sources.append(history[(position-distance)%window])
        if op=='COPY':identity=sources[0];copies+=1
        else:
            if cursor>=count:raise InvalidBlock('Unexpected additional original operation')
            identity=original_order[cursor];cursor+=1;expected=originals[identity]
            if op!=expected['op'] or tuple(sources)!=args[identity] or (op in ('GET','SET') and row.get('reg')!=expected['reg']):
                raise InvalidBlock('Original operation or ordered identity operands do not match witness')
            if op=='GET':
                if actual_last_write.get(row['reg'])!=expected_reads[identity]:raise InvalidBlock('GET moved across same-register SET')
                actual_all.append(identity)
            elif op=='SET':actual_last_write[row['reg']]=identity;actual_writes[row['reg']].append(identity);actual_all.append(identity)
        history[position%window]=identity
    if cursor!=count:raise InvalidBlock('Missing original operations in identity proof output')
    if dict(actual_writes)!=dict(expected_writes):raise InvalidBlock('Same-register SET order changed')
    if memory_order=='conservative' and actual_all!=expected_all:raise InvalidBlock('Conservative GET/SET order changed')
    return {'verified_original_identities':count,'verified_inserted_copies':copies,'memory_order':memory_order,
            'scope':'raw original DAG positions and ordered operands; original-once; inserted COPY preserves exact identity; register access order; COPY-free input'}
