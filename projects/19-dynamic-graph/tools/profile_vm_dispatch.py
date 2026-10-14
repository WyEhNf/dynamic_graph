"""Independent bounded small-matrix trace of original PROGRAM dispatches.

This measures executed opcode coverage, not C++ performance. No runtime change.
"""
import argparse
from collections import Counter
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct

from metadata_wire import OPCODE_NAMES, decode_instruction

CONTROL = {'JUMP', 'JZ', 'JNZ', 'RETURN'}


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def read_program(path):
    text = Path(path).read_text(encoding='utf-8')
    header, body = text.split('\nPROGRAM\n')
    schema = header.splitlines()[0]
    if schema not in ('DYNCHOL 2', 'DYNCHOL 3'):
        raise ValueError('only uncompressed Metadata v2/v3 supported')
    fields = dict(line.split('=', 1) for line in header.splitlines()[1:] if '=' in line)
    rows = []
    for line in body.splitlines():
        if not line.strip():
            continue
        parts = (decode_instruction(line) if schema == 'DYNCHOL 3' else line).split()
        if parts[0] not in OPCODE_NAMES or len(parts) not in (1, 2):
            raise ValueError('invalid opcode record')
        rows.append((parts[0], float(parts[1]) if len(parts) == 2 else 0.0))
    return fields, rows


def load_pairs(rows):
    """Match the isolated candidate's full-CFG, disjoint LOAD discovery."""
    entries = {0}
    for pc, (op, arg) in enumerate(rows):
        if op in {'JUMP', 'JZ', 'JNZ'}:
            if not math.isfinite(arg) or not arg.is_integer() or not 0 <= arg < len(rows):
                return set(), False
            entries.add(int(arg))
        if op in CONTROL and pc + 1 < len(rows):
            entries.add(pc + 1)
    starts = set()
    pc = 0
    while pc + 1 < len(rows):
        if rows[pc][0] == rows[pc + 1][0] == 'LOAD' and pc + 1 not in entries:
            starts.add(pc)
            pc += 2
        else:
            pc += 1
    return starts, True


def matrix_at(path, index, max_n=16):
    with Path(path).open('rb') as stream:
        count = struct.unpack('<I', stream.read(4))[0]
        if not 0 <= index < count:
            raise ValueError('matrix index outside stream')
        for current in range(index + 1):
            n = struct.unpack('<I', stream.read(4))[0]
            if current == index:
                if not 3 <= n <= max_n:
                    raise ValueError('selected matrix exceeds small-trace envelope')
                payload = stream.read(8 * n * n)
                if len(payload) != 8 * n * n:
                    raise ValueError('truncated selected matrix')
                return n, payload
            stream.seek(8 * n * n, 1)


