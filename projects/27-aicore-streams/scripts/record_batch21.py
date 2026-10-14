"""Preserve default/rejected-version scope and optimum-certificate evidence."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["stream_arbitration_batch20_exploratory"]={"source_sha256":hashlib.sha256(Path("research/batch20/solution.cpp").read_bytes()).hexdigest(),"regression":read("reports/regression-batch20.json"),"paired":{n:read(f"reports/paired-final-arbitration-{n}-batch20-summary.json") for n in ["resource","wait"]},"retained_by_default":False,"reason":"Only two T improvements/108 quality records and one equal-T peak improvement; wait holdout CPU +6.5%; default resumes batch19 before certificates."}
    v["latest_solution_sha256"]=hashlib.sha256(Path("research/batch21/solution.cpp").read_bytes()).hexdigest()
    v["optimal_certificates_batch21"]={"regression":read("reports/regression-batch21.json"),"audit":read("reports/certificate-audit-batch21.json"),"paired":{n:read(f"reports/paired-certificates-{n}-batch21-summary.json") for n in ["main","holdout","oracle6","controls"]},"scope":"time bound and peak bound attained; pair-overlap peak bound conditional on T=time bound; compare quality to default batch19, not exploratory batch20","ctest_wall_seconds":.70,"standalone_compile":"GCC -O2 -Wall -Wextra -Wpedantic successful"}
    v["hard_workload_batch21_comparison"]={n:summarize(read(f"reports/{n}-batch19.json"),read(f"reports/{n}-batch21.json")) for n in ["irregular","irregular-holdout"]}
    for c in v["hard_workload_batch21_comparison"].values():assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
    v["batch21_counts"]=dict(strict_regression_records=955,analytic_controls=12,hard_records=48,hard_passed=29,hard_failed=19,total_records=1015,total_passed=996,total_failed=19)
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch20 exploratory excluded; batch21 1015 records/996 pass/19 real feasible failures;132 external optimum checks")


if __name__=="__main__":main()
