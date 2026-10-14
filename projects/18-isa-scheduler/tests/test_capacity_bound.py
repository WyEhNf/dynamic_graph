from dataclasses import replace
import unittest
from isa_scheduler.bounds import forest_capacity_bound
from isa_scheduler.model import InfeasibleSchedule, parse_block
from isa_scheduler.optimizer import optimize
from isa_scheduler.search import search
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


class CapacityBoundTests(unittest.TestCase):
    def test_32_node_balanced_tree_has_strict_local_model_certificate(self):
        data=generate_workload(18001,'balanced_tree',32,2)
        certificate=forest_capacity_bound(parse_block(data))
        self.assertEqual(certificate['minimum_register_slots'],5)
        self.assertTrue(certificate['infeasible_under_model'])
        with self.assertRaisesRegex(InfeasibleSchedule,'proven_infeasible_under_model'):
            optimize(data)
        data['bit_width']=3
        verify(data,optimize(data,time_budget_ms=1000))

    def test_small_abstract_window_bound_matches_complete_oracle(self):
        # W=2 is an internal theorem check; public input still accepts only 2..5 bit.
        data=generate_workload(18001,'balanced_tree',8,2)
        block=replace(parse_block(data),bit_width=1)
        self.assertTrue(forest_capacity_bound(block)['infeasible_under_model'])
        with self.assertRaisesRegex(InfeasibleSchedule,'proven_infeasible_under_model'):
            search(block,time_budget_ms=1000)

    def test_shared_dags_and_register_aliases_never_get_tree_certificate(self):
        data=generate_workload(18001,'ladder_diamond',32,2)
        self.assertIsNone(forest_capacity_bound(parse_block(data)))
        data=generate_workload(18001,'balanced_tree',32,2)
        data['instructions'][1]['reg']=data['instructions'][0]['reg']
        self.assertIsNone(forest_capacity_bound(parse_block(data)))
        data=generate_workload(18001,'balanced_tree',32,2)
        data['instructions'][-1]['reg']=data['instructions'][0]['reg']
        self.assertIsNone(forest_capacity_bound(parse_block(data)))


if __name__=='__main__':unittest.main()
