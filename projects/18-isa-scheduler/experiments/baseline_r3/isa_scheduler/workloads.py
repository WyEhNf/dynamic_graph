"""Research topologies with explicit seeds and controllable sizes.

These are synthetic graph shapes, not measured application traces or official
competition data. Size is a target; actual node count is recorded by evaluators.
"""
import random


FAMILIES = ("balanced_tree", "skew_tree", "parallel_chains", "ladder_diamond",
            "sparse_shared", "butterfly", "hazard_multi", "wide_fanout")


def generate_workload(seed, family, target_nodes, bit_width):
    if family not in FAMILIES or target_nodes < 4:
        raise ValueError("Unknown family or target_nodes < 4")
    rng, rows = random.Random(seed), []

    def emit(op, args=(), reg=None):
        index = len(rows)
        row = {"id": index, "op": op}
        if reg is not None:
            row["reg"] = reg
        if args:
            row["inputs"] = [f"t#{index-a}" for a in args]
        rows.append(row)
        return index

    def arithmetic(args):
        return emit("MULW" if rng.random() < .15 else "ADD", args)

    if family in ("balanced_tree", "skew_tree"):
        leaves = max(2, target_nodes // 2)
        values = [emit("GET", reg=f"r{i}") for i in range(leaves)]
        if family == "balanced_tree":
            while len(values) > 1:
                values = [arithmetic(values[i:i+2]) if i+1 < len(values) else values[i]
                          for i in range(0, len(values), 2)]
            result = values[0]
        else:
            result = values[0]
            for value in values[1:]:
                result = arithmetic((result, value))
        emit("SET", (result,), "out")
    elif family == "parallel_chains":
        chains = max(2, int(target_nodes ** .5))
        depth = max(1, target_nodes // chains - 2)
        values = [emit("GET", reg=f"r{i}") for i in range(chains)]
        for _ in range(depth):
            for i, value in enumerate(values):
                values[i] = arithmetic((value, value))
        for i, value in enumerate(values):
            emit("SET", (value,), f"out{i}")
    elif family == "ladder_diamond":
        a, b = emit("GET", reg="a"), emit("GET", reg="b")
        value = arithmetic((a, b))
        while len(rows) + 3 < target_nodes:
            left = arithmetic((value, a))
            right = arithmetic((value, b))
            value = arithmetic((left, right))
        emit("SET", (value,), "out")
    elif family == "sparse_shared":
        roots = [emit("GET", reg=f"r{i}") for i in range(3)]
        values = list(roots)
        while len(rows) < target_nodes - 1:
            if rng.random() < .25:
                args = (rng.choice(roots), values[-1])
            else:
                args = (rng.choice(values[-4:]), rng.choice(values[-4:]))
            values.append(arithmetic(args))
        emit("SET", (values[-1],), "out")
    elif family == "butterfly":
        width = min(16, max(2, 1 << max(1, (target_nodes // 8).bit_length() - 1)))
        values = [emit("GET", reg=f"r{i}") for i in range(width)]
        rounds = max(1, (target_nodes - 2 * width) // width)
        for stage in range(rounds):
            stride, next_values = 1 << (stage % (width.bit_length() - 1)), list(values)
            for i in range(width):
                partner = i ^ stride
                if i < partner:
                    next_values[i] = arithmetic((values[i], values[partner]))
                    next_values[partner] = arithmetic((values[partner], values[i]))
            values = next_values
        for i, value in enumerate(values):
            emit("SET", (value,), f"out{i}")
    elif family == "hazard_multi":
        names = [f"r{i}" for i in range(min(8, max(2, target_nodes // 16)))]
        while len(rows) + 4 <= target_nodes:
            destination, source = rng.sample(names, 2)
            a, b = emit("GET", reg=destination), emit("GET", reg=source)
            value = arithmetic((a, b))
            emit("SET", (value,), destination)
    else:
        roots = [emit("GET", reg=f"r{i}") for i in range(min(8, max(3, target_nodes // 8)))]
        value = arithmetic((roots[0], roots[1]))
        while len(rows) < target_nodes - 1:
            value = arithmetic((value, rng.choice(roots)))
        emit("SET", (value,), "out")
    return {"block_id": f"research-{family}-{target_nodes}-{seed}",
            "bit_width": bit_width, "instructions": rows}

