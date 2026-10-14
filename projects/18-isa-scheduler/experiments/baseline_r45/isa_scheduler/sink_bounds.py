"""Lift a mandatory-spine capacity obstruction from a pure SET ancestor cone.

Closure outside nodes can be deleted without increasing remaining reference
ages in the identity-preserving COPY-only model. Global register screening is
required; no GET/SET aliasing or hidden ordering dependencies are accepted.
"""
from .closed_subgraph import projection_eligible
from .model import Block,Instruction
from .spine_bounds import spine_capacity_bound


def sink_spine_projections(block):
    if not projection_eligible(block):return
    nodes=block.instructions
    for store in nodes:
        if store.op!="SET":continue
        selected={store.index};current=store.args[0]
        valid=True
        while True:
            node=nodes[current]
            if node.op not in ("ADD","MULW"):valid=False;break
            selected.add(current)
            sources=set(node.args)
            if any(nodes[source].op not in ("GET","ADD","MULW") for source in sources):valid=False;break
            selected.update(source for source in sources if nodes[source].op=="GET")
            previous=[source for source in sources if nodes[source].op in ("ADD","MULW")]
            if len(previous)>1:valid=False;break
            if not previous:break
            current=previous[0]
        if not valid:continue
        indices=sorted(selected);mapping={old:new for new,old in enumerate(indices)}
        projected=Block(f"sink-{block.block_id}-{store.index}",block.bit_width,tuple(
            Instruction(mapping[index],nodes[index].original_id,nodes[index].op,
                        tuple(mapping[source] for source in nodes[index].args),nodes[index].reg,()) for index in indices))
        yield store.index,indices,projected


def sink_spine_capacity_bound(block):
    for terminal,indices,projected in sink_spine_projections(block):
        certificate=spine_capacity_bound(projected)
        if certificate and certificate["infeasible_under_model"]:
            return {**certificate,"kind":"closed_sink_mandatory_spine_capacity",
                    "terminal_original_index":terminal,"projection_node_count":len(indices),
                    "projection_scope":"pure dependency-closed SET ancestor cone; unique disjoint global registers; deleting outside originals/relays only shortens remaining ages; identity preservation required"}
    return None
