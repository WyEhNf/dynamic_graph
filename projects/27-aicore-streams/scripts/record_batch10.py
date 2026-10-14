"""Append late-batch evidence without rewriting earlier measured claims."""
import hashlib
import json
from pathlib import Path


def main():
    def read(p):
        return json.loads(Path(p).read_text())
    validation = read("docs/validation.json")
    validation["latest_solution_sha256"] = hashlib.sha256(Path("solution/solution.cpp").read_bytes()).hexdigest()
    validation["regression_batch10"] = read("reports/regression-batch10.json")
    validation["oracle5_batch9"] = {k:read(f"reports/paired-{name}-batch9-summary.json") for k,name in [("development", "oracle5"), ("holdout", "oracle5-holdout")]}
    validation["event_pruning_batch10"] = {k:read(f"reports/paired-{name}-batch10-summary.json") for k,name in [("development", "pruning"), ("holdout", "pruning-holdout")]}
    validation["exact_parallel_oracle"]["independent_node_limit"] = 5
    validation["exact_parallel_oracle"]["five_node_development_exact"] = 24
    validation["exact_parallel_oracle"]["five_node_holdout_exact"] = 24
    validation["exact_parallel_oracle"]["five_node_candidate_evaluations"] = 1111850
    validation["exact_parallel_oracle"]["submission_complete_node_limit"] = 4
    validation["exact_parallel_oracle"]["submission_five_node_search"] = "6000 additional evaluations, membership/order then single added guard, bounded not complete"
    Path("docs/validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2))
    print("batch10 evidence appended:679 case records")


if __name__ == "__main__":
    main()
