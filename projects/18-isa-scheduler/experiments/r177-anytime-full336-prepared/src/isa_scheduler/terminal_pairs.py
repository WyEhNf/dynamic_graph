"""Linear optimal order proposal for a narrowly recognized W=4 shape.

Each complete component has two distinct GET roots and m independent ADD/MULW
nodes, each with one dedicated SET. Components use disjoint roots/registers.
Emit m-3 computation/SET pairs, then the final <=3 computations and their
SETs. Generic expiry emission produces max(0,2m-6) root relays. The separate
raw identity and endpoint lower-bound checks certify actual output before
claiming optimality. Other shapes/windows retain the normal portfolio.
"""
from time import perf_counter
from collections import defaultdict
from .local_order import emit_order
from .model import InfeasibleSchedule


def recognize(block,deadline=None):
    if block.window!=4 or block.memory_order!='hazard':return None
    nodes=block.instructions;groups=defaultdict(list);stores={};root_group={}
    for node in nodes:
        if deadline is not None and node.index%256==0 and perf_counter()>=deadline:return None
        if node.op in ('ADD','MULW'):
            roots=tuple(sorted(set(node.args)))
            if len(roots)!=2 or any(nodes[root].op!='GET'for root in roots):return None
            for root in roots:
                if root in root_group and root_group[root]!=roots:return None
                root_group[root]=roots
            groups[roots].append(node.index)
        elif node.op=='SET':
            source=node.args[0]
            if nodes[source].op not in ('ADD','MULW') or source in stores:return None
            stores[source]=node.index
        elif node.op!='GET':return None
    if not groups or set(stores)!={value for values in groups.values()for value in values}:return None
    gets=[node.reg for node in nodes if node.op=='GET'];writes=[node.reg for node in nodes if node.op=='SET']
    if len(set(gets))!=len(gets) or len(set(writes))!=len(writes) or set(gets)&set(writes):return None
    return {'groups':dict(groups),'stores':stores}


def schedule_terminal_pairs(block,*,time_budget_ms=100,plan=None):
    started=perf_counter();deadline=started+time_budget_ms/1000
    plan=recognize(block,deadline) if plan is None else plan
    if plan is None:raise InfeasibleSchedule('terminal_pairs requires complete disjoint two-GET terminal groups, W=4 and hazard memory mode')
    order=[];emitted=set();expected=0
    for roots,values in sorted(plan['groups'].items()):
        order.extend(roots);emitted.update(roots);prefix=max(0,len(values)-3);expected+=max(0,2*len(values)-6)
        for value in values[:prefix]:order.extend((value,plan['stores'][value]))
        order.extend(values[prefix:]);order.extend(plan['stores'][value]for value in values[prefix:])
    order.extend(node.index for node in block.instructions if node.op=='GET' and node.index not in emitted)
    result=emit_order(block,order,deadline=deadline)
    if result is None:raise InfeasibleSchedule('Restricted terminal order failed; no global infeasibility claim')
    result['stats'].update(strategy='terminal_pairs',terminal_pair_groups=len(plan['groups']),
                           terminal_formula_copy_count=expected,elapsed_ms=(perf_counter()-started)*1000)
    result['stats']['terminal_formula_matched']=result['stats']['inserted_copy_count']==expected
    return result
