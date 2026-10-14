"""Fixed40 branching/external-context blocks, independent of candidate code."""


def generated(case_id):
    family = case_id // 10; variant = case_id % 5; external = (case_id % 10) // 5
    pairs = (('fork3','padded5'),('padded5','padded5'),('fork_unary4','comb5'),('comb5','padded6'))
    bits = 3 if variant in (2,3) else 2
    rows=[]

    def append(op, args=(), reg=None):
        index=len(rows); row={'id':f'branch-{case_id}-original-{index}', 'op':op}
        if reg is not None: row['reg']=reg
        if args:
            sources=tuple(reversed(args)) if (index+case_id)%2 else tuple(args)
            row['inputs']=[f't#{index-source}' for source in sources]
        rows.append(row); return index

    if variant==4:
        append('GET',reg='unused_before')
        other=append('GET',reg='other_read'); append('SET',(other,),reg='other_write')
    ext=append('GET',reg='outside_read') if external else None
    prefix=list(range(len(rows)))

    def side(shape,label):
        begin=len(rows); a=append('GET',reg=label+'a'); b=append('GET',reg=label+'b')
        first='MULW' if case_id%2 else 'ADD'; second='ADD' if case_id%2 else 'MULW'
        if shape=='fork3': result=append(first,(a,b))
        elif shape=='fork_unary4':
            value=append(first,(a,b)); result=append(second,(value,value))
        elif shape in ('padded5','padded6'):
            va=append(first,(a,a)); vb=append(second,(b,b)); result=append('ADD',(va,vb))
            if shape=='padded6': result=append('MULW',(result,result))
        elif shape=='comb5':
            value=append(first,(a,b)); c=append('GET',reg=label+'c'); result=append(second,(value,c))
        else: raise ValueError(shape)
        return result,list(range(begin,len(rows)))

    left,a=side(pairs[family][0],'left_'); right,b=side(pairs[family][1],'right_')
    parent=append('ADD',(left,right)); append('SET',(parent,),reg='pair_write')
    if ext is not None: append('SET',(ext,),reg='outside_write')
    if variant==4: append('GET',reg='unused_after')
    data={'block_id':f'fixed-branch-context-{case_id}','bit_width':bits,'instructions':rows}
    by_root={left:a,right:b}
    roots=[parent-int(token[2:]) for token in rows[parent]['inputs']]
    sides=[by_root[root] for root in roots]
    return {'case_id':case_id,'family':pairs[family],'variant':variant,'external_count':external,
            'input':data,'parent':parent,'side_orders':sides,'baseline_order':list(range(len(rows))),
            'prefix':prefix,'suffix':list(range(parent+1,len(rows)))}


def interleavings(left,right):
    """All merges preserve each fixed side's original order; no candidate use."""
    def visit(i,j,prefix):
        if i==len(left) and j==len(right): yield prefix; return
        if i<len(left): yield from visit(i+1,j,prefix+[left[i]])
        if j<len(right): yield from visit(i,j+1,prefix+[right[j]])
    return visit(0,0,[])
