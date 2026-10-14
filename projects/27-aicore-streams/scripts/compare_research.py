"""Compare benchmark reports by case; do not turn absent solutions into zero T."""
import argparse
import json
import statistics
from pathlib import Path


def summarize(before, after):
    old = {x["name"]: x for x in before["cases"]}
    common = [(old[x["name"]], x) for x in after["cases"] if x["pass"] and old[x["name"]]["pass"] and x["valid"] and old[x["name"]]["valid"]]
    result=dict(before=before["summary"], after=after["summary"], common_cases=len(common),
                common_solve_us_before=sum(x["solve_us"] for x, y in common),
                common_solve_us_after=sum(y["solve_us"] for x, y in common),
                improved_T=sum(y["T"] < x["T"] for x, y in common),
                regressed_T=sum(y["T"] > x["T"] for x, y in common),
                improved_peak_at_equal_T=sum(y["T"] == x["T"] and y["peak_memory"] < x["peak_memory"] for x, y in common),
                regressed_peak_at_equal_T=sum(y["T"] == x["T"] and y["peak_memory"] > x["peak_memory"] for x, y in common),
                recovered=[x["name"] for x in after["cases"] if x["pass"] and not old[x["name"]]["pass"]],
                lost=[x["name"] for x in after["cases"] if not x["pass"] and old[x["name"]]["pass"]],
                model_disagreements=sum(not x["models_equal"] for x in after["cases"]),
                duplicates=sum(x.get("duplicate_candidates", 0) for x in after["cases"]),
                scales=[dict(n=n, median_us=statistics.median(x["solve_us"] for x in after["cases"] if x["n"] == n),
                             max_us=max(x["solve_us"] for x in after["cases"] if x["n"] == n))
                        for n in sorted({x["n"] for x in after["cases"]})])
    measured=[(x,y) for x,y in common if x.get("solve_thread_cpu_us",-1)>=0 and y.get("solve_thread_cpu_us",-1)>=0]
    result.update(common_thread_cpu_measured_cases=len(measured),common_thread_cpu_us_before=sum(x["solve_thread_cpu_us"] for x,y in measured) if measured else None,common_thread_cpu_us_after=sum(y["solve_thread_cpu_us"] for x,y in measured) if measured else None)
    for label,data in [("before",before),("after",after)]:
        result["all_solve_us_"+label]=sum(x["solve_us"] for x in data["cases"])
        cpu=[x.get("solve_thread_cpu_us",-1) for x in data["cases"]]
        result["all_thread_cpu_us_"+label]=sum(cpu) if all(x>=0 for x in cpu) else None
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = summarize(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
