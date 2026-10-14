"""Separate exact-oracle cost from generated solver-suite metrics."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from generate_frontier_cases import oracle_case


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=20261013)
    p.add_argument("--nodes", type=int, default=5)
    p.add_argument("--cases", type=int, default=24)
    p.add_argument("--prefix", type=Path, default=Path("data/parallel-oracle5"))
    args = p.parse_args()
    source, output = Path(f"{args.prefix}-input.json"), Path(f"{args.prefix}.json")
    cases = [oracle_case(args.seed+i, args.nodes) for i in range(args.cases)]
    source.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=cases), separators=(",", ":")))
    started = time.perf_counter()
    run = subprocess.run([str(Path("build/aicore_oracle.exe").resolve()), str(source), str(output)], capture_output=True, text=True, check=True)
    wall = time.perf_counter()-started
    rows = json.loads(output.read_text())["cases"]
    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    cost = dict(seed=args.seed, nodes=args.nodes, cases=args.cases, oracle_generation_wall_seconds=wall, oracle_candidate_evaluations=sum(x["generation"]["plans_evaluated"] for x in rows), oracle_exe_sha256=sha("build/aicore_oracle.exe"), oracle_source_sha256=sha("src/parallel_oracle.cpp"), input_sha256=sha(source), suite_sha256=sha(output), scope="exhaustive explicit direct synchronization model, not official transitive model")
    Path(f"{args.prefix}-cost.json").write_text(json.dumps(cost, indent=2))
    print(run.stdout)
    print(json.dumps(cost, indent=2))


if __name__ == "__main__":
    main()