def trace(fields, rows, n, values, *, block=32, limit=1000000):
    if type(limit) is not int or limit < 1:
        raise ValueError('positive finite instruction limit required')
    slots = [0.0] * int(fields['slots'])
    initialized = set()
    def checked_index(arg, bound):
        if not math.isfinite(arg) or not arg.is_integer() or not 0 <= arg < bound:
            raise ValueError('invalid index')
        return int(arg)
    shape = checked_index(float(fields['shape_slot']), len(slots))
    slots[shape] = float(n)
    initialized.add(shape)
    block_slot = int(fields.get('block_slot', -1))
    if block_slot >= 0:
        slots[checked_index(float(block_slot), len(slots))] = float(block)
        initialized.add(block_slot)
    stack, output = [], [0.0] * len(values)
    starts, classification_valid = load_pairs(rows)
    opcounts, pccounts, bigrams = Counter(), Counter(), Counter()
    steps = pairs = pc = 0
    previous = None
    # Use the platform C functions for explicit FMA and IEEE min/max.
    library = ctypes.CDLL('ucrtbase.dll')
    native = {}
    for name, arity in (('fma', 3), ('fmin', 2), ('fmax', 2)):
        function = getattr(library, name)
        function.argtypes = [ctypes.c_double] * arity
        function.restype = ctypes.c_double
        native[name] = function
    while True:
        if steps >= limit:
            raise ValueError('instruction trace budget exhausted')
        if not 0 <= pc < len(rows):
            raise ValueError('program ended without RETURN')
        at = pc
        op, arg = rows[pc]
        pc += 1
        steps += 1
        opcounts[op] += 1
        pccounts[at] += 1
        if previous is not None:
            bigrams[rows[previous][0] + ' ' + op] += 1
            if previous in starts and at == previous + 1:
                pairs += 1
        previous = at
        if op == 'CONST': stack.append(arg)
        elif op == 'LOAD':
            slot = checked_index(arg, len(slots))
            if slot not in initialized: raise ValueError('uninitialized scalar')
            stack.append(slots[slot])
        elif op == 'STORE':
            slot = checked_index(arg, len(slots)); slots[slot] = stack.pop(); initialized.add(slot)
        elif op == 'UNINIT': initialized.discard(checked_index(arg, len(slots)))
        elif op == 'READ':
            array = values if arg == 0 else output
            stack.append(array[checked_index(stack.pop(), len(array))])
        elif op == 'WRITE':
            value = stack.pop(); index = checked_index(stack.pop(), len(output))
            if not math.isfinite(value): raise ValueError('nonfinite output')
            output[index] = value
        elif op == 'DUP': stack.append(stack[-1])
        elif op == 'POP': stack.pop()
        elif op in {'JUMP', 'JZ', 'JNZ'}:
            taken = op == 'JUMP' or (stack.pop() == 0) == (op == 'JZ')
            if taken: pc = checked_index(arg, len(rows))
        elif op == 'RETURN':
            if stack.pop() != 0 or stack: raise ValueError('invalid source return')
            return output, {'steps': steps, 'opcode_counts': dict(opcounts),
                'pc_counts': dict(pccounts), 'dynamic_bigram_counts': dict(bigrams),
                'load_pair_classification_valid': classification_valid,
                'static_disjoint_load_pairs': len(starts), 'executed_load_pairs': pairs,
                'possible_dispatch_removal_fraction': pairs / steps,
                'scope': 'Executed original small PROGRAM; fraction is not CPU speedup.'}
        elif op in {'NEG', 'NOT', 'BOOL', 'TRUNC', 'SQRT', 'ABS'}:
            x = stack.pop()
            if op == 'NEG': x = -x
            elif op == 'NOT': x = float(x == 0)
            elif op == 'BOOL': x = float(x != 0)
            elif op == 'TRUNC':
                if not math.isfinite(x) or not -2147483648 <= math.trunc(x) <= 2147483647:
                    raise ValueError('invalid int32 conversion')
                x = float(math.trunc(x))
            elif op == 'SQRT': x = math.sqrt(x)
            else: x = abs(x)
            stack.append(x)
        elif op == 'FMA':
            c, b, a = stack.pop(), stack.pop(), stack.pop(); stack.append(native['fma'](a, b, c))
        else:
            b, a = stack.pop(), stack.pop()
            if op == 'ADD': x = a + b
            elif op == 'SUB': x = a - b
            elif op == 'MUL': x = a * b
            elif op == 'DIV': x = a / b
            elif op in {'IDIV', 'MOD'}:
                if b == 0 or (a == -2147483648 and b == -1): raise ValueError('undefined int32 division')
                x = float(math.trunc(a / b)) if op == 'IDIV' else math.fmod(a, b)
                if x == 0: x = 0.0
            elif op == 'MIN': x = native['fmin'](a, b)
            elif op == 'MAX': x = native['fmax'](a, b)
            elif op == 'LT': x = float(a < b)
            elif op == 'LE': x = float(a <= b)
            elif op == 'GT': x = float(a > b)
            elif op == 'GE': x = float(a >= b)
            elif op == 'EQ': x = float(a == b)
            elif op == 'NE': x = float(a != b)
            else: raise ValueError('unsupported opcode')
            stack.append(x)
        if len(stack) > 4096: raise ValueError('stack overflow')


def profile_case(case, index=0):
    paths = case['paths']
    metadata = Path(paths['program.meta'])
    observed_hashes = {name: file_sha(paths[name]) for name in ('program.meta', 'source.c', 'input.bin', 'oracle.bin')}
    if any(value != case['hashes'][name] for name, value in observed_hashes.items()):
        raise ValueError('frozen source, Metadata, input or original C oracle changed')
    digest = observed_hashes['program.meta']
    fields, rows = read_program(metadata)
    n, payload = matrix_at(paths['input.bin'], index)
    expected_n, expected = matrix_at(paths['oracle.bin'], index)
    output, counts = trace(fields, rows, n, struct.unpack(f'<{n*n}d', payload), block=case['block'])
    actual = struct.pack(f'<{n*n}d', *output)
    if n != expected_n or actual != expected:
        raise AssertionError('small-trace output differs from frozen original C oracle')
    return {'source': case['source'], 'matrix_index': index, 'n': n,
            'metadata_sha256': digest, 'verified_full_file_sha256': observed_hashes,
            'selected_input_payload_sha256': hashlib.sha256(payload).hexdigest(),
            'selected_oracle_payload_sha256': hashlib.sha256(expected).hexdigest(),
            'original_C_selected_matrix_byte_equal': True, **counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    unique = {}
    for case in plan['functional']['cases']:
        unique.setdefault(case['hashes']['source.c'], case)
    records = [profile_case(case) for case in unique.values()]
    result = {'records': records, 'count': len(records), 'plan_sha256': hashlib.sha256(args.plan.read_bytes()).hexdigest(),
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'First small matrix per original source; no large-shape frequency or performance claim.'}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'count': len(records), 'all_original_C_selected_matrix_equal': True,
                      'executed_load_pairs': sum(r['executed_load_pairs'] for r in records)}))
