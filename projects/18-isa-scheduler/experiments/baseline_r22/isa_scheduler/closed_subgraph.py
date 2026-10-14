"""Dependency-closed projections for narrowly scoped obstruction research.

On pure identity-preserving COPY-only DAGs with unique disjoint GET/SET
registers, a valid full schedule projects to a closed subgraph schedule: delete
unselected original nodes and their relays; retained references only get
shorter. Thus exact model infeasibility of a closed subgraph is necessary for
full model feasibility. It says nothing about rewrites/recompute/rereads/spill.
"""
from .model import parse_block


def projection_eligible(block):
    nodes=block.instructions
    if any(node.op not in ("GET","SET","ADD","MULW") for node in nodes):return False
    reads=[node.reg for node in nodes if node.op=="GET"]
    writes=[node.reg for node in nodes if node.op=="SET"]
    return (len(reads)==len(set(reads)) and len(writes)==len(set(writes))
            and not set(reads)&set(writes) and not any(node.order_deps for node in nodes))


def closed_subset_data(data,indices):
    block=parse_block(data)
    if not projection_eligible(block):raise ValueError("Unique disjoint registers and pure graph required")
    selected=set(indices)
    if any(type(index) is not int or not 0<=index<len(block.instructions) for index in selected):
        raise ValueError("Invalid original node index")
    if any(not set(block.instructions[index].args)<=selected for index in selected):
        raise ValueError("Subset is not dependency closed")
    mapping={index:rank for rank,index in enumerate(sorted(selected))}
    rows=[]
    for index in sorted(selected):
        node=block.instructions[index]
        row={"id":node.original_id,"op":node.op}
        if node.reg is not None:row["reg"]=node.reg
        if node.args:row["inputs"]=[f"t#{mapping[index]-mapping[source]}" for source in node.args]
        rows.append(row)
    return {"block_id":f"closed-{block.block_id}","bit_width":block.bit_width,"instructions":rows}


def candidate_closures(block,max_nodes=16,max_candidates=60):
    if not projection_eligible(block):return []
    masks=[]
    for node in block.instructions:
        mask=1<<node.index
        for source in set(node.args):mask|=masks[source]
        masks.append(mask)
    probes=[node.index for node in block.instructions if node.op not in ("GET","SET")
            and masks[node.index].bit_count()<=max_nodes][:128]
    candidates=set()
    for offset,a in enumerate(probes):
        candidates.add(masks[a])
        for b in probes[offset+1:]:
            combined=masks[a]|masks[b]
            if combined.bit_count()<=max_nodes:candidates.add(combined)
    candidates=[mask for mask in candidates if mask.bit_count()>=block.window+2]
    def priority(mask):
        counts={}
        for index,node in enumerate(block.instructions):
            if mask>>index&1:
                for source in set(node.args):counts[source]=counts.get(source,0)+1
        shared=sum(count>1 for count in counts.values())
        return (-shared,mask.bit_count(),mask)
    candidates.sort(key=priority)
    return [tuple(index for index in range(len(masks)) if mask>>index&1) for mask in candidates[:max_candidates]]
