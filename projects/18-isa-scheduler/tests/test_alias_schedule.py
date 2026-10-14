import unittest
from unittest.mock import patch
from isa_scheduler.alias_schedule import ordered_classes
from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify, interpret, IntegerSemantics
from isa_scheduler.workloads import generate_workload


class AliasTests(unittest.TestCase):
    def test_get_set_and_ordered_operands_are_not_merged(self):
        data={"block_id":"scope","bit_width":2,"instructions":[
            {"id":0,"op":"GET","reg":"r"},{"id":1,"op":"GET","reg":"r"},
            {"id":2,"op":"ADD","inputs":["t#2","t#1"]},
            {"id":3,"op":"ADD","inputs":["t#2","t#3"]},
            {"id":4,"op":"SET","reg":"r","inputs":["t#2"]},
            {"id":5,"op":"SET","reg":"r","inputs":["t#3"]}]}
        classes=ordered_classes(parse_block(data))
        self.assertEqual(len(set(classes)),6)
        result=optimize(data,"alias_pressure",time_budget_ms=1000)
        verify(data,result)
        self.assertEqual(len(result["stats"]["original_order"]),6)
        self.assertFalse(result["stats"]["fixed_order_lower_bound_applicable"])

    def test_random_structural_aliases_independent_differential(self):
        successes=0
        for seed in range(80):
            data=generate_workload(seed,"ordered_duplicate_network",64,2+seed%4)
            try:result=optimize(data,"alias_pressure",time_budget_ms=1000)
            except (BudgetExceeded,InfeasibleSchedule):continue
            successes+=1
            verify(data,result)
            for bits in (8,16,32):
                inputs={row["reg"]:seed+3*i+1 for i,row in enumerate(data["instructions"]) if row["op"]=="GET"}
                semantics=IntegerSemantics(bits,True)
                self.assertEqual(interpret(data["instructions"],inputs,semantics),
                                 interpret(result["optimized_instructions"],inputs,semantics))
            self.assertEqual(sorted(result["stats"]["original_order"]),list(range(len(data["instructions"]))))
        self.assertGreaterEqual(successes,50)

    def test_changed_model_never_applies_identity_certificate(self):
        data=generate_workload(100,"ordered_duplicate_network",128,2)
        with patch("isa_scheduler.optimizer.forest_capacity_bound",side_effect=AssertionError("Wrong-model certificate used")):
            try:
                result=optimize(data,"alias_pressure",time_budget_ms=1000)
            except InfeasibleSchedule as exc:
                self.assertNotIn("proven_infeasible_under_model",str(exc))
            else:
                verify(data,result)
                self.assertEqual(result["stats"]["value_identity_model"],"ordered_structural_arithmetic_aliases")

