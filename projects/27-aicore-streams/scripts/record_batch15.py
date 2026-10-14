"""Record independent six-node oracle, preserving unresolved hard graph failures."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch15"]=read("reports/regression-batch15.json")
    v["oracle6_batch15"]={name:read(f"reports/paired-{name}-batch15-summary.json") for name in ["oracle6","oracle6-holdout"]}
    v["oracle6_independent_cost"]=[read(f"data/parallel-oracle6{suffix}-cost.json") for suffix in ["","-holdout"]]
    v["hard_workload_batch15_comparison"]={}
    for name in ["irregular","irregular-holdout"]:
        c=summarize(read(f"reports/paired-{name}-batch14-1-after.json"),read(f"reports/{name}-batch15.json"))
        assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        v["hard_workload_batch15_comparison"][name]=c
    v["batch15_counts"]=dict(passing_regression_records=859,hard_records=48,hard_passed=23,hard_failed=25,total_records=907,total_passed=882,total_failed=25)
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch15:859 regression records passed; 24/24 six-node exact; 25 hard failures remain")


if __name__=="__main__":
    main()
