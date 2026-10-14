"""Independent third-model reference tests and exact-oracle sanity checks."""
import json
import subprocess
from pathlib import Path
from generate_cases import case, hardware, node, official_samples
from generate_frontier_cases import resource_witness


def main():
    expected = [(365, 320), (124, 55), (152, 45)]
    for x, result in zip(official_samples(), expected):
        assert resource_witness(x["hardware"], x["nodes"], x["witness_plan"]) == result
    # Full-core equal-type nodes must serialize; different types can overlap.
    nodes = [node(11, "AIC", 2, 2, 1, 1), node(43, "AIC", 2, 3, 1, 1)]
    same = case("exact_same_pool", hardware(aic=2, aiv=2, streams=2, memory=100, record=0, wait=0), nodes, 5)
    other = json.loads(json.dumps(same))
    other["name"] = "exact_distinct_pools"
    other["nodes"][1]["core_type"] = "AIV"
    target = Path("build/test-reports")
    target.mkdir(exist_ok=True)
    input_path, output_path = target / "oracle-sanity-input.json", target / "oracle-sanity-output.json"
    input_path.write_text(json.dumps(dict(format="aicore-local-v1", cases=[same, other])))
    subprocess.run([str(Path("build/aicore_oracle.exe").resolve()), str(input_path), str(output_path)], check=True)
    rows = json.loads(output_path.read_text())["cases"]
    assert (rows[0]["generation"]["oracle_T"], rows[0]["generation"]["oracle_peak"]) == (5, 3)
    assert (rows[1]["generation"]["oracle_T"], rows[1]["generation"]["oracle_peak"]) == (3, 4)
    for x in rows:
        assert resource_witness(x["hardware"], x["nodes"], x["witness_plan"]) == (x["generation"]["witness_T"], x["generation"]["witness_peak"])
    print("third-model references=3 oracle analytic optima=2: passed")


if __name__ == "__main__":
    main()
