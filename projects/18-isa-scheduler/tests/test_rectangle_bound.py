import unittest
from isa_scheduler.rectangle_bounds import rectangle_capacity_bound
from isa_scheduler.closed_subgraph import closed_subset_data
from isa_scheduler.model import parse_block,InfeasibleSchedule,BudgetExceeded
from isa_scheduler.relaxed_capacity import capacity_oracle
from isa_scheduler.optimizer import optimize
from isa_scheduler.workloads import generate_workload


class RectangleTests(unittest.TestCase):
    def test_large_matrix_closed_projection_proof(self):
        for size in (64,256,1024,4096):
            data=generate_workload(123,'matrix_product_tile',size,2)
            proof=rectangle_capacity_bound(parse_block(data),time_budget_ms=1000)
            self.assertIsNotNone(proof)
            projected=closed_subset_data(data,proof['original_indices'])
            result=capacity_oracle(parse_block(projected),max_nodes=20,time_budget_ms=1000)
            self.assertTrue(result['outcome'].startswith('proven'))
            self.assertEqual(result['explored_states'],227)
            # Online 10ms budget may legitimately be unknown under contention;
            # completeness is established separately above with 1000ms.
            with self.assertRaises((InfeasibleSchedule,BudgetExceeded)):
                optimize(data,time_budget_ms=1000)

    def test_hazards_widths_and_budgets_do_not_get_false_proofs(self):
        data=generate_workload(1,'matrix_product_tile',256,3)
        self.assertIsNone(rectangle_capacity_bound(parse_block(data),time_budget_ms=1000))
        data['bit_width']=2
        self.assertIsNone(rectangle_capacity_bound(parse_block(data),time_budget_ms=0))
        self.assertIsNone(rectangle_capacity_bound(parse_block(data),time_budget_ms=1000,max_pairs=0))
        self.assertIsNone(rectangle_capacity_bound(parse_block(data,'conservative'),time_budget_ms=1000))
        getrows=[row for row in data['instructions'] if row['op']=='GET'];getrows[1]['reg']=getrows[0]['reg']
        self.assertIsNone(rectangle_capacity_bound(parse_block(data),time_budget_ms=1000))

    def test_unrelated_graphs_not_claimed_infeasible(self):
        for family in ('serial_chains','near_window_spine','butterfly','ordered_duplicate_network'):
            self.assertIsNone(rectangle_capacity_bound(parse_block(generate_workload(1,family,128,2)),time_budget_ms=1000))
