"""Record rejected locality and distinct wall/thread CPU timing scopes."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):return json.loads(Path(p).read_text())
    v=read("docs/validation.json")
    v["latest_solution_sha256"]=hashlib.sha256(Path("research/batch23/solution.cpp").read_bytes()).hexdigest()
    v["gated_assignment_batch23"]={"regression":read("reports/regression-batch23.json"),"plan_identity":read("reports/plan-identity-batch23.json"),"certificate_audit":read("reports/certificate-audit-batch23.json"),"paired":{n:read(f"reports/paired-gated-{n}-batch23-summary.json") for n in ["main","dense"]},"ctest":"4/4","ctest_wall_seconds":5.09,"standalone_compile":"GCC -O2 no warnings","performance_conclusion":"No observable material speedup: main wall +1.7%/thread CPU +2.4%; dense wall flat/thread CPU -1.8%, within quantization/load uncertainty."}
    rejected={"source_sha256":hashlib.sha256(Path("research/batch23-rejected-lifetime/solution.cpp").read_bytes()).hexdigest(),"retained_by_default":False,"reason":"No recovery on old48 or fresh72; extra failed-path evaluation cost","diagnostic_scope":"single focused quality runs, not paired cost measurement"}
    v["lifetime_locality_batch23_rejected"]=rejected;v["fresh_lifetime_batch23"]={}
    for h in ["","-holdout"]:
        old=read(f"reports/lifetime-before{h}-batch23.json");new=read(f"reports/lifetime{h}-batch23.json")
        c=summarize(old,new);assert not c["lost"] and c["regressed_T"]==c["regressed_peak_at_equal_T"]==c["model_disagreements"]==0
        rows={x["name"]:x for x in old["cases"]}
        for x in new["cases"]:assert x["plan"]==rows[x["name"]]["plan"] and x["pass"]==rows[x["name"]]["pass"]
        v["fresh_lifetime_batch23"][h or "development"]=c
    v["batch23_counts"]=dict(strict_regression_records=979,old_hard_records=48,old_hard_passed=29,new_hard_records=72,new_hard_passed=43,new_hard_failed=29,total_records=1099,total_passed=1051,total_failed=48)
    v["timing_scope_audit"]="Historical solve_us is steady_clock elapsed call wall time, includes OS preemption, not actual thread CPU. Added Win32 user+kernel thread CPU only local harness; observed 15625us quantum, zero small-case CPU not zero cost. New CPU field never applied retrospectively."
    Path("docs/validation.json").write_text(json.dumps(v,ensure_ascii=False,indent=2))
    print("batch23:979 strict pass;1027 old +72 fresh emitted plans identical;1099 records/1051pass/48 real feasible failures")


if __name__=="__main__":main()
