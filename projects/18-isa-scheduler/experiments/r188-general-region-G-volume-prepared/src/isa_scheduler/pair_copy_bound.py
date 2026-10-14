"""Global COPY bound for two-root terminal consumer groups.

Between the first and last of m computations using both roots, both roots
persist. At most W-2 prior results can remain unstored before the last use;
at least max(0,m-1-(W-2)) dedicated SETs occur inside that interval. Thus
L >= m-2+max(0,m-1-(W-2)) other original instructions persist between uses.
The age sum increases by 2 per step; a root relay reduces it by <=W-2.
Immediately after the first common computation both roots have ages >=2,3;
immediately before the last they have distinct ages <=W, so the difference
is <=(2W-1)-5=2(W-3). This allocates only those two roots' COPYs.
Disjoint pairs replace their individual consumer bounds; all others retain
individual bounds. This is original-once/COPY-only, not algebraic aliasing.
"""
from collections import Counter,defaultdict
from .consumer_copy_bound import consumer_copy_bound
from .raw_pure import dependencies
from .model import InvalidBlock


def _root_pair_bound(count,window):
    slack=window-2;steps=max(0,count-2)+max(0,count-1-slack)
    return max(0,(2*steps-2*(window-3)+slack-1)//slack),steps


def pair_copy_bound(block):
    base=consumer_copy_bound(block)
    if base is None:return None
    nodes=block.instructions;users=[set()for _ in nodes];groups=defaultdict(int)
    for node in nodes:
        for source in set(node.args):users[source].add(node.index)
    for node in nodes:
        if node.op not in ('ADD','MULW') or len(set(node.args))!=2:continue
        pair=tuple(sorted(node.args))
        if any(nodes[source].op!='GET' for source in pair):continue
        if len(users[node.index])!=1 or nodes[next(iter(users[node.index]))].op!='SET':continue
        groups[pair]+=1
    window=block.window;individual=[max(0,(len(user)-window+window-2)//(window-1))for user in users]
    proposals=[]
    for pair,count in groups.items():
        bound,steps=_root_pair_bound(count,window);gain=bound-sum(individual[root]for root in pair)
        if gain>0:proposals.append((gain,pair,count,steps,bound))
    used=set();selected=[];total=base['copy_lower_bound']
    for gain,pair,count,steps,bound in sorted(proposals,reverse=True):
        if used.intersection(pair):continue
        used.update(pair);total+=gain
        selected.append({'roots':list(pair),'terminal_computations':count,'forced_inner_originals':steps,'root_pair_copy_lower_bound':bound,'age_sum_endpoint_difference':2*(window-3)})
    if not selected:return None
    return {'kind':'disjoint_terminal_root_pairs_age_sum','copy_lower_bound':total,'window':window,'pairs':selected,'endpoint_refined':True,
            'scope':'all topological orders; unique disjoint GET/SET registers; original identities once; pure COPY-free input; COPY-only; no aliases/recompute/reread/spill',
            'argument':'two roots persist between terminal common computations; limited unstored outputs force SETs inside interval; selected root pairs are disjoint'}


def check_pair_copy_certificate(data,certificate):
    # Rebuild raw grammar, distinct users, register assumptions and root groups.
    args=dependencies(data);rows=data['instructions'];window=2**data['bit_width']
    gets=[row['reg']for row in rows if row['op']=='GET'];stores=[row['reg']for row in rows if row['op']=='SET']
    if len(set(gets))!=len(gets) or len(set(stores))!=len(stores) or set(gets)&set(stores):raise InvalidBlock('Unique disjoint registers required')
    users=[set()for _ in rows]
    for user,sources in enumerate(args):
        for source in sources:users[source].add(user)
    groups=Counter()
    for index,row in enumerate(rows):
        if row['op'] not in ('ADD','MULW') or len(set(args[index]))!=2:continue
        roots=tuple(sorted(args[index]))
        if all(rows[root]['op']=='GET'for root in roots) and len(users[index])==1 and rows[next(iter(users[index]))]['op']=='SET':groups[roots]+=1
    individual=[max(0,(len(user)-window+window-2)//(window-1))for user in users]
    observed=sum(individual);selected=certificate.get('pairs');used=set();refined=certificate.get('endpoint_refined',False)
    if type(refined)is not bool:raise InvalidBlock('Endpoint proof mode must be boolean')
    if not isinstance(selected,list):raise InvalidBlock('Root-pair witnesses required')
    for witness in selected:
        if not isinstance(witness,dict) or not isinstance(witness.get('roots'),list):raise InvalidBlock('Root-pair witness required')
        roots=witness['roots']
        if len(roots)!=2 or any(type(root)is not int for root in roots) or roots!=sorted(set(roots)) or used.intersection(roots):raise InvalidBlock('Disjoint ordered root pairs required')
        count=groups[tuple(roots)]
        if not count:raise InvalidBlock('Terminal common root group missing')
        # Independent integer inequality, without proposal ranking/helper state.
        slack=window-2;steps=max(0,count-2)+max(0,count-1-slack)
        age_range=2*(window-3) if refined else 2*slack
        bound=max(0,(2*steps-age_range+slack-1)//slack)
        if 'age_sum_endpoint_difference' in witness and witness['age_sum_endpoint_difference']!=age_range:raise InvalidBlock('Root age endpoint difference mismatch')
        if witness.get('terminal_computations')!=count or witness.get('forced_inner_originals')!=steps or witness.get('root_pair_copy_lower_bound')!=bound:raise InvalidBlock('Terminal group summary mismatch')
        gain=bound-sum(individual[root]for root in roots)
        if gain<=0:raise InvalidBlock('Pair must strengthen individual identity bound')
        used.update(roots);observed+=gain
    claimed=certificate.get('copy_lower_bound')
    if certificate.get('window')!=window or type(claimed)is not int or not 0<=claimed<=observed:raise InvalidBlock('Terminal pair COPY bound not established')
    return {'verified_global_copy_lower_bound':observed,'scope':'distinct original identity COPY-only pure graph; disjoint root-pair age sums'}
