import unittest
from isa_scheduler.forest_linear import emit_forest,eligible
from isa_scheduler.incremental import PreparedGraph,schedule_incremental
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify


class DirectForestPoliciesTests(unittest.TestCase):
    def test_conservative_memory_chain_is_not_a_direct_forest(self):
        data=generate_workload(1,"balanced_tree",32,4)
        block=parse_block(data,"conservative")
        self.assertFalse(eligible(block,PreparedGraph(block)))

    def test_three_general_policy_outputs_exactly_match_direct_emission(self):
        families=("balanced_tree","skew_tree","parallel_chains","ragged_tree","padded_tree")
        for seed in range(1000):
            data=generate_workload(seed,families[seed%len(families)],32+seed%97,2+seed%4)
            block=parse_block(data);prepared=PreparedGraph(block)
            self.assertTrue(eligible(block,prepared))
            for policy in ("pressure","demand","size_pressure"):
                try:before=schedule_incremental(block,policy,prepared=prepared)
                except InfeasibleSchedule:
                    with self.assertRaises(InfeasibleSchedule):emit_forest(block,prepared,policy=policy)
                    continue
                after=emit_forest(block,prepared,policy=policy)
                self.assertEqual(before["optimized_instructions"],after["optimized_instructions"],(seed,policy))
                verify(data,after)
