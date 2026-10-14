"""DYNCHOL 3 base36_opcode_v1: fixed opcode IDs, unchanged argument text."""
import math
import re

# This order is a wire contract, independent of enum numbering or map iteration.
OPCODE_NAMES = ('CONST','LOAD','STORE','UNINIT','READ','WRITE','DUP','POP',
                'ADD','SUB','MUL','DIV','IDIV','MOD','NEG','NOT','BOOL','TRUNC',
                'SQRT','ABS','MIN','MAX','FMA','LT','LE','GT','GE','EQ','NE',
                'JUMP','JZ','JNZ','RETURN')
OPCODE_CODES = '0123456789ABCDEFGHIJKLMNOPQRSTUVW'
REQUIRED = frozenset(('CONST','LOAD','STORE','UNINIT','READ','WRITE','JUMP','JZ','JNZ'))
_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


def _argument(text):
    if not _NUMBER.fullmatch(text) or not math.isfinite(float(text)):
        raise ValueError('invalid finite numeric bytecode argument')


def encode_instruction(line):
    """Accept canonical v2 text and replace only its mnemonic with its ID."""
    name, separator, argument = line.partition(' ')
    if name not in OPCODE_NAMES or (bool(separator) != (name in REQUIRED)):
        raise ValueError('invalid canonical named instruction')
    if separator: _argument(argument)
    return OPCODE_CODES[OPCODE_NAMES.index(name)] + (separator + argument)


def decode_instruction(line):
    if not line or line[0] not in OPCODE_CODES:
        raise ValueError('invalid compact opcode')
    name = OPCODE_NAMES[OPCODE_CODES.index(line[0])]
    suffix = line[1:]
    if name in REQUIRED:
        if not suffix.startswith(' '): raise ValueError('missing compact argument')
        _argument(suffix[1:])
    elif suffix:
        raise ValueError('unexpected compact argument')
    return name + suffix
