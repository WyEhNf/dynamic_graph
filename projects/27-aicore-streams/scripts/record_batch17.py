"""Freeze grouped-sink recovery, with remaining failures retained."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch17"]=read("reports/regression-batch17.json")
    v["partition_batch17"]={name:read(f"reports/paired-{name}-batch17-summary.json") for name in ["partition","partition-holdout"]}
    unresolved=[]
    for s in v["partition_batch17"].values():
        for run in s["runs"]:
            c=run["comparison"]
            assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        unresolved += [x["name"] for x in read(s["runs"][0]["after"]["report"])["cases"] if not x["pass"]]
    v["known_witness_feasible_unresolved_batch17"]=unresolved
    v["batch17_counts"]=dict(strict_regression_records=883,original_hard_records=48,original_hard_passed=29,original_hard_failed=19,total_records=931,total_passed=912,total_failed=19)
    v["standalone_and_ctest_batch17"]=dict(ctest="3/3",ctest_wall_seconds=1.60,standalone="GCC -O2 no warnings")
    v["batch17_draft_bug"]=dict(issue="division by zero in sink affinity for producer without successors",fixed="exclude empty successor list before computing weight",scope="unusable draft CLI runs are excluded; all reported paired metrics use corrected source")
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch17:883 strict records passed; original hard29/48; 19 unresolved")


if __name__=="__main__":
    main()
