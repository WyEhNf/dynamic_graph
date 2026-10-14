"""Research topologies with explicit seeds and controllable sizes.

These are synthetic graph shapes, not measured application traces or official
competition data. Size is a target; actual node count is recorded by evaluators.
"""
import random


FAMILIES = ("balanced_tree", "skew_tree", "parallel_chains", "ladder_diamond",
            "sparse_shared", "butterfly", "hazard_multi", "wide_fanout",
            "multi_sink_shared", "fanout_diamonds", "multi_sink_irregular", "cross_group_shared",
            "ragged_tree", "padded_tree", "dot_product_many", "stencil_1d", "matrix_product_tile", "sparse_live", "near_window_spine")


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

    if family=="near_window_spine":
        roots=[emit("GET",reg=f"persistent{i}") for i in range((1<<bit_width)-2)]
        value=arithmetic(tuple(roots[:2]))
        sequence=list(roots[2:])
        while len(rows)<max(target_nodes,len(roots)+3)-1:
            if not sequence:
                sequence=list(roots);rng.shuffle(sequence)
            value=arithmetic((value,sequence.pop(0)))
        emit("SET",(value,),"out")
    elif family=="dot_product_many":
        outputs=4
        width=max(2,target_nodes//13)
        weights=[emit("GET",reg=f"w{i}") for i in range(width)]
        values=[[emit("GET",reg=f"x{row}_{i}") for i in range(width)] for row in range(outputs)]
        for row in range(outputs):
            products=[emit("MULW",(weights[i],values[row][i])) for i in range(width)]
            total=products[0]
            for product in products[1:]:total=emit("ADD",(total,product))
            emit("SET",(total,),f"out{row}")
    elif family=="stencil_1d":
        width=max(3,target_nodes//4)
        values=[emit("GET",reg=f"x{i}") for i in range(width)]
        for i in range(width):
            pair=emit("ADD",(values[max(0,i-1)],values[i]))
            total=emit("ADD",(pair,values[min(width-1,i+1)]))
            emit("SET",(total,),f"out{i}")
    elif family=="matrix_product_tile":
        width=2
        while 2*(width+1)**2+2*(width+1)**3<=target_nodes:width+=1
        a=[[emit("GET",reg=f"a{i}_{j}") for j in range(width)] for i in range(width)]
        b=[[emit("GET",reg=f"b{i}_{j}") for j in range(width)] for i in range(width)]
        for i in range(width):
            for j in range(width):
                products=[emit("MULW",(a[i][k],b[k][j])) for k in range(width)]
                total=products[0]
                for product in products[1:]:total=emit("ADD",(total,product))
                emit("SET",(total,),f"c{i}_{j}")
    elif family in ("ragged_tree", "padded_tree"):
        leaves = max(2,target_nodes//2) if family=="ragged_tree" else max(2,int(target_nodes**.5))
        values=[emit("GET",reg=f"r{i}") for i in range(leaves)]
        if family=="padded_tree":
            # Unary data dependencies keep demand unchanged while changing
            # subtree work substantially; all original arithmetic is retained.
            padding=[0]*leaves
            for _ in range(max(0,target_nodes-2*leaves)):
                padding[rng.randrange(leaves)]+=1
            for i in range(leaves):
                for _ in range(padding[i]):values[i]=arithmetic((values[i],values[i]))
            while len(values)>1:
                values=[arithmetic(values[i:i+2]) if i+1<len(values) else values[i] for i in range(0,len(values),2)]
        else:
            while len(values)>1:
                children=[]
                for _ in range(2):
                    position=rng.randrange(len(values))
                    children.append(values[position]);values[position]=values[-1];values.pop()
                values.append(arithmetic(tuple(children)))
        emit("SET",(values[0],),"out")
    elif family in ("balanced_tree", "skew_tree"):
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
    elif family in ("sparse_shared","sparse_live"):
        roots = [emit("GET", reg=f"r{i}") for i in range(3)]
        values = list(roots)
        while len(rows) < target_nodes - 1:
            if rng.random() < .25:
                args = (rng.choice(roots), values[-1])
            else:
                args = (rng.choice(values[-4:]), rng.choice(values[-4:]))
            values.append(arithmetic(args))
        emit("SET", (values[-1],), "out")
        if family=="sparse_live":
            # Create a separate corpus where all data nodes reach the SET;
            # this is input generation, never deletion from a submitted block.
            required={len(rows)-1};stack=[len(rows)-1]
            while stack:
                index=stack.pop()
                for token in rows[index].get("inputs",[]):
                    source=index-int(token[2:])
                    if source not in required:required.add(source);stack.append(source)
            mapping={index:rank for rank,index in enumerate(sorted(required))}
            retained=[]
            for index in sorted(required):
                row={**rows[index]}
                if "inputs" in row:
                    row["inputs"]=[f"t#{mapping[index]-mapping[index-int(token[2:])]}" for token in row["inputs"]]
                retained.append(row)
            rows=retained
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
    elif family in ("multi_sink_irregular", "cross_group_shared"):
        root_count = rng.randint(2, min(6, max(2, target_nodes//32)))
        roots = [emit("GET", reg=f"common{i}") for i in range(root_count)]
        branches = rng.randint(4, min(16, max(4, target_nodes//8)))
        values = [emit("GET", reg=f"private{i}") for i in range(branches)]
        mappings = [rng.randrange(root_count) for _ in range(branches)]
        lengths = [1] * branches
        for _ in range(max(0, target_nodes-root_count-3*branches)):
            lengths[rng.randrange(branches)] += 1
        active = list(range(branches))
        while active:
            branch = rng.choice(active)
            source = mappings[branch]
            if family == "cross_group_shared" and rng.random() < .2:
                source = rng.randrange(root_count)
            values[branch] = arithmetic((values[branch], roots[source]))
            lengths[branch] -= 1
            if lengths[branch] == 0:
                active.remove(branch)
        order = list(range(branches));rng.shuffle(order)
        for branch in order:
            emit("SET", (values[branch],), f"out{branch}")
    elif family in ("multi_sink_shared", "fanout_diamonds"):
        root_count = 4 if family == "multi_sink_shared" else 1
        roots = [emit("GET", reg=f"common{i}") for i in range(root_count)]
        branches = max(4, min(16, target_nodes // 8))
        per_level = 3 if family == "fanout_diamonds" else 1
        depth = max(1, (target_nodes-root_count-2*branches)//(branches*per_level))
        results = []
        for branch in range(branches):
            value = emit("GET", reg=f"private{branch}")
            common = roots[branch % root_count]
            for _ in range(depth):
                if family == "fanout_diamonds":
                    left = arithmetic((value, common))
                    right = arithmetic((common, value))
                    value = arithmetic((left, right))
                else:
                    value = arithmetic((value, common))
            results.append(value)
        for branch, value in enumerate(results):
            emit("SET", (value,), f"out{branch}")
    else:
        roots = [emit("GET", reg=f"r{i}") for i in range(min(8, max(3, target_nodes // 8)))]
        value = arithmetic((roots[0], roots[1]))
        while len(rows) < target_nodes - 1:
            value = arithmetic((value, rng.choice(roots)))
        emit("SET", (value,), "out")
    return {"block_id": f"research-{family}-{target_nodes}-{seed}",
            "bit_width": bit_width, "instructions": rows}

