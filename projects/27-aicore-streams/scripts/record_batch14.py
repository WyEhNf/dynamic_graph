"""Record hard-workload failures explicitly, separately from passing regression."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v = read("docs/validation.json")
    v["latest_solution_sha256"] = hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch14"] = read("reports/regression-batch14.json")
    v["irregular_consumers_batch14"] = {name:read(f"reports/paired-{name}-batch14-summary.json") for name in ["irregular","irregular-holdout","bundle-shortlist","bundle-shortlist-holdout"]}
    unresolved = []
    for name in ["irregular","irregular-holdout"]:
        s=read(f"reports/paired-{name}-batch14-summary.json")
        for run in s["runs"]:
            c=run["comparison"]
            assert c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0 and not c["lost"]
        results=read(s["runs"][0]["after"]["report"])
        unresolved += [x["name"] for x in results["cases"] if not x["pass"]]
    v["known_witness_feasible_unresolved_batch14"] = unresolved
    v["batch14_counts"] = dict(passing_historical_records=835,new_hard_records=48,new_passed=23,new_failed_with_witness=25,total_records=883,total_passed=858,total_failed=25,scope="not an all-passing suite; heuristic no-candidate is not proof of infeasibility")
    v["standalone_and_ctest_batch14"] = dict(ctest="3/3",ctest_wall_seconds=0.93,standalone="GCC -O2, standard library only, no warnings")
    v["batch14_negative"] = dict(complete_all_remaining_consumers_bundle="no extra recovery on 48 graph records; not retained",full_target_scan_frozen="research/batch14-full-scan",probe_reports="irregular*-consumer-close-batch14.json exploratory drafts are not frozen source timing comparisons")
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch14:835 historical passed; 23/48 new hard cases, 25 unresolved retained")


if __name__=="__main__":
    main()
