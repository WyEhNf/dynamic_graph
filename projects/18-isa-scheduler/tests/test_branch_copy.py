import unittest
from time import perf_counter
from isa_scheduler.branch_copy import schedule_branch_copy,_branches,_transition
from isa_scheduler.incremental import PreparedGraph
from isa_scheduler.branch_dp import schedule_branches
from isa_scheduler.model import parse_block,InfeasibleSchedule,BudgetExceeded
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify,interpret,IntegerSemantics


class BranchCopyTests(unittest.TestCase):
    def test_transition_cost_and_original_once_coverage_48_graphs(self):
        checked=0
        for seed in range(4):
            for family in ('multi_sink_shared','multi_sink_irregular','cross_group_shared'):
                for bits in range(2,6):
                    data=generate_workload(400+seed,family,128,bits);block=parse_block(data);prepared=PreparedGraph(block)
                    try:new=schedule_branch_copy(data,block,prepared,time_budget_ms=500)
                    except (InfeasibleSchedule,BudgetExceeded):continue
                    verify(data,new)
                    checked+=1
                    self.assertEqual(set(new['stats']['original_order']),set(range(len(block.instructions))))
                    self.assertEqual(len(new['stats']['original_order']),len(block.instructions))
                    initial={node.reg:-7+node.index*3 for node in block.instructions if node.op=='GET'}
                    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False)):
                        self.assertEqual(interpret(data['instructions'],initial,semantics),interpret(new['optimized_instructions'],initial,semantics))
        self.assertGreater(checked,30)

    def test_old_candidate_retained_and_independent_rejection_screens(self):
        data=generate_workload(31,'multi_sink_shared',64,4);block=parse_block(data);prepared=PreparedGraph(block)
        old=schedule_branches(block,prepared,time_budget_ms=500)
        new=schedule_branch_copy(data,block,prepared,time_budget_ms=500,beam_width=1,max_states=1)
        verify(data,new);self.assertLessEqual(new['stats']['inserted_copy_count'],old['stats']['inserted_copy_count'])
        for family in ('hazard_multi','butterfly','fanout_diamonds'):
            data=generate_workload(1,family,128,4);block=parse_block(data)
            with self.assertRaises(InfeasibleSchedule):schedule_branch_copy(data,block,PreparedGraph(block))

    def test_large_transition_has_bounded_termination(self):
        data=generate_workload(9,'multi_sink_irregular',1024,4);block=parse_block(data);prepared=PreparedGraph(block)
        branches,_=_branches(block,prepared)
        with self.assertRaises(BudgetExceeded):_transition(block,prepared,branches,0,0,(),0,999999)
