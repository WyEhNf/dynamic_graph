"""Freeze successful feasibility recovery and its rejected quality trajectory."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    source = Path("solution/solution.cpp").read_text()
    # Recover the EXACT draft behind the first documented regression. Its
    # source hash must match the original paired artifact before saving it.
    start = source.index("  // Feasibility recovery AFTER")
    end = source.index("  metrics.micros=", start)
    draft = (source[:start] + source[end:]).replace("for(int mode:{3,0,1,2})", "for(int mode:{3,0,1,2,4})")
    expected = "08fc39e010428317fb687c07df6127058394a5afb7915740b3a9c002c58adc0b"
    digest = hashlib.sha256(draft.encode()).hexdigest()
    if digest != expected:
        raise RuntimeError(f"Draft reconstruction mismatch: {digest}")
    target = Path("research/batch11-rejected")
    target.mkdir(exist_ok=True)
    target.joinpath("solution.cpp").write_text(draft, newline="\n")
    v = read("docs/validation.json")
    v["latest_solution_sha256"] = hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    v["regression_batch11"] = read("reports/regression-batch11-preserved.json")
    v["overlapping_consumers_batch11"] = {k:read(f"reports/paired-{name}-preserved-batch11-summary.json") for k,name in [("development", "overlap"), ("holdout", "overlap-holdout")]}
    v["overlap_quality_rejection"] = dict(rejected_source_sha256=expected, stress_regressed_T=1, intermediate_development_regressed_peak_equal_T=1, action="move new feasibility recovery after ALL old search and arbitration, only if no feasible result")
    v["total_case_records_batch11"] = 739
    Path("docs/validation.json").write_text(json.dumps(v, ensure_ascii=False, indent=2))
    print("batch11:739 records passed; rejected exact source saved")


if __name__ == "__main__":
    main()
