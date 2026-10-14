"""Necessary identity capacity bound from an undirected dependency minor.

A topological order with live frontier <=W gives path-decomposition bags
live-before + current node of size <=W+1, hence treewidth <=W. Minimum degree
of every minor lower-bounds treewidth. A minor with min degree >W therefore
refutes only original-once, distinct-identity retention, COPY-only schedules.
Ignoring register ordering weakens this necessary bound safely.

This module is offline research only, not enabled by the default optimizer.
"""
import hashlib,heapq,json
from time import perf_counter
from .model import InvalidBlock
from .verify import _original_header,inspect,_reference_distance


def raw_graph(data):
    """Independent original JSON validation; no parsed scheduler DAG/state."""
    _original_header(data);rows=data['instructions'];inspect(rows)
    adj={index:set() for index in range(len(rows))}
    for index,row in enumerate(rows):
        tokens=[row['source']] if row['op']=='COPY' else row.get('inputs',[])
        for token in tokens:
            source=index-_reference_distance(token)
            adj[index].add(source);adj[source].add(index)
    return adj


def input_hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def contraction_bound(data,*,time_budget_ms=100,max_nodes=8192,policy='common'):
    if time_budget_ms<=0 or max_nodes<1 or policy not in ('common','degree'):raise ValueError('Invalid contraction budget/policy')
    started=perf_counter();deadline=started+time_budget_ms/1000
    if len(data.get('instructions',[]))>max_nodes:return None
    adj=raw_graph(data);window=2**data['bit_width'];actions=[];bound=prefix=0
    heap=[(len(neighbors),index) for index,neighbors in adj.items()];heapq.heapify(heap)
    outcome='complete_lower_bound_only'
    while adj:
        if perf_counter()>=deadline:outcome='time_budget_exhausted_lower_bound_only';break
        while heap:
            degree,vertex=heapq.heappop(heap)
            if vertex in adj and len(adj[vertex])==degree:break
        else:raise AssertionError('Missing live degree heap entry')
        if degree>bound:bound=degree;prefix=len(actions)
        if bound>window:outcome='infeasible_under_identity_model';break
        if not degree:actions.append(['delete',vertex]);del adj[vertex];continue
        if policy=='common':
            target=min(adj[vertex],key=lambda index:(len(adj[vertex]&adj[index]),len(adj[index]),index))
        else:target=min(adj[vertex],key=lambda index:(len(adj[index]),index))
        neighbors=adj[vertex]-{target};adj[target].update(neighbors);adj[target].discard(vertex)
        for neighbor in neighbors:
            adj[neighbor].discard(vertex);adj[neighbor].add(target)
            heapq.heappush(heap,(len(adj[neighbor]),neighbor))
        heapq.heappush(heap,(len(adj[target]),target));actions.append(['contract',vertex,target]);del adj[vertex]
    return {'kind':'dependency_minor_min_degree','input_sha256':input_hash(data),'window':window,
            'lower_bound':bound,'outcome':outcome,'policy':policy,'actions':actions[:prefix],
            'contractions_scanned':len(actions),'bound_prefix':prefix,'max_nodes':max_nodes,
            'elapsed_ms':(perf_counter()-started)*1000,'time_budget_ms':time_budget_ms,
            'proof_scope':'distinct original identities computed once; COPY-only; no alias/recompute/reread/spill'}


def check_contraction_certificate(data,certificate):
    """Replay certificate on fresh raw JSON; independently measure its minor.

    Only this result, never the heuristic's outcome string, licenses rejection.
    The search heap/choice/ranks/window-live state is neither read nor trusted.
    """
    adj=raw_graph(data);window=2**data['bit_width']
    if certificate.get('input_sha256')!=input_hash(data) or certificate.get('window')!=window:
        raise InvalidBlock('Minor certificate input/window mismatch')
    actions=certificate.get('actions')
    if not isinstance(actions,list):raise InvalidBlock('Minor action list required')
    original=adj;parent={index:index for index in original};members={index:{index} for index in original}
    active=set(original)
    def representative(index):
        while parent[index]!=index:
            parent[index]=parent[parent[index]];index=parent[index]
        return index
    for action in actions:
        if not isinstance(action,list) or len(action) not in (2,3):raise InvalidBlock('Invalid minor action')
        kind,vertex=action[:2]
        if type(vertex) is not int or vertex not in active:raise InvalidBlock('Unknown minor vertex')
        if kind=='delete' and len(action)==2:
            active.remove(vertex)
        elif kind=='contract' and len(action)==3:
            target=action[2]
            if type(target) is not int or target not in active or target==vertex:raise InvalidBlock('Unknown/self contraction target')
            if not any(representative(neighbor)==target for member in members[vertex] for neighbor in original[member]):
                raise InvalidBlock('Contraction must use a current edge')
            # Union original branch sets, independently of search adjacency
            # mutations. Reconstruct final simple minor from original edges.
            parent[vertex]=target;members[target].update(members.pop(vertex));active.remove(vertex)
        else:raise InvalidBlock('Unknown minor action')
    adj={index:set() for index in active}
    for left,neighbors in original.items():
        left2=representative(left)
        if left2 not in active:continue
        for right in neighbors:
            right2=representative(right)
            if right2 in active and left2!=right2:adj[left2].add(right2)
    observed=min(map(len,adj.values()),default=0)
    claimed=certificate.get('lower_bound')
    if type(claimed) is not int or claimed<0 or claimed>observed:raise InvalidBlock('Minor degree claim not established')
    return {'verified_min_degree':observed,'window':window,'infeasible_under_identity_model':observed>window,
            'minor_vertices':len(adj),'actions_replayed':len(actions)}
