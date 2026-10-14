"""All-order per-identity COPY bound from distinct original consumer counts.

If a value has u distinct original consumers, birth-to-last-use spans >=u
original emissions. With c relays of this identity, u+c <= (c+1)W. Thus
c>=ceil((u-W)/(W-1)). Sum per identity: inserted COPY relays have one owner.
Strict original-once/distinct-identity/COPY-only model, not alias/recompute.
"""
from .raw_pure import dependencies
from .model import InvalidBlock


def consumer_copy_bound(block):
    nodes=block.instructions
    if any(node.op not in ('GET','SET','ADD','MULW') for node in nodes):return None
    get_names=[node.reg for node in nodes if node.op=='GET'];set_names=[node.reg for node in nodes if node.op=='SET']
    if len(set(get_names))!=len(get_names) or len(set(set_names))!=len(set_names) or set(get_names)&set(set_names):return None
    counts=[0]*len(nodes)
    for node in nodes:
        for source in set(node.args):counts[source]+=1
    window=block.window
    contributions=[max(0,(count-window+window-2)//(window-1))for count in counts]
    return {'kind':'distinct_consumer_identity_relay_sum','window':window,'copy_lower_bound':sum(contributions),
            'positive_identities':sum(value>0 for value in contributions),
            'scope':'all topological orders; unique disjoint GET/SET registers; original identities once; pure COPY-free input; COPY-only output; no aliases/recompute/reread/spill',
            'argument':'u distinct original users plus c own relays span at least u+c physical emissions; c>=ceil((u-W)/(W-1)); each relay has one identity owner'}


def check_consumer_copy_certificate(data,certificate):
    args=dependencies(data);rows=data['instructions']
    gets=[row['reg']for row in rows if row['op']=='GET'];stores=[row['reg']for row in rows if row['op']=='SET']
    if len(set(gets))!=len(gets) or len(set(stores))!=len(stores) or set(gets)&set(stores):raise InvalidBlock('Unique disjoint registers required')
    consumers=[set()for _ in rows]
    for index,sources in enumerate(args):
        for source in sources:consumers[source].add(index)
    window=2**data['bit_width'];observed=sum(max(0,(len(users)-window+window-2)//(window-1))for users in consumers)
    claimed=certificate.get('copy_lower_bound')
    if certificate.get('window')!=window or type(claimed) is not int or not 0<=claimed<=observed:
        raise InvalidBlock('Consumer-count COPY bound not established')
    return {'verified_global_copy_lower_bound':observed,'scope':'distinct original identity COPY-only pure graph'}
