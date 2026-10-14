"""Global COPY necessary lower bound on a strictly screened forced pure spine.

Unlike fixed-order bounds, only forced arithmetic order is used. GET births
may be delayed and interleaved arbitrarily. Identity-preserving, original-once
COPY-only scope; no aliases/recomputation/rereads/spill. This is a lower bound,
not a scheduler and not an official scoring rule.
"""
from .spine_bounds import spine_capacity_bound
from .verify import _original_header,_reference_distance
from .model import InvalidBlock


def spine_copy_bound(block):
    screen=spine_capacity_bound(block)
    if screen is None or screen['infeasible_under_model']:return None
    nodes=block.instructions;roots={node.index for node in nodes if node.op=='GET'}
    arithmetic=[node for node in nodes if node.op in ('ADD','MULW')]
    first={};last={}
    for stage,node in enumerate(arithmetic):
        for source in set(node.args)&roots:first.setdefault(source,stage);last[source]=stage
    candidates=sorted(roots,key=lambda source:(last[source]-first[source],-first[source],source),reverse=True)
    start=-1;end=len(arithmetic);bound=0;best=None
    for count,source in enumerate(candidates[:block.window-1],1):
        start=max(start,first[source]);end=min(end,last[source]);steps=max(0,end-start-1)
        slack=block.window-count
        required=max(0,(count*steps-count*slack+slack-1)//slack)
        if required>bound:
            bound=required;best={'roots':candidates[:count],'after_first_use_stage':start,
                                'before_last_use_stage':end,'forced_inner_steps':steps,
                                'persistent_identities':count,'age_sum_range':count*slack}
    return {'kind':'forced_spine_persistent_age_sum','copy_lower_bound':bound,'window':block.window,
            'witness':best,'root_count':len(roots),'spine_nodes':len(arithmetic),
            'scope':'all topological orders of this screened forced pure spine; distinct original identities once; COPY-only; no alias/recompute/reread/spill',
            'argument':'k root identities persist across L forced arithmetic steps; each step adds k to age sum; each COPY reduces it by at most W-k; total range <=k(W-k)'}


def check_spine_copy_certificate(data,certificate):
    """Check one selected-root proof on raw JSON, never a scheduler DAG.

    The verifier does not repeat the ranking or trust root-interval summaries.
    It derives the forced chain, first/last uses and witness inequality afresh.
    """
    _original_header(data);rows=data['instructions'];args={};seen=set()
    # Structural proof does not need a second SHA expression graph. Validate
    # its complete pure-input grammar independently, on raw JSON positions.
    fields={'GET':{'id','op','reg','inputs'},'SET':{'id','op','reg','inputs'},
            'ADD':{'id','op','inputs'},'MULW':{'id','op','inputs'}}
    arities={'GET':0,'SET':1,'ADD':2,'MULW':2}
    for index,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('op'),str) or row['op'] not in fields:
            raise InvalidBlock('Pure COPY-free spine required')
        op=row['op']
        if not row.keys()<=fields[op]:raise InvalidBlock('Unknown pure spine instruction field')
        identifier=row.get('id',index)
        if type(identifier) not in (int,str) or identifier in seen:raise InvalidBlock('Invalid/duplicate spine instruction id')
        seen.add(identifier);tokens=row.get('inputs',[])
        if not isinstance(tokens,list) or len(tokens)!=arities[op]:raise InvalidBlock('Invalid spine input arity')
        if op in ('GET','SET') and (not isinstance(row.get('reg'),str) or not row['reg']):raise InvalidBlock('GET/SET register required')
        sources=tuple(index-_reference_distance(token)for token in tokens)
        if any(source<0 for source in sources):raise InvalidBlock('Future/current or unreachable spine reference')
        args[index]=sources
    roots={index for index,row in enumerate(rows)if row['op']=='GET'}
    stores=[index for index,row in enumerate(rows)if row['op']=='SET']
    arithmetic=[index for index,row in enumerate(rows)if row['op'] in ('ADD','MULW')]
    if len(stores)!=1 or not arithmetic:raise InvalidBlock('Single forced output spine required')
    names=[rows[index]['reg'] for index in roots]
    if len(set(names))!=len(names) or rows[stores[0]]['reg'] in names:raise InvalidBlock('Unique disjoint GET/SET registers required')
    if args[stores[0]]!=(arithmetic[-1],):raise InvalidBlock('SET must consume last spine result')
    first={};last={};users={index:set()for index in range(len(rows))}
    for index,sources in args.items():
        for source in sources:users[source].add(index)
    for stage,index in enumerate(arithmetic):
        sources=set(args[index]);previous=arithmetic[stage-1] if stage else None
        if stage and (previous not in sources or not sources-{previous}<=roots):raise InvalidBlock('Arithmetic order is not forced spine')
        if not stage and not sources<=roots:raise InvalidBlock('First spine node must consume roots')
        successor=arithmetic[stage+1] if stage+1<len(arithmetic) else stores[0]
        if users[index]!={successor}:raise InvalidBlock('Spine output has extra consumer')
        for source in sources&roots:first.setdefault(source,stage);last[source]=stage
    if set(first)!=roots:raise InvalidBlock('Uncovered GET in spine certificate')
    window=2**data['bit_width'];claimed=certificate.get('copy_lower_bound')
    if certificate.get('window')!=window or type(claimed) is not int or claimed<0:raise InvalidBlock('Invalid COPY bound/window')
    witness=certificate.get('witness')
    if not claimed:
        return {'verified_global_copy_lower_bound':0,'scope':'distinct original identity COPY-only forced spine'}
    if not isinstance(witness,dict):raise InvalidBlock('Selected-root witness required')
    selected=witness.get('roots')
    if not isinstance(selected,list) or any(type(source) is not int or source not in roots for source in selected):raise InvalidBlock('Invalid witness GET roots')
    count=len(selected)
    if not 0<count<window or len(set(selected))!=count:raise InvalidBlock('Distinct witness roots fewer than window required')
    start=max(first[source]for source in selected);end=min(last[source]for source in selected);steps=max(0,end-start-1)
    if witness.get('after_first_use_stage')!=start or witness.get('before_last_use_stage')!=end or witness.get('forced_inner_steps')!=steps:
        raise InvalidBlock('Root persistent interval mismatch')
    slack=window-count;observed=max(0,(count*steps-count*slack+slack-1)//slack)
    if witness.get('persistent_identities')!=count or witness.get('age_sum_range')!=count*slack:
        raise InvalidBlock('Witness age-sum summary mismatch')
    if claimed>observed:raise InvalidBlock('COPY lower bound exceeds witness inequality')
    return {'verified_global_copy_lower_bound':observed,'scope':'distinct original identity COPY-only forced spine'}
