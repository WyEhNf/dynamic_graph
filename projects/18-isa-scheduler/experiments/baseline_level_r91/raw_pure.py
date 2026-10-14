"""Independent raw grammar/reference validation for pure mathematical proofs.

No scheduler DAG and no SHA expression graph. Output verification remains a
separate mandatory symbolic/numeric check. COPY-bearing inputs are excluded.
"""
from .verify import _original_header,_reference_distance
from .model import InvalidBlock


def dependencies(data):
    _original_header(data);rows=data['instructions'];args=[];seen=set()
    fields={'GET':{'id','op','reg','inputs'},'SET':{'id','op','reg','inputs'},
            'ADD':{'id','op','inputs'},'MULW':{'id','op','inputs'}}
    arities={'GET':0,'SET':1,'ADD':2,'MULW':2}
    for index,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('op'),str) or row['op'] not in fields:
            raise InvalidBlock('Pure COPY-free instructions required')
        op=row['op']
        if not row.keys()<=fields[op]:raise InvalidBlock('Unknown pure instruction field')
        identifier=row.get('id',index)
        if type(identifier) not in (int,str) or identifier in seen:raise InvalidBlock('Invalid/duplicate instruction id')
        seen.add(identifier);tokens=row.get('inputs',[])
        if not isinstance(tokens,list) or len(tokens)!=arities[op]:raise InvalidBlock('Invalid input arity')
        if op in ('GET','SET') and (not isinstance(row.get('reg'),str) or not row['reg']):raise InvalidBlock('GET/SET register required')
        sources=tuple(index-_reference_distance(token)for token in tokens)
        if any(source<0 for source in sources):raise InvalidBlock('Future/current or unreachable reference')
        args.append(sources)
    return args
