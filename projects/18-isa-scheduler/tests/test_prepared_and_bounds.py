import unittest
from isa_scheduler.bounds import fixed_order_copy_bound
from isa_scheduler.incremental import PreparedGraph,schedule_incremental
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


class PreparedTests(unittest.TestCase):
    def test_reused_graph_does_not_leak_mutable_policy_state(self):
        for family in ('balanced_tree','hazard_multi','multi_sink_irregular','cross_group_shared'):
            for bits in range(2,6):
                data=generate_workload(18001,family,128,bits);block=parse_block(data);prepared=PreparedGraph(block)
                for policy in ('stable_fast','pressure','ready_fast','affinity','demand','incremental','pressure'):
                    try:fresh=schedule_incremental(block,policy)
                    except InfeasibleSchedule:
                        with self.assertRaises(InfeasibleSchedule):schedule_incremental(block,policy,prepared=prepared)
                        continue
                    reused=schedule_incremental(block,policy,prepared=prepared)
                    self.assertEqual(fresh['optimized_instructions'],reused['optimized_instructions'])
                    verify(data,reused)
                    bound=fixed_order_copy_bound(block,reused['stats']['original_order'])
                    self.assertLessEqual(bound['copy_lower_bound'],reused['stats']['inserted_copy_count'])
                    self.assertLessEqual(bound['fixed_order_peak_live'],block.window)

    def test_wrong_block_preparation_and_wrong_order_trace_rejected(self):
        data=generate_workload(18001,'parallel_chains',128,2);block=parse_block(data)
        with self.assertRaises(ValueError):schedule_incremental(parse_block(data),prepared=PreparedGraph(block))
        with self.assertRaises(ValueError):fixed_order_copy_bound(block,[0]*len(block.instructions))
        with self.assertRaises(ValueError):fixed_order_copy_bound(block,list(reversed(range(len(block.instructions)))))


if __name__=='__main__':unittest.main()
