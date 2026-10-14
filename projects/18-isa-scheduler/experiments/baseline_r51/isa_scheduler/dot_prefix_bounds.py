"""Necessary capacity certificate for three shared three-product prefixes.

This is graph matching, not recognition by application names. Selected pure
prefixes retain all 27 originals and their eight-input arithmetic dependencies.
Complete independent age-free DP decides the actual closed projection; unknown
or exhausted budgets never prove infeasibility. Distinct identities only.
"""
from itertools import combinations
from time import perf_counter
from .closed_subgraph import projection_eligible
from .model import BudgetExceeded,parse_block
from .relaxed_capacity import capacity_oracle


def shared_prefix_capacity_bound(block, *, time_budget_ms=15,max_combinations=128):
    if block.window!=4 or len(block.instructions)<27:return None
    started=perf_counter();deadline=started+time_budget_ms/1000
    if not projection_eligible(block):return None
    nodes=block.instructions;groups={}
    for node in nodes:
        if node.index%128==0 and perf_counter()>=deadline:return None
        if node.op not in ('ADD','MULW') or len(set(node.args))!=2:continue
        earlier,last=(nodes[a] for a in node.args)
        if earlier.op not in ('ADD','MULW') or len(set(earlier.args))!=2:continue
        products=tuple(nodes[a] for a in earlier.args)+(last,)
        if any(p.op not in ('ADD','MULW') for p in products):continue
        if any(nodes[a].op!='GET' for p in products for a in p.args):continue
        shared=tuple(p.args[0] for p in products);private=tuple(p.args[1] for p in products)
        if len(set(shared+private))!=6:continue
        groups.setdefault(shared,[]).append((private,node.index,earlier.index,tuple(p.index for p in products)))
    attempted=0
    for shared,rows in groups.items():
        for selected in combinations(rows,3):
            if attempted>=max_combinations or perf_counter()>=deadline:return None
            attempted+=1
            if len(set(shared+tuple(a for item in selected for a in item[0])))!=12:continue
            indices=set(shared)
            for private,merge,earlier,products in selected:indices.update((*private,merge,earlier,*products))
            if len(indices)!=27:continue
            ordered=sorted(indices);mapping={old:new for new,old in enumerate(ordered)};instructions=[]
            for index in ordered:
                node=nodes[index];item={'id':mapping[index],'op':node.op}
                if node.reg is not None:item['reg']=node.reg
                if node.args:item['inputs']=[f't#{mapping[index]-mapping[a]}' for a in node.args]
                instructions.append(item)
            projected={'block_id':f'prefix-{block.block_id}','bit_width':2,'instructions':instructions}
            remaining=(deadline-perf_counter())*1000
            if remaining<=0:return None
            try:proof=capacity_oracle(parse_block(projected),max_nodes=27,max_states=10000,
                                      time_budget_ms=remaining,depth_first=True)
            except BudgetExceeded:return None
            if not proof['outcome'].startswith('proven'):return None
            return {'kind':'closed_shared_three_product_prefix_exact_capacity','infeasible_under_model':True,
                    'window':4,'original_indices':ordered,'projected_node_count':27,'capacity_dp':proof,
                    'recognizer_combinations':attempted,'elapsed_ms':(perf_counter()-started)*1000,
                    'scope':'pure unique disjoint GET/SET; distinct original identities once; COPY only; no alias/recompute/reread/spill',
                    'argument':'full schedule projects to this closed graph; independent capacity-4 completed-mask DP completely exhausted'}
    return None
