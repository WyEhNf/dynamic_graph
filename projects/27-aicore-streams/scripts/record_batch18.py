"""Record common-case quality portfolio and orthogonal workload limits."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch18"]=read("reports/regression-batch18.json")
    v["core_priority_batch18"]={name:read(f"reports/paired-{name}-batch18-summary.json") for name in ["resource-corepriority","resource-corepriority-holdout","corepacking","corepacking-holdout"]}
    v["hard_workload_batch18_comparison"]={}
    for name,label in [("irregular","partition"),("irregular-holdout","partition-holdout")]:
        c=summarize(read(f"reports/paired-{label}-batch17-1-after.json"),read(f"reports/{name}-batch18.json"))
        assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        v["hard_workload_batch18_comparison"][name]=c
    v["batch18_counts"]=dict(strict_regression_records=919,hard_records=48,hard_passed=29,hard_failed=19,total_records=967,total_passed=948,total_failed=19)
    v["standalone_and_ctest_batch18"]=dict(ctest="3/3",ctest_wall_seconds=0.71,standalone="GCC -O2 no warnings")
    v["timing_caution_batch18"]="New four candidates add work. Corepacking before measurements suffered substantial host scheduling noise; apparent solver-time decreases are not attributed to algorithm acceleration. Resource-DAG paired increases are reported separately."
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch18:919 strict passed; 14/72 common T improvements,3 peak; 19 hard failures remain")


if __name__=="__main__":
    main()
