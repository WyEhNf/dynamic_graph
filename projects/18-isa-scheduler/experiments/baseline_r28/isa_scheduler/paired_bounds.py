"""Necessary live-slot bound for strictly screened two-input/two-output networks.

Each arithmetic pair consumes the same two distinct logical parents. Both
parents remain until the second partner: first emission changes live count +1,
second -1. Roots have exactly one such consumer pair; terminal outputs each
have exactly one SET. Before the first SET there are no released terminals.
The first partner of its output pair depends on R GET identities, so at that
moment live >= R+1. COPY cannot lower this identity-preserving relaxed capacity.
"""


def paired_network_capacity_bound(block):
    nodes=block.instructions
    if any(node.op not in ("GET","SET","ADD","MULW") for node in nodes):return None
    roots=[node for node in nodes if node.op=="GET"]
    stores=[node for node in nodes if node.op=="SET"]
    arithmetic=[node for node in nodes if node.op in ("ADD","MULW")]
    if not roots or not stores or not arithmetic or len(arithmetic)%2:return None
    read_regs=[node.reg for node in roots];write_regs=[node.reg for node in stores]
    if len(set(read_regs))!=len(read_regs) or len(set(write_regs))!=len(write_regs) or set(read_regs)&set(write_regs):return None
    pairs={};users=[set() for _ in nodes]
    for node in nodes:
        for source in set(node.args):users[source].add(node.index)
        if node.op in ("ADD","MULW"):
            key=tuple(sorted(set(node.args)))
            if len(key)!=2:return None
            pairs.setdefault(key,[]).append(node.index)
    if any(len(group)!=2 for group in pairs.values()):return None
    for node in nodes:
        consumers=users[node.index]
        if node.op=="SET":
            if consumers or nodes[node.args[0]].op not in ("ADD","MULW"):return None
        elif len(consumers)==1 and node.op in ("ADD","MULW") and nodes[next(iter(consumers))].op=="SET":
            pass
        elif len(consumers)==2:
            a,b=sorted(consumers)
            if nodes[a].op not in ("ADD","MULW") or nodes[b].op not in ("ADD","MULW"):return None
            if set(nodes[a].args)!=set(nodes[b].args):return None
        else:return None
    ancestors=[0]*len(nodes);root_bits={node.index:1<<offset for offset,node in enumerate(roots)}
    for node in nodes:
        if node.op=="GET":ancestors[node.index]=root_bits[node.index]
        else:
            for source in set(node.args):ancestors[node.index]|=ancestors[source]
    mandatory=min(ancestors[node.args[0]].bit_count() for node in stores)
    required=mandatory+1
    return {"kind":"paired_two_input_two_output_network_capacity","minimum_register_slots":required,
            "minimum_terminal_root_ancestors":mandatory,"root_count":len(roots),"pair_count":len(pairs),
            "window":block.window,"infeasible_under_model":required>block.window,
            "scope":"strict two-parent paired arithmetic; each internal identity consumed by one pair; terminals each one SET; unique disjoint GET/SET registers; single emission identity-preserving COPY only; no alias folding/recompute/reread/spill",
            "argument":"before first SET, live identities = completed GETs + half-completed arithmetic pairs; first terminal partner requires >=R roots and creates a half pair, hence >=R+1 live"}
