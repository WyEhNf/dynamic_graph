"""Lossless complete expression DAG and presence-preserving audit records.

Wire v1 pools operator strings, uses stable record field IDs, shares an equal
presence mask, and escapes literal values in three enum-valued fields.
PROGRAM, task dependences and floating-point argument text remain unchanged.
"""
from symbolic_metadata import decode_symbols
FIELDS=('id','kind','condition','increment','parent','mode','array','index','loop_ids')
ENUMS={'kind':('for','while'),'mode':('read','write'),'array':('input','output')}

def pack_records(records):
    keys=list(dict.fromkeys(key for row in records for key in row))
    if any(not isinstance(key,str) for key in keys):raise ValueError('record field names must be strings')
    masks=[sum(1<<i for i,key in enumerate(keys) if key in row) for row in records]
    common=masks[0] if masks and all(x==masks[0] for x in masks) else None
    def value(key,v):
        choices=ENUMS.get(key)
        if choices is None:return v
        return choices.index(v) if isinstance(v,str) and v in choices else ['=',v]
    rows=[]
    for row,mask in zip(records,masks):
        values=[value(key,row[key]) for key in keys if key in row]
        rows.append(values if common is not None else [mask,values])
    return [[FIELDS.index(k) if k in FIELDS else k for k in keys],common,rows]

def unpack_records(data):
    if not isinstance(data,list) or len(data)!=3:raise ValueError('invalid packed records')
    encoded,common,rows=data
    if not isinstance(encoded,list) or not isinstance(rows,list):raise ValueError('invalid packed record fields')
    keys=[]
    for key in encoded:
        if type(key) is int and 0<=key<len(FIELDS):keys.append(FIELDS[key])
        elif isinstance(key,str) and key not in FIELDS:keys.append(key)
        else:raise ValueError('invalid packed field ID')
    if len(set(keys))!=len(keys):raise ValueError('duplicate packed record field')
    def valid(mask):return type(mask) is int and mask>=0 and mask>>len(keys)==0
    if common is not None and not valid(common):raise ValueError('invalid shared presence mask')
    result=[]
    for row in rows:
        if common is None:
            if not isinstance(row,list) or len(row)!=2:raise ValueError('invalid packed record row')
            mask,values=row
        else:mask,values=common,row
        if not valid(mask) or not isinstance(values,list) or mask.bit_count()!=len(values):raise ValueError('invalid packed record presence')
        record={};it=iter(values)
        for i,key in enumerate(keys):
            if not mask&(1<<i):continue
            v=next(it);choices=ENUMS.get(key)
            if choices is not None:
                if type(v) is int and 0<=v<len(choices):v=choices[v]
                elif isinstance(v,list) and len(v)==2 and v[0]=='=':v=v[1]
                else:raise ValueError('invalid packed enum or literal')
            record[key]=v
        result.append(record)
    return result

def pack_symbols(pool,loops,accesses):
    ops=list(dict.fromkeys(node[0] for node in pool))
    if any(not isinstance(op,str) for op in ops):raise ValueError('invalid expression operator')
    compact=[[ops.index(node[0]),*node[1:]] for node in pool]
    return ops,compact,pack_records(loops),pack_records(accesses)

def unpack_symbols(ops,pool,loops,accesses):
    if not isinstance(ops,list) or any(not isinstance(op,str) for op in ops) or len(set(ops))!=len(ops):raise ValueError('invalid packed operators')
    if not isinstance(pool,list):raise ValueError('invalid packed expression pool')
    expanded=[]
    for node in pool:
        if not isinstance(node,list) or not node or type(node[0]) is not int or not 0<=node[0]<len(ops):raise ValueError('invalid packed operator ID')
        expanded.append([ops[node[0]],*node[1:]])
    return expanded,unpack_records(loops),unpack_records(accesses)

def decode_packed_symbols(ops,pool,loops,accesses):
    return decode_symbols(*unpack_symbols(ops,pool,loops,accesses))
