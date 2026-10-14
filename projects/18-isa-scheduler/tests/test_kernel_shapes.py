import unittest
from isa_scheduler.model import parse_block
from isa_scheduler.verify import IntegerSemantics,interpret
from isa_scheduler.workloads import generate_workload


class KernelShapeTests(unittest.TestCase):
    def test_three_templates_match_separate_integer_gold_functions(self):
        semantics=IntegerSemantics(16,False)
        for family in ("dot_product_many","stencil_1d","matrix_product_tile"):
            data=generate_workload(1000001,family,64,5)
            initial={row["reg"]:sum(map(ord,row["reg"]))%11-5 for row in data["instructions"] if row["op"]=="GET"}
            result=interpret(data["instructions"],initial,semantics)
            if family=="dot_product_many":
                width=sum(name.startswith("w") for name in initial)
                expected={f"out{row}":sum(initial[f"w{i}"]*initial[f"x{row}_{i}"] for i in range(width))%65536 for row in range(4)}
            elif family=="stencil_1d":
                width=len(initial)
                expected={f"out{i}":sum(initial[f"x{j}"] for j in (max(0,i-1),i,min(width-1,i+1)))%65536 for i in range(width)}
            else:
                width=2
                expected={f"c{i}_{j}":sum(initial[f"a{i}_{k}"]*initial[f"b{k}_{j}"] for k in range(width))%65536 for i in range(width) for j in range(width)}
            for register,value in expected.items():self.assertEqual(result[register],value,(family,register))

    def test_live_sparse_has_no_unobserved_data_nodes(self):
        for seed in range(970001,970051):
            block=parse_block(generate_workload(seed,"sparse_live",256,3))
            observed={node.index for node in block.instructions if node.op=="SET"}
            stack=list(observed)
            while stack:
                index=stack.pop()
                for source in block.instructions[index].args:
                    if source not in observed:observed.add(source);stack.append(source)
            self.assertEqual(observed,set(range(len(block.instructions))))
