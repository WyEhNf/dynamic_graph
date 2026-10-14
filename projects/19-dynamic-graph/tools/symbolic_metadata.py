"""Lossless shared expression DAG encoding for the audit loop/access metadata."""
from __future__ import annotations
import json


def encode_record_table(records):
    """Share field names, retaining missing fields separately from explicit null."""
    keys = list(dict.fromkeys(key for record in records for key in record))
    if any(not isinstance(key, str) for key in keys):
        raise ValueError('record field names must be strings')
    rows = []
    for record in records:
        mask = sum(1 << index for index,key in enumerate(keys) if key in record)
        rows.append([mask, [record[key] for key in keys if key in record]])
    return [keys, rows]


def decode_record_table(table):
    if not isinstance(table, list) or len(table) != 2:
        raise ValueError('invalid record table')
    keys, rows = table
    if not isinstance(keys, list) or any(not isinstance(k,str) for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('invalid record table fields')
    if not isinstance(rows, list):
        raise ValueError('invalid record table rows')
    result = []
    for row in rows:
        if not isinstance(row,list) or len(row) != 2:
            raise ValueError('invalid record table row')
        mask, values = row
        if type(mask) is not int or mask < 0 or mask >> len(keys) or not isinstance(values,list) or mask.bit_count() != len(values):
            raise ValueError('invalid record table presence mask')
        iterator = iter(values)
        result.append({key: next(iterator) for index,key in enumerate(keys) if mask & (1 << index)})
    return result

def encode_symbols(loops,accesses):
    pool=[];intern={}
    def expression(value):
        key=json.dumps(value,separators=(',',':'))
        if key in intern:return intern[key]
        op=value[0]
        literal=2 if op in ('read','call','cast')else len(value)if op in ('constant','slot','array')else 1
        encoded=value[:literal]+[expression(v)for v in value[literal:]]
        index=len(pool);pool.append(encoded);intern[key]=index;return index
    loop_records=[]
    for loop in loops:
        record={**loop,'condition':expression(loop['condition'])}
        if 'increment'in loop:record['increment']=expression(loop['increment'])if loop['increment']is not None else None
        loop_records.append(record)
    access_records=[{**access,'index':expression(access['index'])}for access in accesses]
    return pool,loop_records,access_records

def decode_symbols(pool,loops,accesses):
    expanded=[]
    for index,node in enumerate(pool):
        op=node[0];literal=2 if op in ('read','call','cast')else len(node)if op in ('constant','slot','array')else 1
        if any(not isinstance(child,int)or child<0 or child>=index for child in node[literal:]):raise ValueError('invalid expression DAG reference')
        expanded.append(node[:literal]+[expanded[child]for child in node[literal:]])
    loop_records=[]
    for loop in loops:
        record={**loop,'condition':expanded[loop['condition']]}
        if 'increment'in loop:record['increment']=expanded[loop['increment']]if loop['increment']is not None else None
        loop_records.append(record)
    return loop_records,[{**access,'index':expanded[access['index']]}for access in accesses]
