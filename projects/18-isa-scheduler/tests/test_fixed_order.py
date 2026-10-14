from dataclasses import replace
import unittest

from isa_scheduler.fixed_order import solve_fixed_order
from isa_scheduler.fuzz import generate
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, parse_block
from isa_scheduler.scheduler import schedule
from isa_scheduler.search import search
from isa_scheduler.verify import IntegerSemantics, interpret, verify
from isa_scheduler.workloads import generate_workload


class FixedOrderTests(unittest.TestCase):
    def test_independent_full_state_oracle_for_300_orders(self):
        for seed in range(910001, 910301):
            family = ("wide", "branch", "highfanout", "hazard")[seed % 4]
            data = generate(seed, family, 2+(seed % 2))
            block = parse_block(data)
            # An independent reference implementation still enumerates masks
            # and live identities; add a dependency chain to force one order.
            chained = replace(block, instructions=tuple(
                replace(node, order_deps=tuple(sorted(set(node.order_deps) | ({node.index-1} if node.index else set()))))
                for node in block.instructions))
            solutions = []
            for function in (lambda: search(chained, time_budget_ms=1000, max_states=100000),
                             lambda: solve_fixed_order(block, list(range(len(block.instructions))),
                                                       time_budget_ms=1000, max_states=100000)):
                try: solutions.append(function())
                except InfeasibleSchedule: solutions.append(None)
            self.assertEqual(solutions[0] is None, solutions[1] is None, seed)
            if solutions[1] is not None:
                self.assertEqual(solutions[0]["stats"]["inserted_copy_count"],
                                 solutions[1]["stats"]["inserted_copy_count"], seed)
                verify(data, solutions[1])
                registers = {row["reg"]: i+3 for i,row in enumerate(data["instructions"]) if row["op"] == "GET"}
                for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False)):
                    self.assertEqual(interpret(data["instructions"], registers, semantics),
                                     interpret(solutions[1]["optimized_instructions"], registers, semantics))

    def test_budget_retains_existing_candidate_and_rejects_wrong_order(self):
        data = generate_workload(910001, "ladder_diamond", 64, 2)
        block = parse_block(data)
        incumbent = schedule(block, "stable")
        result = solve_fixed_order(block, incumbent["stats"]["original_order"], incumbent,
                                   time_budget_ms=1000, max_states=1)
        self.assertEqual(result["optimized_instructions"], incumbent["optimized_instructions"])
        self.assertEqual(result["stats"]["fixed_order_search"]["outcome"], "state_budget_exhausted")
        with self.assertRaises(ValueError): solve_fixed_order(block, list(reversed(range(len(block.instructions)))), incumbent)
        with self.assertRaises(ValueError): solve_fixed_order(block, list(range(len(block.instructions))), time_budget_ms=0)

    def test_input_copy_duplicate_operand_and_register_hazards(self):
        data = {"block_id":"copy-hazard", "bit_width":2, "instructions":[
            {"op":"GET", "reg":"a"}, {"op":"COPY", "source":"t#1"},
            {"op":"ADD", "inputs":["t#1", "t#1"]},
            {"op":"SET", "reg":"a", "inputs":["t#1"]},
            {"op":"GET", "reg":"a"}, {"op":"MULW", "inputs":["t#1", "t#5"]},
            {"op":"SET", "reg":"out", "inputs":["t#1"]}]}
        block = parse_block(data)
        result = solve_fixed_order(block, list(range(len(block.instructions))))
        verify(data,result)
        self.assertEqual(result["stats"]["total_copy_count"], result["stats"]["inserted_copy_count"]+1)

