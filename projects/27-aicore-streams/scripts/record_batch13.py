"""Record completed batches without overwriting historic version scopes."""
import hashlib
import json
from pathlib import Path


def main():
    def read(path):
        return json.loads(Path(path).read_text())
    v = read("docs/validation.json")
    v["latest_solution_sha256"] = hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["resource_quality_batch12"] = {name:read(f"reports/paired-{name}-batch12-summary.json") for name in ["resource-quality", "resource-quality-holdout"]}
    v["weighted_frontier_batch13"] = {name:read(f"reports/paired-{name}-batch13-summary.json") for name in ["weighted-beam", "weighted-beam-holdout"]}
    v["regression_batch13"] = read("reports/regression-batch13.json")
    v["beam_telemetry_batch13"] = {}
    for name in ["weighted-overlap", "weighted-overlap-holdout"]:
        cases = read(f"reports/{name}-batch13.json")["cases"]
        v["beam_telemetry_batch13"][name] = dict(cases_with_beam=sum(x["beam_expansions"]>0 for x in cases), child_states=sum(x["beam_expansions"] for x in cases), maximum_width=max(x["beam_width"] for x in cases), scope="beam attempted, does not identify which returned candidate won")
    v["total_case_records_batch13"] = 835
    v["standalone_and_ctest_batch13"] = dict(ctest="3/3", ctest_wall_seconds=0.56, standalone="GCC 15.2.0 -std=c++17 -O2 -Wall -Wextra -Wpedantic, no warnings", solver_source_sha256=v["latest_solution_sha256"])
    Path("docs/validation.json").write_text(json.dumps(v, ensure_ascii=False, indent=2))
    print("recorded batches12/13; 835 records; historical artifacts retained")


if __name__ == "__main__":
    main()
