import unittest
from isa_scheduler.branch_dp import schedule_branches
from isa_scheduler.incremental import PreparedGraph
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import IntegerSemantics,interpret,verify
from isa_scheduler.workloads import generate_workload
from isa_scheduler.optimizer import optimize


class BranchDPTests(unittest.TestCase):
    def test_structural_branches_independent_outputs(self):
        successful=0
        for family in ("multi_sink_shared","multi_sink_irregular","cross_group_shared"):
            for seed in range(990001,990021):
                for bits in range(2,6):
                    data=generate_workload(seed,family,128,bits);block=parse_block(data)
                    try:result=schedule_branches(block,PreparedGraph(block),time_budget_ms=1000)
                    except InfeasibleSchedule:continue
                    verify(data,result)
                    registers={row["reg"]:3*i-7 for i,row in enumerate(data["instructions"]) if row["op"]=="GET"}
                    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False)):
                        self.assertEqual(interpret(data["instructions"],registers,semantics),interpret(result["optimized_instructions"],registers,semantics))
                    successful+=1
        self.assertGreater(successful,180)

    def test_non_spines_and_register_hazards_are_rejected(self):
        for family in ("matrix_product_tile","hazard_multi","fanout_diamonds","butterfly"):
            block=parse_block(generate_workload(1,family,64,2))
            with self.assertRaises(InfeasibleSchedule):schedule_branches(block,PreparedGraph(block))

    def test_unused_gets_are_preserved_and_portfolio_keeps_verified_candidates(self):
        for family in ("multi_sink_shared","multi_sink_irregular"):
            for seed in range(1500001,1500005):
                for bits in (3,4,5):
                    data=generate_workload(seed,family,128,bits)
                    # Insert an unused unique-register GET into the beginning;
                    # relative distances between existing instructions remain.
                    data["instructions"].insert(0,{"id":-1,"op":"GET","reg":"unused"})
                    before=optimize(data,"auto",time_budget_ms=1000)
                    after=optimize(data,"branch_portfolio",time_budget_ms=1000)
                    verify(data,after)
                    self.assertLessEqual(after["stats"]["inserted_copy_count"],before["stats"]["inserted_copy_count"])
                    self.assertEqual(sum(row.get("reg")=="unused" for row in after["optimized_instructions"]),1)
