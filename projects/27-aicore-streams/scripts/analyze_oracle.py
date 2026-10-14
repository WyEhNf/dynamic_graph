"""Measure gaps only against an independently constructed exhaustive oracle."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("suite", type=Path)
    p.add_argument("result", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    cases = {x["name"]: x for x in json.loads(args.suite.read_text())["cases"]}
    rows = []
    for x in json.loads(args.result.read_text())["cases"]:
        oracle = cases[x["name"]]["generation"]
        rows.append(dict(name=x["name"], returned_feasible=x["valid"] and x["pass"], oracle_T=oracle["oracle_T"], oracle_peak=oracle["oracle_peak"], T_gap=x["T"]-oracle["oracle_T"] if x["valid"] else None, peak_gap=x["peak_memory"]-oracle["oracle_peak"] if x["valid"] and x["T"] == oracle["oracle_T"] else None, solve_us=x["solve_us"], plans_evaluated=oracle["plans_evaluated"]))
    maximum_n = max(len(x["nodes"]) for x in cases.values())
    summary = dict(total=len(rows), feasible=sum(x["returned_feasible"] for x in rows), exact_T_and_peak=sum(x["returned_feasible"] and x["T_gap"] == 0 and x["peak_gap"] == 0 for x in rows), independent_oracle_plans=sum(x["plans_evaluated"] for x in rows), scope=f"exhaustive n<={maximum_n}, <=2 streams, explicit direct synchronization only", rows=rows)
    args.output.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!="rows"}))


if __name__ == "__main__":
    main()
