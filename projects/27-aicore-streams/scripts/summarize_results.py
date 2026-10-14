"""Summarize measured local benchmark results; no official-score inference."""
from __future__ import annotations
import argparse
import json
import platform
import statistics
from collections import defaultdict
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--results",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=json.loads(args.results.read_text(encoding="utf-8"))
    rows=result["cases"]
    grouped=defaultdict(list)
    for row in rows:
        grouped[row["n"]].append(row)
    summary={"scope":"self-generated local tests; no official hidden-test claim",
             "platform":platform.platform(),"summary":result["summary"],
             "returned_plan_model_agreements":sum(r["plan"] is not None and r["models_equal"] for r in rows),
             "expected_infeasible_cases":sum(not r["expected_feasible"] for r in rows),
             "official_example_solver_results":[{k:r[k] for k in ["name","T","peak_memory","solve_us"]} for r in rows if r["name"].startswith("official_")],
             "scales":[]}
    for n,group in sorted(grouped.items()):
        feasible=[r for r in group if r["expected_feasible"]]
        times=[r["solve_us"] for r in group]
        summary["scales"].append({"n":n,"cases":len(group),"passed":sum(r["pass"] for r in group),
                                  "solve_us_median":statistics.median(times),"solve_us_max":max(times),
                                  "solve_us_mean":round(statistics.mean(times),2),
                                  "candidates_max":max(r["candidates"] for r in group),
                                  "T_max":max((r["T"] for r in feasible),default=0),
                                  "peak_max":max((r["peak_memory"] for r in feasible),default=0)})
    args.output.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
