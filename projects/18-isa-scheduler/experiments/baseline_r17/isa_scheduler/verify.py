"""Independent structural and symbolic verification, plus integer interpreter.

Symbolic signatures preserve operand order and treat arithmetic as opaque pure
functions. They avoid guessing MULW overflow semantics. GET/SET traces and the
multiset of computed expressions must agree; inserted COPY is transparent.
"""
from collections import Counter
import hashlib
from dataclasses import dataclass

from .model import ARITIES, InvalidBlock, distance, parse_block


def _signature(parts):
    # Length-delimited repr of a tuple gives unambiguous opcode/operand encoding.
    return hashlib.sha256(repr(tuple(parts)).encode("utf-8")).hexdigest()


def inspect(rows, window=None):
    values, registers, memory_trace, computations = [], {}, {}, Counter()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("op") not in ARITIES:
            raise InvalidBlock(f"Instruction {index}: invalid or unsupported opcode")
        op = row["op"]
        tokens = [row.get("source")] if op == "COPY" else row.get("inputs", [])
        if not isinstance(tokens, list) or len(tokens) != ARITIES[op]:
            raise InvalidBlock(f"Instruction {index}: invalid operand count")
        args = []
        for token in tokens:
            delta = distance(token)
            if delta > index or (window is not None and delta > window):
                raise InvalidBlock(f"Instruction {index}: unreachable {token}")
            args.append(values[index - delta])
        if op == "GET":
            reg = row.get("reg")
            if not isinstance(reg, str) or not reg:
                raise InvalidBlock("GET requires reg")
            val = registers.get(reg, _signature(("INITIAL_REGISTER", reg)))
            memory_trace.setdefault(reg, []).append((op, val))
        elif op == "SET":
            reg = row.get("reg")
            if not isinstance(reg, str) or not reg:
                raise InvalidBlock("SET requires reg")
            val = args[0]
            registers[reg] = val
            memory_trace.setdefault(reg, []).append((op, val))
        elif op == "COPY":
            val = args[0]
        else:
            val = _signature((op, *args))
        if op != "COPY":
            computations[(op, row.get("reg"), val)] += 1
        values.append(val)
    return memory_trace, computations, registers


class VerificationContext:
    """Independent immutable-input snapshot reused across portfolio candidates.

    The expected symbolic graph is reconstructed from raw input here, never
    from scheduler state. Context validity is tied to this original snapshot.
    """
    def __init__(self, original):
        parse_block(original)
        self.block_id = original["block_id"]
        self.bits = original["bit_width"]
        self._expected = inspect(original["instructions"])

    def check(self, optimized):
        return _check_output(self.block_id, self.bits, self._expected, optimized)


def _check_output(block_id, bits, expected, optimized):
    if not isinstance(optimized, dict):
        raise InvalidBlock("Optimized result must be an object")
    if set(optimized) - {"block_id", "optimized_instructions", "stats"}:
        raise InvalidBlock("Unknown optimized output fields")
    if optimized.get("block_id") != block_id:
        raise InvalidBlock("block_id mismatch")
    rows = optimized.get("optimized_instructions")
    if not isinstance(rows, list):
        raise InvalidBlock("optimized_instructions must be an array")
    if type(bits) is not int or not 2 <= bits <= 5:
        raise InvalidBlock("Invalid original bit_width")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidBlock("Optimized instructions must be objects")
        if row.get("id") != index:
            raise InvalidBlock("Optimized ids must be contiguous output positions")
    parse_block({"block_id": block_id, "bit_width": bits, "instructions": rows})
    observed = inspect(rows, 2 ** bits)
    if expected != observed:
        raise InvalidBlock("Symbolic equivalence failed: operations, operands or register trace changed")
    return {"valid": True, "structural": True, "symbolic_equivalence": True}


def verify(original, optimized):
    return VerificationContext(original).check(optimized)


@dataclass(frozen=True)
class IntegerSemantics:
    """Explicit research semantics, not a claim about the official ISA."""
    word_bits: int | None = None
    signed: bool = False
    overflow: str = "wrap"
    max_unbounded_bits: int = 4096

    def __post_init__(self):
        if self.word_bits is not None and (type(self.word_bits) is not int or not 1 <= self.word_bits <= 128):
            raise InvalidBlock("word_bits must be 1..128 or None")
        if self.overflow not in ("wrap", "error"):
            raise InvalidBlock("overflow must be wrap or error")
        if type(self.max_unbounded_bits) is not int or self.max_unbounded_bits < 1:
            raise InvalidBlock("max_unbounded_bits must be positive")

    def normalize(self, value):
        if type(value) is not int:
            raise InvalidBlock("Integer interpreter accepts integer register values only")
        if self.word_bits is None:
            if value.bit_length() > self.max_unbounded_bits:
                raise InvalidBlock("Unbounded integer safety limit exceeded")
            return value
        modulus = 1 << self.word_bits
        minimum = -(modulus // 2) if self.signed else 0
        maximum = modulus // 2 - 1 if self.signed else modulus - 1
        if self.overflow == "error" and not minimum <= value <= maximum:
            raise InvalidBlock("Configured integer overflow")
        value %= modulus
        return value - modulus if self.signed and value >= modulus // 2 else value


def interpret(rows, initial_registers, semantics=None):
    """MULW defaults to unbounded ints; configurable fixed-word low-bit model."""
    semantics = semantics or IntegerSemantics()
    registers = {reg: semantics.normalize(value) for reg, value in initial_registers.items()}
    values = []
    for index, row in enumerate(rows):
        op = row["op"]
        tokens = [row["source"]] if op == "COPY" else row.get("inputs", [])
        args = [values[index - distance(t)] for t in tokens]
        if op == "GET":
            val = registers[row["reg"]]
        elif op == "SET":
            val = args[0]
            registers[row["reg"]] = val
        elif op == "COPY":
            val = args[0]
        elif op == "ADD":
            val = args[0] + args[1]
        elif op == "MULW":
            if semantics.word_bits is None and args[0] and args[1] and args[0].bit_length() + args[1].bit_length() > semantics.max_unbounded_bits + 1:
                raise InvalidBlock("Unbounded integer safety limit exceeded")
            val = args[0] * args[1]
        else:
            raise InvalidBlock(f"Unsupported interpreter opcode: {op}")
        val = semantics.normalize(val)
        if op == "SET":
            registers[row["reg"]] = val
        values.append(val)
    return registers

