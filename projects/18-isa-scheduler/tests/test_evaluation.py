import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from isa_scheduler.evaluation import batch, evaluate_case, summarize, write_report
from isa_scheduler.fuzz import generate, minimize_dead_nodes, run_fuzz
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, InvalidBlock, parse_block
from isa_scheduler.optimizer import optimize
from isa_scheduler.scheduler import schedule
from isa_scheduler.search import search
from isa_scheduler.verify import IntegerSemantics, interpret, verify


ROOT = Path(__file__).resolve().parents[1]


class ExtendedTests(unittest.TestCase):
    def test_exact_oracle_known_minimum_one_copy(self):
        data = json.loads((ROOT / "fixtures/far-dependency.json").read_text())
        result = search(parse_block(data, "conservative"), time_budget_ms=1000)
        verify(data, result)
        self.assertEqual(result["stats"]["inserted_copy_count"], 1)
        self.assertEqual(result["stats"]["search"]["outcome"], "optimal_under_model")

    def test_exact_oracle_proves_capacity_case_in_its_model(self):
        data = json.loads((ROOT / "fixtures/infeasible-window.json").read_text())
        with self.assertRaisesRegex(InfeasibleSchedule, "proven_infeasible_under_model"):
            search(parse_block(data, "conservative"), time_budget_ms=1000, exact_max_nodes=13)

    def test_search_state_budget_is_separate_and_retains_incumbent(self):
        data = json.loads((ROOT / "fixtures/far-dependency.json").read_text())
        block = parse_block(data, "conservative")
        with self.assertRaises(BudgetExceeded):
            search(block, max_states=1, time_budget_ms=1000)
        result = search(block, schedule(block), max_states=1, time_budget_ms=1000)
        verify(data, result)
        self.assertEqual(result["stats"]["search"]["outcome"], "state_budget_exhausted")

    def test_time_budget_and_exact_size_boundary(self):
        data = generate(18, "branch", 2)
        with self.assertRaises(BudgetExceeded):
            search(parse_block(data), time_budget_ms=0)
        data["instructions"] = [{"id": i, "op": "GET", "reg": f"r{i}"} for i in range(11)]
        with self.assertRaisesRegex(BudgetExceeded, "limited to 10"):
            search(parse_block(data))

    def test_verified_portfolio_recovers_stable_failure(self):
        data = generate(19, "branch", 2)
        with self.assertRaises(InfeasibleSchedule):
            schedule(parse_block(data), "stable")
        result = optimize(data, "auto", time_budget_ms=1000)
        verify(data, result)
        self.assertEqual(result["stats"]["search"]["outcome"], "optimal_under_model")

    def test_independent_register_reads_reorder_and_remove_artificial_copy(self):
        data = json.loads((ROOT / "fixtures/far-dependency.json").read_text())
        result = search(parse_block(data, "hazard"), time_budget_ms=1000)
        verify(data, result)
        self.assertEqual(result["stats"]["inserted_copy_count"], 0)
        self.assertEqual(result["stats"]["search"]["memory_order"], "hazard")

    def test_register_dependencies_include_raw_war_waw_without_cross_register_edges(self):
        rows = [{"id": 0, "op": "GET", "reg": "a"},
                {"id": 1, "op": "GET", "reg": "b"},
                {"id": 2, "op": "ADD", "inputs": ["t#1", "t#1"]},
                {"id": 3, "op": "SET", "reg": "a", "inputs": ["t#1"]},
                {"id": 4, "op": "GET", "reg": "a"},
                {"id": 5, "op": "SET", "reg": "a", "inputs": ["t#3"]},
                {"id": 6, "op": "GET", "reg": "a"}]
        block = parse_block({"block_id": "hazards", "bit_width": 3, "instructions": rows})
        self.assertEqual(block.instructions[1].order_deps, ())
        self.assertEqual(block.instructions[3].order_deps, (0,))
        self.assertEqual(block.instructions[4].order_deps, (3,))
        self.assertEqual(block.instructions[5].order_deps, (3, 4))
        self.assertEqual(block.instructions[6].order_deps, (5,))

    def test_verifier_accepts_cross_register_reorder_and_rejects_real_hazard(self):
        original = json.loads((ROOT / "fixtures/official-known-input.json").read_text())
        reordered = {"block_id": original["block_id"], "optimized_instructions": [
            {"id": 0, "op": "GET", "reg": "r2"}, {"id": 1, "op": "GET", "reg": "r1"},
            {"id": 2, "op": "MULW", "inputs": ["t#2", "t#1"]}]}
        self.assertTrue(verify(original, reordered)["valid"])
        original = json.loads((ROOT / "fixtures/register-hazard.json").read_text())
        corrupted = {"block_id": original["block_id"], "optimized_instructions": [
            {"id": 0, "op": "GET", "reg": "a"}, {"id": 1, "op": "GET", "reg": "a"},
            {"id": 2, "op": "ADD", "inputs": ["t#2", "t#2"]},
            {"id": 3, "op": "SET", "reg": "a", "inputs": ["t#1"]},
            {"id": 4, "op": "MULW", "inputs": ["t#3", "t#3"]},
            {"id": 5, "op": "SET", "reg": "out", "inputs": ["t#1"]}]}
        with self.assertRaises(InvalidBlock):
            verify(original, corrupted)

    def test_beam_never_claims_global_optimum_after_pruning(self):
        data = generate(19, "branch", 2)
        result = optimize(data, "beam", time_budget_ms=1000, beam_width=1)
        verify(data, result)
        self.assertNotEqual(result["stats"]["search"]["outcome"], "optimal_under_model")

    def test_fixed_width_wrap_signed_unsigned_and_trap(self):
        rows = [{"id": 0, "op": "GET", "reg": "a"},
                {"id": 1, "op": "ADD", "inputs": ["t#1", "t#1"]},
                {"id": 2, "op": "SET", "reg": "out", "inputs": ["t#1"]}]
        self.assertEqual(interpret(rows, {"a": 127}, IntegerSemantics(8, True))["out"], -2)
        self.assertEqual(interpret(rows, {"a": 255}, IntegerSemantics(8, False))["out"], 254)
        with self.assertRaisesRegex(InvalidBlock, "overflow"):
            interpret(rows, {"a": 127}, IntegerSemantics(8, True, "error"))
        with self.assertRaises(InvalidBlock):
            IntegerSemantics(0)

    def test_big_integer_guard_does_not_skip_fixed_width_checks(self):
        rows = [{"id": 0, "op": "GET", "reg": "a"}]
        for i in range(1, 20):
            rows.append({"id": i, "op": "MULW", "inputs": ["t#1", "t#1"]})
        rows.append({"id": 20, "op": "SET", "reg": "out", "inputs": ["t#1"]})
        data = {"block_id": "huge-integer", "bit_width": 2, "instructions": rows}
        row, result = evaluate_case(data)
        self.assertIsNotNone(result)
        self.assertEqual(row["numeric_configurations"], 2)
        self.assertEqual(len(row["numeric_skipped"]), 1)

    def test_auto_uses_beam_for_larger_graph_and_validates_output(self):
        data = json.loads((ROOT / "fixtures/large-highfanout.json").read_text())
        result = optimize(data, "auto", time_budget_ms=1000)
        verify(data, result)
        self.assertTrue(any(a["strategy"] == "beam" for a in result["stats"]["attempts"]))

    def test_unconfirmed_opcodes_and_fields_fail_closed(self):
        data = generate(18, "hazard", 2)
        data["instructions"][2]["op"] = "SLL"
        with self.assertRaisesRegex(InvalidBlock, "Unsupported"):
            parse_block(data)
        data = generate(18, "hazard", 2)
        data["hidden_side_effect"] = True
        with self.assertRaisesRegex(InvalidBlock, "Unknown"):
            parse_block(data)

    def test_all_families_all_widths_double_validation(self):
        for family in ("wide", "branch", "highfanout", "hazard"):
            for bits in range(2, 6):
                row, result = evaluate_case(generate(100, family, bits), time_budget_ms=1000)
                if result:
                    self.assertEqual(row["status"], "verified")
                    self.assertEqual(row["numeric_configurations"], 3)
                else:
                    self.assertEqual(row["status"], "proven_infeasible_under_model")

    def test_batch_jsonl_invalid_input_and_csv_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "inputs.jsonl"
            source.write_text(json.dumps(generate(20, "hazard", 2)) + "\nINVALID\n", encoding="utf-8")
            report = batch(source, ("auto",))
            self.assertEqual(report["summary"]["auto"]["status_counts"], {"invalid_input": 1, "verified": 1})
            output = Path(temp) / "report.json"
            write_report(report, output)
            self.assertTrue(output.with_suffix(".csv").exists())
            self.assertIn("p99", report["summary"]["auto"]["latency_ms_all_inputs"]["schedule_ms"])

    def test_corrupt_candidate_is_a_verification_failure_not_unsolved(self):
        data = json.loads((ROOT / "fixtures/official-known-input.json").read_text())
        corrupted = schedule(parse_block(data))
        corrupted["optimized_instructions"][2]["inputs"] = ["t#1", "t#1"]
        with patch("isa_scheduler.optimizer.schedule", return_value=corrupted):
            record, result = evaluate_case(data, "ready")
        self.assertIsNone(result)
        self.assertEqual(record["status"], "verification_failure")
        self.assertEqual(summarize([record])["ready"]["correctness_rate_emitted_outputs"], 0)

    def test_batch_cli_semantic_failure_returns_nonzero_and_preserves_report(self):
        from isa_scheduler.__main__ import main
        report = {"summary": {}, "records": [{"strategy": "auto", "status": "verification_failure"}]}
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "bad.json"
            with patch("sys.argv", ["isa_scheduler", "batch", "unused", "--output", str(destination)]):
                with patch("isa_scheduler.__main__.batch", return_value=report):
                    self.assertEqual(main(), 4)
            self.assertTrue(destination.exists())

    def test_strict_cli_export_schema_and_budget_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "strict.json"
            command = [sys.executable, "-m", "isa_scheduler", "optimize",
                       str(ROOT / "fixtures/official-known-input.json"), "--strict", "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(json.loads(output.read_text())), {"block_id", "optimized_instructions"})
            result = subprocess.run([*command[:5], "--time-budget-ms", "0.0000001"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)

    def test_deterministic_corpus_hash_and_small_fuzz_report(self):
        self.assertEqual(generate(18, "wide", 2), generate(18, "wide", 2))
        with tempfile.TemporaryDirectory() as temp:
            report = run_fuzz(32, 18, temp, time_budget_ms=1000)
            self.assertEqual(report["case_count"], 32)
            self.assertEqual(len(report["records"]), 96)
            self.assertEqual(report["summary"]["auto"]["correctness_rate_emitted_outputs"], 1)


if __name__ == "__main__":
    unittest.main()

