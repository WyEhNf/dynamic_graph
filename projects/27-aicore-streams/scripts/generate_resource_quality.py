"""Fresh scarce-core seed for evaluating T, independent constructive witness."""
import argparse
import json
from pathlib import Path
from generate_frontier_cases import random_case


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=20261016)
    p.add_argument("--output", type=Path, default=Path("data/resource-quality.json"))
    args = p.parse_args()
    cases = [random_case(args.seed+n*100+int(d*1000)+e, n, d, e, True) for n in [64, 256, 1024] for d in [.03, .1] for e in [0, 3, 100000]]
    args.output.write_text(json.dumps(dict(format="aicore-local-v1", generator_seed=args.seed, cases=cases), separators=(",", ":")))
    print(f"resource quality={len(cases)} seed={args.seed}")


if __name__ == "__main__":
    main()
