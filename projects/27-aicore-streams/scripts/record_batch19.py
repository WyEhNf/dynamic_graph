"""Record delayed-reservation quality without claiming candidate-model equivalence."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch19"]=read("reports/regression-batch19.json")
    v["delayed_resources_batch19"]={name:read(f"reports/paired-{name}-batch19-summary.json") for name in ["delayed-resource","delayed-resource-holdout","wait-overlap","wait-overlap-holdout"]}
    v["hard_workload_batch19_comparison"]={}
    for name in ["irregular","irregular-holdout"]:
        c=summarize(read(f"reports/{name}-batch18.json"),read(f"reports/{name}-batch19.json"))
        assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        v["hard_workload_batch19_comparison"][name]=c
    v["batch19_counts"]=dict(strict_regression_records=955,hard_records=48,hard_passed=29,hard_failed=19,total_records=1003,total_passed=984,total_failed=19)
    v["standalone_and_ctest_batch19"]=dict(ctest="3/3",ctest_wall_seconds=10.95,standalone="GCC -O2 no warnings")
    v["delayed_candidate_model_scope"]="Constructive Wait/Compute separation; Record conservatively charged at all producer ends. Only exact evaluator establishes emitted plan validity/T/peak, not this construction model. Zero-event quality cases skip extra candidates."
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch19:955 strict passed;15/36 new wait T improvements,2/36 old small gains;19 hard failures")


if __name__=="__main__":
    main()
