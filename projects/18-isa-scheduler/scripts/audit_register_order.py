"""Compare all fixed-seed cases rejected by conservative register ordering."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from isa_scheduler.evaluation import evaluate_case, write_report, summarize
from isa_scheduler.fuzz import generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=18)
    parser.add_argument("--output", default="outputs/register-order-audit.json")
    args = parser.parse_args()
    families = ("wide", "branch", "highfanout", "hazard")
    records, audit_cases = [], []
    for case in range(args.count):
        family = families[case % 4]
        data = generate(args.seed + case, family, 2 + ((case // 4) % 4))
        conservative, _ = evaluate_case(data, "auto", source=f"audit:{case}", seed=args.seed + case,
                                        memory_order="conservative", time_budget_ms=100)
        if conservative["status"] != "proven_infeasible_under_model":
            continue
        hazard, result = evaluate_case(data, "auto", source=f"audit:{case}", seed=args.seed + case,
                                      memory_order="hazard", time_budget_ms=100)
        conservative["strategy"] = "auto_conservative"
        hazard["strategy"] = "auto_hazard"
        records.extend((conservative, hazard))
        audit_cases.append({"seed": args.seed + case, "family": family, "input": data,
                            "hazard_status": hazard["status"],
                            "verified_hazard_output": result,
                            "attribution": "artificial cross-register ordering" if result else "not recovered; see bounded proof scope"})
    report = {"dataset": "synthetic register ordering audit; not original-problem infeasibility proof",
              "seed": args.seed, "scanned_cases": args.count,
              "conservative_model_infeasible": len(audit_cases),
              "hazard_model_recovered": sum(c["hazard_status"] == "verified" for c in audit_cases),
              "cases": audit_cases, "summary": summarize(records), "records": records}
    write_report(report, args.output)
    print({"report": args.output, "recovered": report["hazard_model_recovered"],
           "conservative_infeasible": report["conservative_model_infeasible"]})


if __name__ == "__main__":
    main()
