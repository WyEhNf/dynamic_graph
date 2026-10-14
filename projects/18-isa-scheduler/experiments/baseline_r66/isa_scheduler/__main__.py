import argparse
import json
from pathlib import Path
import sys

from .evaluation import batch, write_report
from .fuzz import run_fuzz
from .model import BudgetExceeded, InfeasibleSchedule, InvalidBlock
from .optimizer import optimize
from .verify import verify


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def budget_arguments(parser, default=100):
    parser.add_argument("--time-budget-ms", type=float, default=default)
    parser.add_argument("--max-states", type=int, default=30000)
    parser.add_argument("--memory-order", choices=("hazard", "conservative"), default="hazard")


def main():
    parser = argparse.ArgumentParser(description="Problem 18 bounded-distance ISA scheduler")
    commands = parser.add_subparsers(dest="command", required=True)
    solve = commands.add_parser("optimize", help="Schedule and independently verify one block")
    solve.add_argument("input")
    solve.add_argument("--output")
    solve.add_argument("--strategy", choices=("ready", "stable", "auto", "exact", "beam", "pressure", "demand", "incremental", "stable_fast", "ready_fast", "affinity", "deadline", "age_first", "size_pressure", "forest_work", "branch_dp", "branch_portfolio", "forest_portfolio", "alias_pressure", "local_swap", "local_relocate", "minor_portfolio", "branch_copy"), default="auto")
    solve.add_argument("--strict", action="store_true", help="Export only official core output keys")
    budget_arguments(solve)
    check = commands.add_parser("verify", help="Verify an existing optimized JSON")
    check.add_argument("input")
    check.add_argument("optimized")
    bench = commands.add_parser("benchmark", help="Compare strategies on local fixtures")
    bench.add_argument("--fixtures", default="fixtures")
    bench.add_argument("--output")
    bench.add_argument("--csv")
    bench.add_argument("--strategies", default="stable,ready,auto")
    budget_arguments(bench)
    many = commands.add_parser("batch", help="Evaluate directory, JSON, or JSONL")
    many.add_argument("input")
    many.add_argument("--output", default="outputs/batch-report.json")
    many.add_argument("--csv")
    many.add_argument("--strategies", default="stable,ready,auto")
    budget_arguments(many)
    fuzz = commands.add_parser("fuzz", help="Generate and differentially evaluate seeded small DAGs")
    fuzz.add_argument("--count", type=int, default=10000)
    fuzz.add_argument("--seed", type=int, default=18)
    fuzz.add_argument("--output", default="outputs/fuzz-10000.json")
    fuzz.add_argument("--csv")
    fuzz.add_argument("--counterexamples", default="outputs/counterexamples")
    budget_arguments(fuzz, 100)
    args = parser.parse_args()
    try:
        report = False
        if args.command == "optimize":
            original = read_json(args.input)
            result = optimize(original, args.strategy, time_budget_ms=args.time_budget_ms, max_states=args.max_states, memory_order=args.memory_order)
            result["stats"]["verification"] = verify(original, result)
            if args.strict:
                result = {key: result[key] for key in ("block_id", "optimized_instructions")}
        elif args.command == "verify":
            result = verify(read_json(args.input), read_json(args.optimized))
        elif args.command == "fuzz":
            result = run_fuzz(args.count, args.seed, args.counterexamples, args.time_budget_ms, args.max_states, args.memory_order)
            report = True
        else:
            strategies = tuple(args.strategies.split(","))
            if not strategies or any(s not in ("stable", "ready", "auto", "exact", "beam", "pressure", "demand", "incremental", "stable_fast", "ready_fast", "affinity", "deadline", "age_first", "size_pressure", "forest_work", "branch_dp", "branch_portfolio", "forest_portfolio", "alias_pressure", "local_swap", "local_relocate", "minor_portfolio", "branch_copy") for s in strategies):
                raise InvalidBlock("Invalid strategy list")
            result = batch(args.fixtures if args.command == "benchmark" else args.input,
                           strategies, args.time_budget_ms, args.max_states, args.memory_order)
            report = True
        if getattr(args, "output", None):
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if report:
                write_report(result, destination, args.csv)
                print(json.dumps({"report": str(destination), "summary": result["summary"]}, ensure_ascii=False))
            else:
                destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if report and any(row["status"] == "verification_failure" for row in result["records"]):
            return 4
        return 0
    except BudgetExceeded as exc:
        print(f"BUDGET_EXHAUSTED: {exc}", file=sys.stderr)
        return 3
    except (InvalidBlock, InfeasibleSchedule, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

