import unittest
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import IntegerSemantics,interpret,verify
from isa_scheduler.workloads import generate_workload


class NearWindowTests(unittest.TestCase):
    def test_eight_times_guard_rejects_a_constructively_feasible_32_slot_graph(self):
        data=generate_workload(1900001,"near_window_spine",512,5);block=parse_block(data)
        with self.assertRaises(InfeasibleSchedule):schedule_incremental(block,"stable_fast",max_copy_factor=8)
        output=schedule_incremental(block,"stable_fast")
        self.assertGreater(output["stats"]["inserted_copy_count"],8*len(block.instructions))
        self.assertLessEqual(output["stats"]["inserted_copy_count"],(block.window-1)*len(block.instructions))
        verify(data,output)
        registers={row["reg"]:index-13 for index,row in enumerate(data["instructions"]) if row["op"]=="GET"}
        semantics=IntegerSemantics(16,True)
        self.assertEqual(interpret(data["instructions"],registers,semantics),interpret(output["optimized_instructions"],registers,semantics))

    def test_small_windows_still_terminate_and_validate(self):
        for bits in (2,3,4):
            data=generate_workload(1900001,"near_window_spine",128,bits)
            verify(data,schedule_incremental(parse_block(data),"pressure"))
