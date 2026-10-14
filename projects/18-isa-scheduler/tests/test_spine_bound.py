from dataclasses import replace
import random
import unittest
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.search import search
from isa_scheduler.spine_bounds import spine_capacity_bound
from isa_scheduler.workloads import generate_workload


class SpineBoundTests(unittest.TestCase):
    def test_short_spines_with_capacity_certificate_have_no_full_oracle_solution(self):
        checked=0
        for seed in range(960001,960101):
            rng=random.Random(seed)
            rows=[{"op":"GET","reg":f"r{i}"} for i in range(3)]
            rows.append({"op":"ADD","inputs":["t#3","t#2"]})
            for _ in range(3):
                index=len(rows);root=rng.randrange(3)
                rows.append({"op":"ADD","inputs":["t#1",f"t#{index-root}"]})
            rows.append({"op":"SET","reg":"out","inputs":["t#1"]})
            data={"block_id":seed,"bit_width":2,"instructions":rows}
            # Internal window two only for proof audit; public parser unchanged.
            block=replace(parse_block(data),bit_width=1)
            certificate=spine_capacity_bound(block)
            if certificate and certificate["infeasible_under_model"]:
                with self.assertRaises(InfeasibleSchedule):search(block,time_budget_ms=1000,max_states=100000)
                checked+=1
        self.assertGreater(checked,50)

    def test_shared_branches_and_register_aliases_are_not_misclassified(self):
        for family in ("ladder_diamond","butterfly","matrix_product_tile","multi_sink_shared"):
            self.assertIsNone(spine_capacity_bound(parse_block(generate_workload(1,family,128,2))))
        data=generate_workload(1,"wide_fanout",128,2)
        certificate=spine_capacity_bound(parse_block(data))
        self.assertIsNotNone(certificate)
        self.assertTrue(certificate["infeasible_under_model"])
        data["instructions"][-1]["reg"]="r0"
        self.assertIsNone(spine_capacity_bound(parse_block(data)))
