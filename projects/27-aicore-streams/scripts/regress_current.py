"""One meaningful full regression after a source batch, preserving evidence."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from compare_research import summarize


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="batch10")
    p.add_argument("--bench",default="build/aicore_bench.exe")
    p.add_argument("--source",default="solution/solution.cpp")
    args = p.parse_args()
    suites = [("stress", "data/stress.json", "reports/stress-batch8.json"), ("development", "data/research-final.json", "reports/development-batch8.json"), ("holdout", "data/research-holdout-final.json", "reports/holdout-batch8.json"), ("frontier", "data/frontier.json", "reports/paired-frontier-batch8-1-after.json"), ("frontier-holdout", "data/frontier-holdout.json", "reports/paired-frontier-holdout-batch8-1-after.json"), ("oracle4", "data/parallel-oracle.json", "reports/paired-oracle-batch8-1-after.json"), ("oracle4-holdout", "data/parallel-oracle-holdout.json", "reports/paired-oracle-holdout-batch8-1-after.json"), ("oracle5", "data/parallel-oracle5.json", "reports/paired-oracle5-batch9-1-after.json"), ("oracle5-holdout", "data/parallel-oracle5-holdout.json", "reports/paired-oracle5-holdout-batch9-1-after.json")]
    if Path("data/overlap.json").exists():
        suites += [("overlap", "data/overlap.json", "reports/overlap-before-batch11.json"), ("overlap-holdout", "data/overlap-holdout.json", "reports/overlap-holdout-before-batch11.json")]
    if Path("data/resource-quality.json").exists():
        suites += [("resource-quality", "data/resource-quality.json", "reports/paired-resource-quality-batch12-1-after.json"), ("resource-quality-holdout", "data/resource-quality-holdout.json", "reports/paired-resource-quality-holdout-batch12-1-after.json"), ("weighted-overlap", "data/overlap-weighted.json", "reports/weighted-before-batch12.json"), ("weighted-overlap-holdout", "data/overlap-weighted-holdout.json", "reports/weighted-holdout-before-batch12.json")]
    if Path("data/parallel-oracle6.json").exists():
        suites += [("oracle6","data/parallel-oracle6.json","reports/oracle6-expanded-batch15.json"),("oracle6-holdout","data/parallel-oracle6-holdout.json","reports/oracle6-holdout-expanded-batch15.json")]
    if Path("reports/paired-projection-small-batch16-1-after.json").exists():
        suites += [("irregular-small","data/irregular-small.json","reports/paired-projection-small-batch16-1-after.json"),("irregular-small-holdout","data/irregular-small-holdout.json","reports/paired-projection-small-holdout-batch16-1-after.json")]
    if Path("data/corepacking.json").exists():
        suites += [("corepacking","data/corepacking.json","reports/corepacking-after-batch18.json"),("corepacking-holdout","data/corepacking-holdout.json","reports/corepacking-holdout-after-batch18.json")]
    if Path("data/wait-overlap.json").exists():
        suites += [("wait-overlap","data/wait-overlap.json","reports/wait-overlap-after-batch19.json"),("wait-overlap-holdout","data/wait-overlap-holdout.json","reports/wait-overlap-holdout-after-batch19.json")]
    if Path("reports/dense-batch22.json").exists():
        suites += [("certificate-controls","data/certificate-controls.json","reports/certificate-controls-batch22.json"),("dense","data/dense-assignment.json","reports/dense-batch22.json"),("dense-holdout","data/dense-assignment-holdout.json","reports/dense-holdout-batch22.json")]
    comparisons = {}
    started = time.perf_counter()
    for name, source, before in suites:
        output = Path(f"reports/{name}-{args.label}.json")
        subprocess.run([str(Path(args.bench).resolve()), "--input", source, "--output", str(output), "--csv", str(output.with_suffix(".csv"))], check=True)
        old, new = json.loads(Path(before).read_text()), json.loads(output.read_text())
        c = summarize(old, new)
        assert c["regressed_T"] == c["regressed_peak_at_equal_T"] == c["model_disagreements"] == c["after"]["failed"] == 0
        comparisons[name] = c
    result = dict(source_sha256=hashlib.sha256(Path(args.source).read_bytes()).hexdigest(), case_records=sum(x["after"]["total"] for x in comparisons.values()), elapsed_wall_seconds=time.perf_counter()-started, all_passed=True, comparisons=comparisons, timing_scope="single functional regression, not paired CPU evidence")
    Path(f"reports/regression-{args.label}.json").write_text(json.dumps(result, indent=2))
    print(f'{result["case_records"]} case-records passed; no quality regression; {result["elapsed_wall_seconds"]:.3f}s')


if __name__ == "__main__":
    main()
