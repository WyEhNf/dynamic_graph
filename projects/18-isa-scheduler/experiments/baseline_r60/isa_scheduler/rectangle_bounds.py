"""Bounded exact certificate for a pure 20-node shared product rectangle.

The recognizer uses graph structure, never family names. A dependency-closed
2x2 rectangle consists of 8 distinct GET identities, 8 two-input pure products
and 4 two-product merges. In the distinct-identity single-emission model a
capacity-4 schedule is impossible; verify this using the independent age-free
completed-mask DP on the actual projected graph, not a cached outcome.
Unknown/budget exhaustion returns no certificate. Equivalent-value aliasing,
rereads, recomputation or spill are outside this necessary relaxation.
"""
from itertools import combinations
from time import perf_counter
from .closed_subgraph import projection_eligible
from .model import BudgetExceeded,parse_block
from .relaxed_capacity import capacity_oracle


def rectangle_capacity_bound(block, *, time_budget_ms=10, max_pairs=4096):
    if block.window!=4 or len(block.instructions)<20:return None
    started=perf_counter();deadline=started+time_budget_ms/1000
    if not projection_eligible(block):return None
    nodes=block.instructions;cells={}
    for node in nodes:
        if node.index%128==0 and perf_counter()>=deadline:return None
        if node.op not in ('ADD','MULW') or len(set(node.args))!=2:continue
        first,second=(nodes[a] for a in node.args)
        if any(parent.op not in ('ADD','MULW') for parent in (first,second)):continue
        roots=first.args+second.args
        if len(set(roots))!=4 or any(nodes[a].op!='GET' for a in roots):continue
        x=(first.args[0],second.args[0]);y=(first.args[1],second.args[1])
        cells.setdefault(x,{})[y]=node.index
    pairs={};probed=0
    for x,row in cells.items():
        for y1,y2 in combinations(sorted(row),2):
            if probed>=max_pairs or perf_counter()>=deadline:return None
            probed+=1;pair=(y1,y2)
            for previous in pairs.get(pair,()):
                if len(set(previous+x+y1+y2))!=8:continue
                sinks=(cells[previous][y1],cells[previous][y2],row[y1],row[y2])
                indices=set(sinks)
                for sink in sinks:indices.update(nodes[sink].args)
                for index in tuple(indices):indices.update(nodes[index].args)
                if len(indices)!=20:continue
                ordered=sorted(indices);mapping={old:new for new,old in enumerate(ordered)};rows=[]
                for index in ordered:
                    node=nodes[index];item={'id':mapping[index],'op':node.op}
                    if node.reg is not None:item['reg']=node.reg
                    if node.args:item['inputs']=[f't#{mapping[index]-mapping[a]}' for a in node.args]
                    rows.append(item)
                data={'block_id':f'rectangle-{block.block_id}','bit_width':2,'instructions':rows}
                remaining=(deadline-perf_counter())*1000
                if remaining<=0:return None
                try:
                    proof=capacity_oracle(parse_block(data),max_nodes=20,max_states=10000,
                                          time_budget_ms=remaining,depth_first=True)
                except BudgetExceeded:return None
                if not proof['outcome'].startswith('proven'):return None
                return {'kind':'closed_product_rectangle_exact_capacity','infeasible_under_model':True,
                        'window':4,'original_indices':ordered,'projected_node_count':20,
                        'capacity_dp':proof,'recognizer_pairs':probed,
                        'elapsed_ms':(perf_counter()-started)*1000,
                        'scope':'pure unique disjoint GET/SET registers; identity preserving single emission; COPY only; no alias/recompute/reread/spill',
                        'argument':'full schedule projects to this dependency-closed graph; freely retained capacity-4 DP completely exhausted'}
            pairs.setdefault(pair,[]).append(x)
    return None
