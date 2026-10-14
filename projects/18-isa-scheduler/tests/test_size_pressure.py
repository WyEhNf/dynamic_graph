import unittest
from isa_scheduler.incremental import PreparedGraph,schedule_incremental
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import IntegerSemantics,interpret,verify
from isa_scheduler.workloads import generate_workload


class SizePressureTests(unittest.TestCase):
    def test_equal_demand_long_branch_first_avoids_relay(self):
        rows=[{"op":"GET","reg":"a"},{"op":"GET","reg":"b"}]
        for _ in range(60):rows.append({"op":"ADD","inputs":["t#1","t#1"]})
        index=len(rows)
        rows.append({"op":"MULW","inputs":[f"t#{index}","t#1"]})
        rows.append({"op":"SET","reg":"out","inputs":["t#1"]})
        data={"block_id":"unequal-work-equal-demand","bit_width":2,"instructions":rows}
        block=parse_block(data)
        old=schedule_incremental(block,"pressure")
        new=schedule_incremental(block,"size_pressure")
        verify(data,old);verify(data,new)
        self.assertGreater(old["stats"]["inserted_copy_count"],0)
        self.assertEqual(new["stats"]["inserted_copy_count"],0)

    def test_ragged_and_padded_structure_seeds_and_reuse(self):
        successes=0
        for family in ("ragged_tree","padded_tree","sparse_shared","hazard_multi"):
            for seed in range(930001,930011):
                for bits in (2,3,4,5):
                    data=generate_workload(seed,family,128,bits)
                    block=parse_block(data);prepared=PreparedGraph(block)
                    try:result=schedule_incremental(block,"size_pressure",prepared=prepared)
                    except InfeasibleSchedule:continue
                    verify(data,result)
                    old=schedule_incremental(block,"pressure",prepared=prepared)
                    verify(data,old)
                    again=schedule_incremental(block,"size_pressure",prepared=prepared)
                    self.assertEqual(result["optimized_instructions"],again["optimized_instructions"])
                    registers={row["reg"]:3+i for i,row in enumerate(data["instructions"]) if row["op"]=="GET"}
                    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False)):
                        self.assertEqual(interpret(data["instructions"],registers,semantics),
                                         interpret(result["optimized_instructions"],registers,semantics))
                    successes+=1
        self.assertGreater(successes,100)
