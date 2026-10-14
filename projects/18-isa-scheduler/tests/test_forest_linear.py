import unittest
from isa_scheduler.forest_linear import emit_forest,eligible,window_work_order
from isa_scheduler.incremental import PreparedGraph,schedule_incremental
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


class LinearForestTests(unittest.TestCase):
    def test_1000_postorder_emissions_match_general_ready_policy(self):
        for case in range(1000):
            data=generate_workload(940001+case,("balanced_tree","skew_tree","ragged_tree","padded_tree")[case%4],
                                   (16,64,128,256,512)[case%5],2+((case//4)%4))
            block=parse_block(data);prepared=PreparedGraph(block)
            self.assertTrue(eligible(block,prepared))
            try:old=schedule_incremental(block,"size_pressure",prepared=prepared)
            except InfeasibleSchedule:
                with self.assertRaises(InfeasibleSchedule):emit_forest(block,prepared)
                continue
            result=emit_forest(block,prepared)
            self.assertEqual(result["optimized_instructions"],old["optimized_instructions"],case)
            self.assertEqual(result["stats"]["original_order"],old["stats"]["original_order"])
            verify(data,result)

    def test_dead_nodes_shared_dags_and_register_aliases_rejected(self):
        for family in ("sparse_shared","hazard_multi","cross_group_shared"):
            block=parse_block(generate_workload(940001,family,64,3));prepared=PreparedGraph(block)
            self.assertFalse(eligible(block,prepared))
            with self.assertRaises(ValueError):emit_forest(block,prepared)
        data={"block_id":"dead-get","bit_width":2,"instructions":[{"op":"GET","reg":"unused"}]}
        block=parse_block(data);prepared=PreparedGraph(block)
        self.assertFalse(eligible(block,prepared))
        with self.assertRaises(ValueError):emit_forest(block,prepared)

    def test_work_first_capacity_and_independent_outputs(self):
        successes=0
        for case in range(500):
            data=generate_workload(950001+case,("ragged_tree","padded_tree")[case%2],
                                   (16,64,128,256,512)[case%5],2+((case//2)%4))
            block=parse_block(data);prepared=PreparedGraph(block)
            try:result=emit_forest(block,prepared,work_first=True)
            except InfeasibleSchedule:continue
            verify(data,result)
            self.assertEqual(set(result["stats"]["original_order"]),set(range(len(block.instructions))))
            self.assertEqual(len(result["stats"]["original_order"]),len(block.instructions))
            # Independently compute peak logical live capacity along the plan.
            from isa_scheduler.bounds import fixed_order_copy_bound
            bound=fixed_order_copy_bound(block,result["stats"]["original_order"])
            self.assertLessEqual(bound["fixed_order_peak_live"],block.window)
            self.assertLessEqual(bound["copy_lower_bound"],result["stats"]["inserted_copy_count"])
            successes+=1
        self.assertGreater(successes,350)
