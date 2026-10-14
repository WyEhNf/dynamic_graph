import unittest
from isa_scheduler.closed_subgraph import closed_subset_data,projection_eligible
from isa_scheduler.model import BudgetExceeded,parse_block
from isa_scheduler.relaxed_capacity import capacity_oracle
from isa_scheduler.workloads import generate_workload


class RelaxationTests(unittest.TestCase):
    def test_balanced_tree_matches_known_four_slot_requirement(self):
        block=parse_block(generate_workload(1,"balanced_tree",16,2))
        self.assertTrue(capacity_oracle(block,3)["outcome"].startswith("proven"))
        self.assertTrue(capacity_oracle(block,4)["outcome"].startswith("feasible"))
        result=capacity_oracle(block,4)
        self.assertEqual(set(result["relaxed_original_order"]),set(range(len(block.instructions))))

    def test_budget_and_projection_screening(self):
        data=generate_workload(1,"ragged_tree",16,2);block=parse_block(data)
        with self.assertRaises(BudgetExceeded):capacity_oracle(block,max_states=1)
        with self.assertRaises(ValueError):closed_subset_data(data,[len(block.instructions)-1])
        with self.assertRaises(ValueError):closed_subset_data(data,[-1])
        self.assertTrue(projection_eligible(block))
        self.assertEqual(len(closed_subset_data(data,range(len(block.instructions)))["instructions"]),len(block.instructions))
        alias=generate_workload(1,"hazard_multi",16,2)
        with self.assertRaises(ValueError):closed_subset_data(alias,[])
