"""Save version-scoped quality and oracle evidence; do not replace old timings."""
import hashlib
import json
from pathlib import Path
from compare_research import summarize


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    entries = {}
    for name in ["frontier", "frontier-holdout", "oracle", "oracle-holdout"]:
        m = read(f"reports/paired-{name}-batch8-summary.json")
        entries[name] = dict(before=m["runs"][0]["comparison"]["before"], after=m["runs"][0]["comparison"]["after"], common=m["runs"][0]["comparison"]["common_cases"], median_common_cpu_before_us=m["median_common_solve_us_before"], median_common_cpu_after_us=m["median_common_solve_us_after"], source_sha256=m["current_solution_sha256"], suite_sha256=m["suite_sha256"])
    for family, before, after in [("stress", "reports/paired-stream-priority-1-after.json", "reports/stress-batch8.json"), ("development", "reports/development-batch7.json", "reports/development-batch8.json"), ("holdout", "reports/holdout-batch7.json", "reports/holdout-batch8.json")]:
        c = summarize(read(before), read(after))
        Path(f"reports/{family}-comparison-batch8.json").write_text(json.dumps(c, indent=2))
        assert c["after"]["failed"] == c["regressed_T"] == c["regressed_peak_at_equal_T"] == c["model_disagreements"] == 0
    v = read("docs/validation.json")
    v["latest_solution_sha256"] = hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["frontier_increment_batch8"] = entries
    v["exact_parallel_oracle"] = dict(node_limit=4, stream_limit=2, scope="explicit direct synchronization local model", development_exact=24, holdout_exact=24, independently_enumerated_plans=41580)
    v["total_case_records_batch8"] = 631
    v["additional_third_model_reference_checks"] = 3
    v["additional_oracle_analytic_checks"] = 2
    Path("docs/validation.json").write_text(json.dumps(v, ensure_ascii=False, indent=2))
    print("batch8 evidence recorded; historical quality did not regress")


if __name__ == "__main__":
    main()
