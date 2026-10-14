import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from isa_scheduler.model import InfeasibleSchedule, InvalidBlock, parse_block
from isa_scheduler.scheduler import schedule
from isa_scheduler.verify import interpret, verify


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class SchedulingTests(unittest.TestCase):
    def check(self, data, strategy="ready"):
        result = schedule(parse_block(data), strategy=strategy)
        self.assertTrue(verify(data, result)["valid"])
        return result

    def test_basic_both_strategies_and_register_outputs(self):
        data = fixture("basic.json")
        for strategy in ("stable", "ready"):
            result = self.check(data, strategy)
            self.assertEqual(result["stats"]["inserted_copy_count"], 0)
            self.assertEqual(interpret(result["optimized_instructions"], {"r1": 7, "r2": -3})["out"], -21)

    def test_far_dependency_requires_legal_copy_relay(self):
        data = fixture("far-dependency.json")
        result = self.check(data, "stable")
        self.assertGreater(result["stats"]["inserted_copy_count"], 0)
        self.assertEqual(interpret(data["instructions"], {"a": 3, "b": 2}),
                         interpret(result["optimized_instructions"], {"a": 3, "b": 2}))

    def test_exact_max_distance_is_allowed(self):
        data = fixture("far-dependency.json")
        data["instructions"].pop(4)
        data["instructions"][4]["inputs"] = ["t#4", "t#1"]
        result = self.check(data, "stable")
        self.assertEqual(result["stats"]["inserted_copy_count"], 0)
        self.assertIn("t#4", result["optimized_instructions"][4]["inputs"])

    def test_duplicate_operand_counts_one_consuming_instruction(self):
        data = {"block_id": "duplicate", "bit_width": 2, "instructions": [
            {"id": 0, "op": "GET", "reg": "a"},
            {"id": 1, "op": "ADD", "inputs": ["t#1", "t#1"]},
            {"id": 2, "op": "SET", "reg": "out", "inputs": ["t#1"]}]}
        result = self.check(data)
        self.assertEqual(interpret(result["optimized_instructions"], {"a": 11})["out"], 22)

    def test_register_read_write_hazard(self):
        data = fixture("register-hazard.json")
        for strategy in ("stable", "ready"):
            result = self.check(data, strategy)
            actual = interpret(result["optimized_instructions"], {"a": 3})
            self.assertEqual(actual["a"], 6)
            self.assertEqual(actual["out"], 36)

    def test_capacity_failure_terminates(self):
        data = fixture("infeasible-window.json")
        for strategy in ("stable", "ready"):
            with self.assertRaises(InfeasibleSchedule):
                schedule(parse_block(data), strategy=strategy)

    def test_wider_window_recovers_capacity_fixture(self):
        data = fixture("infeasible-window.json")
        data["bit_width"] = 3
        self.check(data)

    def test_mutated_operand_is_detected(self):
        data = fixture("basic.json")
        result = self.check(data)
        result["optimized_instructions"][2]["inputs"] = ["t#1", "t#1"]
        with self.assertRaisesRegex(InvalidBlock, "Symbolic equivalence"):
            verify(data, result)

    def test_website_illustrative_copy_example_is_not_equivalent(self):
        data = fixture("basic.json")
        data["instructions"].pop()
        illustration = {"block_id": data["block_id"], "optimized_instructions": [
            {"id": 0, "op": "GET", "reg": "r1"},
            {"id": 1, "op": "GET", "reg": "r2"},
            {"id": 2, "op": "COPY", "source": "t#1"},
            {"id": 3, "op": "MULW", "inputs": ["t#1", "t#2"]}]}
        with self.assertRaisesRegex(InvalidBlock, "Symbolic equivalence"):
            verify(data, illustration)

    def test_validator_rejects_out_of_window(self):
        data = fixture("far-dependency.json")
        result = {"block_id": data["block_id"], "optimized_instructions": data["instructions"]}
        with self.assertRaisesRegex(InvalidBlock, "unreachable"):
            verify(data, result)

    def test_parser_rejects_bad_references_and_unknown_ops(self):
        source = fixture("basic.json")
        for token in ("t#0", "t#-1", "t#3", "r1", None):
            data = copy.deepcopy(source)
            data["instructions"][2]["inputs"][0] = token
            with self.assertRaises(InvalidBlock):
                parse_block(data)
        data = copy.deepcopy(source)
        data["instructions"][2]["op"] = "UNCONFIRMED"
        with self.assertRaises(InvalidBlock):
            parse_block(data)

    def test_all_supported_widths(self):
        for bits in range(2, 6):
            data = fixture("far-dependency.json")
            data["bit_width"] = bits
            self.check(data)

    def test_empty_block(self):
        result = self.check({"block_id": "empty", "bit_width": 2, "instructions": []})
        self.assertEqual(result["optimized_instructions"], [])

    def test_original_copy_input(self):
        data = {"block_id": "copy-input", "bit_width": 2, "instructions": [
            {"id": 0, "op": "GET", "reg": "a"},
            {"id": 1, "op": "COPY", "source": "t#1"},
            {"id": 2, "op": "ADD", "inputs": ["t#1", "t#2"]},
            {"id": 3, "op": "SET", "reg": "out", "inputs": ["t#1"]}]}
        result = self.check(data)
        self.assertEqual(result["stats"]["total_copy_count"], 1)
        self.assertEqual(result["stats"]["inserted_copy_count"], 0)

    def test_seeded_random_dags_differential_semantics(self):
        rng = random.Random(18)
        verified = 0
        for trial in range(100):
            rows = [{"id": 0, "op": "GET", "reg": "a"},
                    {"id": 1, "op": "GET", "reg": "b"}]
            for index in range(2, rng.randint(5, 16)):
                a, b = rng.randrange(index), rng.randrange(index)
                rows.append({"id": index, "op": rng.choice(("ADD", "MULW")),
                             "inputs": [f"t#{index-a}", f"t#{index-b}"]})
            rows.append({"id": len(rows), "op": "SET", "reg": "out", "inputs": ["t#1"]})
            data = {"block_id": trial, "bit_width": 3, "instructions": rows}
            for strategy in ("stable", "ready"):
                try:
                    result = schedule(parse_block(data), strategy=strategy)
                except InfeasibleSchedule:
                    continue
                verify(data, result)
                for inputs in ({"a": 2, "b": -3}, {"a": 0, "b": 5}):
                    self.assertEqual(interpret(rows, inputs), interpret(result["optimized_instructions"], inputs))
                verified += 1
        self.assertGreater(verified, 100)

    def test_cli_round_trip_and_invalid_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            target = str(Path(temp) / "optimized.json")
            source = str(FIXTURES / "far-dependency.json")
            commands = [
                ["optimize", source, "--strategy", "stable", "--output", target],
                ["verify", source, target],
                ["benchmark", "--fixtures", str(FIXTURES)],
            ]
            for arguments in commands:
                result = subprocess.run([sys.executable, "-m", "isa_scheduler", *arguments],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable, "-m", "isa_scheduler", "optimize",
                                     str(FIXTURES / "infeasible-window.json"), "--strategy", "stable"],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("No progress", result.stderr)


if __name__ == "__main__":
    unittest.main()

