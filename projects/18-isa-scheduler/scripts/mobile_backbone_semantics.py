"""Independent flat canonical-symbol and configurable integer interpretations.

No production parser/state/op evaluator imports. Canonical opaque expression
IDs are interned by exact tuple keys, avoiding recursion and digest collisions
on long DAGs. COPY is transparent; ADD/MULW operand order remains exact.
"""
import re


def check_semantics(data, candidate):
    originals = data['instructions']
    physical = candidate['output']['optimized_instructions']
    order = candidate['original_order']
    if len(order) != len(originals) or set(order) != set(range(len(originals))):
        raise ValueError('Missing original identity witness')
    if candidate['output']['block_id'] != data['block_id']:
        raise ValueError('Different block ID')
    width = 1 << data['bit_width']
    registers = sorted({row['reg'] for row in originals if row['op'] in ('GET', 'SET')})
    symbols = {}

    def intern(key):
        if key not in symbols:
            symbols[key] = len(symbols)
        return symbols[key]

    def evaluate(rows, memory, original_identity_order, local_semantics, is_output):
        values, produced, cursor, writes = [], {}, 0, []
        bits, signed = local_semantics if local_semantics is not None else (None, None)
        def wrap(value):
            value %= 1 << bits
            return value - (1 << bits) if signed and value >= 1 << (bits - 1) else value
        for position, row in enumerate(rows):
            op = row['op']
            if op not in ('COPY', 'GET', 'SET', 'ADD', 'MULW') or (not is_output and op == 'COPY'):
                raise ValueError('Unsupported operation in independent evaluator')
            tokens = [row.get('source')] if op == 'COPY' else row.get('inputs', [])
            if not isinstance(tokens, list) or len(tokens) != {'COPY': 1, 'GET': 0, 'SET': 1, 'ADD': 2, 'MULW': 2}[op]:
                raise ValueError('Independent operation arity')
            incoming = []
            for token in tokens:
                if not isinstance(token, str) or not re.fullmatch(r't#[1-9][0-9]*', token):
                    raise ValueError('Independent reference syntax')
                distance = int(token[2:])
                if not 1 <= distance <= position or (is_output and distance > width):
                    raise ValueError('Independent reference distance')
                value = values[position - distance]
                if value is None:
                    raise ValueError('SET does not produce an identity/value')
                incoming.append(value)
            if op == 'COPY':
                value = incoming[0]
            else:
                if cursor >= len(original_identity_order):
                    raise ValueError('Too many original operations')
                identity = original_identity_order[cursor]
                cursor += 1
                if op == 'GET':
                    value = memory[row['reg']]
                elif op == 'SET':
                    value = None
                    memory[row['reg']] = incoming[0]
                    writes.append((identity, row['reg'], incoming[0]))
                elif local_semantics is None:
                    value = intern((op, incoming[0], incoming[1]))
                else:
                    value = wrap(incoming[0] + incoming[1] if op == 'ADD' else incoming[0] * incoming[1])
                produced[identity] = value
            values.append(value)
        if cursor != len(original_identity_order):
            raise ValueError('Incomplete independent evaluation')
        return produced, memory, sorted(writes)

    initial_symbols = {register: intern(('INITIAL', register)) for register in registers}
    original = evaluate(originals, dict(initial_symbols), range(len(originals)), None, False)
    emitted = evaluate(physical, dict(initial_symbols), order, None, True)
    if original != emitted:
        raise AssertionError('Exact opaque canonical-symbol original/SET/register mismatch')
    numeric_checks = []
    for bits, signed in ((8, True), (16, False), (32, True)):
        for seed in (19001, 19002):
            def wrap(value):
                value %= 1 << bits
                return value - (1 << bits) if signed and value >= 1 << (bits - 1) else value
            initial = {register: wrap(seed - 29 * index) for index, register in enumerate(registers)}
            original = evaluate(originals, dict(initial), range(len(originals)), (bits, signed), False)
            emitted = evaluate(physical, dict(initial), order, (bits, signed), True)
            if original != emitted:
                raise AssertionError('Independent integer original/SET/register mismatch')
            numeric_checks.append({'bits': bits, 'signed': signed, 'seed': seed})
    return {'independent_exact_opaque_symbols': True, 'canonical_symbol_count': len(symbols),
            'independent_integer_checks': numeric_checks,
            'all_original_values_and_original_SET_writes_and_registers': True,
            'scope': 'Configured local integers, not claimed official arithmetic widths. Raw identity/hazards checked separately.'}
