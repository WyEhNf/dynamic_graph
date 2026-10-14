"""Generate deterministic SPD fixtures and compare serial/parallel bytes.
Compute timing comes from the runtime; process/IO time is recorded separately.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import subprocess
import time


def make_input(path, sizes):
    with path.open("wb") as stream:
        stream.write(struct.pack("<I", len(sizes)))
        for n in sizes:
            stream.write(struct.pack("<I", n))
            for i in range(n):
                stream.write(struct.pack(f"<{n}d", *(float(n + 2) if i == j else 0.125 for j in range(n))))


def residual(path, sizes):
    worst = 0.0
    with path.open("rb") as stream:
        assert struct.unpack("<I", stream.read(4))[0] == len(sizes)
        for n in sizes:
            assert struct.unpack("<I", stream.read(4))[0] == n
            payload = stream.tell()
            # Check a deterministic sample; full residual is cubic and excluded from benchmark timings.
            sample = [(0, 0), (n-1, n-1), (n-1, 0), (n//2, n//3)]
            rows = {}
            for row in {v for pair in sample for v in pair}:
                stream.seek(payload + row*n*8)
                rows[row] = struct.unpack(f"<{n}d", stream.read(n*8))
                assert all(rows[row][j] == 0 for j in range(row+1, n))
            for i, j in sample:
                actual = sum(rows[i][k] * rows[j][k] for k in range(min(i, j)+1))
                expected = float(n+2) if i == j else 0.125
                worst = max(worst, abs(actual-expected) / max(1.0, abs(expected)))
            stream.seek(payload + n*n*8)
        assert not stream.read(1)
    return worst


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--sizes", default="3,17,67,128")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    sizes = [int(n) for n in args.sizes.split(",")]
    if any(n < 3 or n > 10000 for n in sizes):
        raise SystemExit("sizes must be in [3, 10000]")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.output_dir / "synthetic-input.bin"
    make_input(source, sizes)
    results = {}
    outputs = []
    for scheduler in ("serial", "parallel"):
        destination = args.output_dir / f"{scheduler}.bin"
        destination.unlink(missing_ok=True)
        started = time.perf_counter()
        process = subprocess.run([str(args.runtime.resolve()), "--metadata", str(args.metadata), "--input", str(source), "--output", str(destination), "--scheduler", scheduler, "--threads", str(args.threads)], capture_output=True, text=True, check=True)
        data = json.loads(process.stdout)
        data["wall_ms"] = (time.perf_counter()-started)*1000
        data["sample_relative_residual"] = residual(destination, sizes)
        results[scheduler] = data
        outputs.append(destination)
    identical = True
    with outputs[0].open("rb") as left, outputs[1].open("rb") as right:
        while True:
            a, b = left.read(1024*1024), right.read(1024*1024)
            if a != b:
                identical = False
                break
            if not a:
                break
    report = {"fixture": "self-built deterministic SPD, not official data", "sizes": sizes, "threads": args.threads, "byte_identical_between_schedulers": identical, "results": results, "official_correctness_confirmed": False}
    if not identical or any(r["sample_relative_residual"] > 1e-12 for r in results.values()):
        raise SystemExit("validation failed")
    (args.output_dir / "benchmark.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
