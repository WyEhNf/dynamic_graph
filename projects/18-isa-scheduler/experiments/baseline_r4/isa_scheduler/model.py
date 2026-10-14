"""Parse distance-based instructions into a dependency DAG.

The opcode semantics are deliberately limited to what can be tested locally.
GET/SET use same-register RAW/WAR/WAW dependencies by default. A deliberately
conservative total-order mode remains available for audits.
"""
from dataclasses import dataclass
import re


class InvalidBlock(ValueError):
    pass


class VerificationFailed(InvalidBlock):
    pass


class InfeasibleSchedule(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


ARITIES = {"GET": 0, "SET": 1, "ADD": 2, "MULW": 2, "COPY": 1}
TOKEN = re.compile(r"t#([1-9][0-9]*)\Z")


@dataclass(frozen=True)
class Instruction:
    index: int
    original_id: int | str
    op: str
    args: tuple[int, ...]
    reg: str | None
    order_deps: tuple[int, ...]


@dataclass(frozen=True)
class Block:
    block_id: int | str
    bit_width: int
    instructions: tuple[Instruction, ...]
    memory_order: str = "hazard"

    @property
    def window(self):
        return 2 ** self.bit_width


def distance(token):
    if not isinstance(token, str) or not TOKEN.fullmatch(token):
        raise InvalidBlock(f"Invalid distance token: {token!r}; expected t#d, d >= 1")
    return int(token[2:])


def parse_block(data, memory_order="hazard"):
    if memory_order not in ("hazard", "conservative"):
        raise InvalidBlock("memory_order must be hazard or conservative")
    if not isinstance(data, dict) or "block_id" not in data:
        raise InvalidBlock("A JSON object with block_id is required")
    if set(data) - {"block_id", "bit_width", "instructions"}:
        raise InvalidBlock("Unknown block fields; explicit schema adapter is required")
    if type(data["block_id"]) not in (int, str):
        raise InvalidBlock("block_id must be an integer or string")
    bits = data.get("bit_width")
    if type(bits) is not int or not 2 <= bits <= 5:
        raise InvalidBlock("bit_width must be an integer between 2 and 5")
    rows = data.get("instructions")
    if not isinstance(rows, list):
        raise InvalidBlock("instructions must be an array")
    result, seen, memory_tail = [], set(), None
    last_write, readers = {}, {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidBlock(f"Instruction {i} must be an object")
        original_id = row.get("id", i)
        if type(original_id) not in (int, str) or original_id in seen:
            raise InvalidBlock(f"Instruction {i}: id must be a unique integer or string")
        seen.add(original_id)
        op = row.get("op")
        if op not in ARITIES:
            raise InvalidBlock(f"Unsupported opcode {op!r}; supported: {', '.join(ARITIES)}")
        allowed = {"id", "op"}
        allowed |= {"reg"} if op in ("GET", "SET") else set()
        allowed |= {"source"} if op == "COPY" else {"inputs"}
        if set(row) - allowed:
            raise InvalidBlock(f"Instruction {i}: unknown fields for {op}")
        if op == "COPY":
            if "inputs" in row:
                raise InvalidBlock("COPY uses source, not inputs")
            inputs = [row.get("source")]
        else:
            inputs = row.get("inputs", [])
        if not isinstance(inputs, list) or len(inputs) != ARITIES[op]:
            raise InvalidBlock(f"Instruction {i}: {op} expects {ARITIES[op]} input(s)")
        args = tuple(i - distance(t) for t in inputs)
        if any(a < 0 for a in args):
            raise InvalidBlock(f"Instruction {i}: reference precedes block start")
        reg = row.get("reg")
        if op in ("GET", "SET") and (not isinstance(reg, str) or not reg):
            raise InvalidBlock(f"Instruction {i}: GET/SET requires a nonempty reg")
        order_deps = set()
        if op in ("GET", "SET") and memory_order == "conservative":
            if memory_tail is not None:
                order_deps.add(memory_tail)
            memory_tail = i
        elif op in ("GET", "SET"):
            if reg in last_write:
                order_deps.add(last_write[reg])  # RAW for GET, WAW for SET.
            if op == "GET":
                readers.setdefault(reg, set()).add(i)
            else:
                order_deps.update(readers.get(reg, set()))  # WAR before overwrite.
                readers[reg] = set()
                last_write[reg] = i
        result.append(Instruction(i, original_id, op, args, reg, tuple(sorted(order_deps))))
    return Block(data["block_id"], bits, tuple(result), memory_order)

