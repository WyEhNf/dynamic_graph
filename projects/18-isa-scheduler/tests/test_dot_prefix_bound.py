import unittest
from isa_scheduler.dot_prefix_bounds import shared_prefix_capacity_bound
from isa_scheduler.closed_subgraph import closed_subset_data
from isa_scheduler.relaxed_capacity import capacity_oracle
from isa_scheduler.workloads import generate_workload
from isa_scheduler.model import parse_block,InfeasibleSchedule,BudgetExceeded
from isa_scheduler.optimizer import optimize


class PrefixTests(unittest.TestCase):
    def test_actual_prefix_projection_independent_exhaustion(self):
        for size in (64,256,1024,4096):
            data=generate_workload(123,'dot_product_many',size,2)
            proof=shared_prefix_capacity_bound(parse_block(data),time_budget_ms=1000)
            self.assertIsNotNone(proof)
            projected=closed_subset_data(data,proof['original_indices'])
            result=capacity_oracle(parse_block(projected),max_nodes=27,time_budget_ms=1000)
            self.assertTrue(result['outcome'].startswith('proven'))
            self.assertEqual(result['explored_states'],1481)
            # The independent 1000ms proof above is complete. Online proof has
            # its own 15ms cap; CPU contention may legitimately return unknown
            # and heuristic failure/budget instead of a proof, never an output.
            with self.assertRaises((InfeasibleSchedule,BudgetExceeded)):
                optimize(data,time_budget_ms=1000)

    def test_width_hazard_and_budget_screening(self):
        data=generate_workload(1,'dot_product_many',64,3)
        self.assertIsNone(shared_prefix_capacity_bound(parse_block(data),time_budget_ms=1000))
        data['bit_width']=2
        self.assertIsNone(shared_prefix_capacity_bound(parse_block(data),time_budget_ms=0))
        self.assertIsNone(shared_prefix_capacity_bound(parse_block(data),time_budget_ms=1000,max_combinations=0))
        self.assertIsNone(shared_prefix_capacity_bound(parse_block(data,'conservative'),time_budget_ms=1000))
