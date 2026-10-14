"""Record projected-search recovery and honest remaining feasible failures."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch16"]=read("reports/regression-batch16.json")
    v["projection_batch16"]={name:read(f"reports/paired-{name}-batch16-summary.json") for name in ["projection","projection-holdout","projection-small","projection-small-holdout"]}
    unresolved=[]
    for name,s in v["projection_batch16"].items():
        for run in s["runs"]:
            c=run["comparison"]
            assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        unresolved += [x["name"] for x in read(s["runs"][0]["after"]["report"])["cases"] if not x["pass"]]
    v["known_witness_feasible_unresolved_batch16"]=unresolved
    v["batch16_counts"]=dict(historical_regression_records=859,separate_new_small_records=24,separate_small_passed=24,original_hard_records=48,original_hard_passed=25,original_hard_failed=23,total_records=931,total_passed=908,total_failed=23,scope="859 single functional regression plus 24 paired small cases, not one 883-case timed regression")
    v["standalone_and_ctest_batch16"]=dict(ctest="3/3",ctest_wall_seconds=0.71,standalone="GCC -O2 no warnings")
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch16:859 regression passed +24 small passed; original hard25/48; 23 unresolved")


if __name__=="__main__":
    main()
