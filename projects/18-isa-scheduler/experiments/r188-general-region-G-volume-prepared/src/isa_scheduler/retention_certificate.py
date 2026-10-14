"""Independent raw-JSON replay of a closed retention-mask proof.

No parsed Block, PreparedGraph, scheduler liveness/ranks/search state is read.
The proof is checked by rebuilding every allowed transition of its mask set.
The full-window last-use bridge and safe dead-output dominance are the stated
mathematical premises. This is not a proof for alias/recompute/reread/spill.
"""
import re


def check_retention_certificate(data, certificate):
    if not isinstance(data, dict) or set(data) != {'block_id', 'bit_width', 'instructions'}:
        raise ValueError('Raw original block schema required')
    if type(data['bit_width']) is not int or not 2 <= data['bit_width'] <= 5:
        raise ValueError('Invalid raw window')
    rows = data['instructions']; n = len(rows); window = 2 ** data['bit_width']
    if not isinstance(rows, list): raise ValueError('Original array required')
    if certificate.get('kind') != 'retention_order_dominance_closed_masks' or certificate.get('node_count') != n or certificate.get('window') != window:
        raise ValueError('Certificate kind/size/window mismatch')
    mode = certificate.get('memory_order')
    if mode not in ('hazard', 'conservative'): raise ValueError('Explicit memory ordering model required')
    dependencies = []; arguments = []; users = [0] * n; reads = {}; last_store = {}; identifiers = set()
    raw_order_deps = []; memory_tail = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict): raise ValueError('Original object required')
        op = row.get('op'); identifier = row.get('id', index)
        if type(identifier) not in (int, str) or identifier in identifiers: raise ValueError('Original unique IDs required')
        identifiers.add(identifier)
        arity = {'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}.get(op)
        if arity is None: raise ValueError('Certificate excludes original COPY/unknown operations')
        fields = {'id', 'op', 'inputs'} | ({'reg'} if op in ('GET', 'SET') else set())
        if set(row) - fields: raise ValueError('Unknown raw original field')
        tokens = row.get('inputs', [])
        if not isinstance(tokens, list) or len(tokens) != arity: raise ValueError('Raw arity mismatch')
        sources = set()
        for token in tokens:
            if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token): raise ValueError('Invalid raw relative reference')
            source = index - int(token[2:])
            if not 0 <= source < index: raise ValueError('Raw reference outside previous originals')
            sources.add(source); users[source] |= 1 << index
        arguments.append(sources); ordering = set(sources); memory_dependencies = set()
        if op in ('GET', 'SET'):
            reg = row.get('reg')
            if not isinstance(reg, str) or not reg: raise ValueError('Register required')
            if mode == 'conservative':
                if memory_tail is not None: memory_dependencies.add(memory_tail)
                memory_tail = index
            else:
                if reg in last_store: memory_dependencies.add(last_store[reg])
                if op == 'GET': reads.setdefault(reg, set()).add(index)
                else:
                    memory_dependencies.update(reads.get(reg, set())); reads[reg] = set(); last_store[reg] = index
        raw_order_deps.append(sorted(memory_dependencies)); ordering.update(memory_dependencies)
        dependencies.append(sum(1 << source for source in ordering))
    if certificate.get('original_order_dependencies') != raw_order_deps:
        raise ValueError('Certificate ordering dependencies are not independently reconstructed raw memory hazards')
    raw_masks = certificate.get('completed_masks_hex')
    if not isinstance(raw_masks, list) or not raw_masks: raise ValueError('Nonempty mask proof required')
    if any(not isinstance(token, str) or not re.fullmatch(r'0x[0-9a-f]+', token) for token in raw_masks):
        raise ValueError('Canonical hexadecimal masks required')
    masks = {int(token, 16) for token in raw_masks}; full = (1 << n) - 1
    if len(masks) != len(raw_masks) or 0 not in masks or full in masks or any(mask & ~full for mask in masks):
        raise ValueError('Duplicate/initial/final/out-of-range mask proof')
    checked_edges = dominated_masks = 0
    for done in masks:
        if any(done >> index & 1 and dependencies[index] & done != dependencies[index] for index in range(n)):
            raise ValueError('Proof mask is not dependency closed')
        live = {index for index in range(n) if done >> index & 1 and users[index] & ~done}
        if len(live) > window: raise ValueError('Proof mask exceeds identity capacity')
        following_all = []; following_dead = []
        for index in range(n):
            if done >> index & 1 or dependencies[index] & done != dependencies[index]: continue
            following = done | 1 << index
            killed = {source for source in arguments[index] if not users[source] & ~following}
            if len(live) == window and not killed: continue
            produced = bool(users[index] & ~following)
            after_count = len(live - killed) + produced
            if after_count > window: continue
            checked_edges += 1; following_all.append(following)
            if not produced: following_dead.append(following)
        if following_dead:
            if not any(following in masks for following in following_dead):
                raise ValueError('Dominant ready dead-output transition is missing')
            dominated_masks += 1
        elif any(following not in masks for following in following_all):
            raise ValueError('Proof is not closed under every safe original transition')
    return {'verified_infeasible_under_original_identity_model': True,
        'verified_mask_count': len(masks), 'verified_safe_edges': checked_edges,
        'dead_output_dominated_masks': dominated_masks, 'window': window,
        'scope': 'raw ordered args and same-register RAW/WAR/WAW; unique original identities once; '
                 'COPY-only; no original COPY, alias/reread/recompute/spill; bridge+dead-output dominance'}
