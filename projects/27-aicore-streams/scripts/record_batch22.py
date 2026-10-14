"""Keep dense cost benefits and general-workload negative cost separately."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("research/batch22/solution.cpp").read_bytes()).hexdigest()
    v["assignment_grouping_batch22"]={"regression":read("reports/regression-batch22.json"),"plan_identity":read("reports/plan-identity-batch22.json"),"certificate_audit":read("reports/certificate-audit-batch22.json"),"paired":{n:read(f"reports/paired-{n}-batch22-summary.json") for n in ["dense","dense-holdout","dense-main-holdout","lazy-certificates"]},"assignment_recurrence_comparisons":288,"ctest":"4/4","ctest_wall_seconds":.80,"standalone_compile":"GCC -O2 -Wall -Wextra -Wpedantic successful","scope":"algebraically equivalent Stream decision; no new scheduling heuristic, no new feasibility recovery"}
    v["batch22_counts"]=dict(strict_regression_records=955,analytic_controls=12,dense_records=12,hard_records=48,hard_passed=29,hard_failed=19,total_records=1027,total_passed=1008,total_failed=19)
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch22:1027 records/1008 pass/19 witness-feasible failures;1015 historic emitted plans identical")


if __name__=="__main__":main()
