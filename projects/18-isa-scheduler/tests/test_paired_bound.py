from dataclasses import replace
import unittest
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.paired_bounds import paired_network_capacity_bound
from isa_scheduler.relaxed_capacity import capacity_oracle
from isa_scheduler.search import search
from isa_scheduler.workloads import generate_workload


class PairedBoundTests(unittest.TestCase):
    def test_two_root_network_matches_complete_age_and_capacity_oracles(self):
        block=replace(parse_block(generate_workload(1,"butterfly",16,2)),bit_width=1)
        certificate=paired_network_capacity_bound(block)
        self.assertEqual(certificate["minimum_register_slots"],3)
        with self.assertRaises(InfeasibleSchedule):search(block,time_budget_ms=1000,max_states=100000,exact_max_nodes=16)
        self.assertTrue(capacity_oracle(block,2)["outcome"].startswith("proven"))
        self.assertTrue(capacity_oracle(block,3)["outcome"].startswith("feasible"))

    def test_four_root_network_capacity_proof_and_disallowed_shapes(self):
        block=parse_block(generate_workload(1,"butterfly",32,2))
        certificate=paired_network_capacity_bound(block)
        self.assertEqual(certificate["minimum_register_slots"],5)
        self.assertTrue(capacity_oracle(block,4,max_nodes=32,max_states=200000,time_budget_ms=5000)["outcome"].startswith("proven"))
        self.assertTrue(capacity_oracle(block,5,max_nodes=32,max_states=200000,time_budget_ms=5000,depth_first=True)["outcome"].startswith("feasible"))
        for family in ("sparse_shared","wide_fanout","matrix_product_tile","ladder_diamond"):
            self.assertIsNone(paired_network_capacity_bound(parse_block(generate_workload(1,family,64,2))))
