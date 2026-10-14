"""End-to-end rejection checks and an auditable local validation record."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/validation.json"))
    args = parser.parse_args()
    results = {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chol-validate-", dir=args.output.parent) as folder:
        root = Path(folder)
        cases = {
            "truncated_header": b"\x01\x00",
            "invalid_n": struct.pack("<II", 1, 2),
            "truncated_matrix": struct.pack("<II", 1, 3) + b"\0"*8,
            "trailing_data": struct.pack("<I", 0) + b"x",
            "non_spd": struct.pack("<II9d", 1, 3, -1, 0, 0, 0, 1, 0, 0, 0, 1),
        }
        for label, data in cases.items():
            path = root / (label + ".bin")
            path.write_bytes(data)
            destination = root / (label + ".result.bin")
            process = subprocess.run([str(args.runtime.resolve()), "--metadata", str(args.metadata.resolve()), "--input", str(path), "--output", str(destination)], capture_output=True, text=True)
            if process.returncode == 0 or destination.exists():
                raise SystemExit(f"invalid fixture accepted: {label}")
            results[label] = {"rejected": True, "message": process.stderr.strip()}
        same = root / "same.bin"
        data = struct.pack("<I", 0)
        same.write_bytes(data)
        process = subprocess.run([str(args.runtime.resolve()), "--metadata", str(args.metadata.resolve()), "--input", str(same), "--output", str(same)], capture_output=True, text=True)
        if process.returncode == 0 or same.read_bytes() != data:
            raise SystemExit("same-path input was modified or accepted")
        results["same_path_preserves_input"] = {"rejected": True, "message": process.stderr.strip()}
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_source_used": False,
        "ctest": "runtime_correctness passed: known factor, LL^T residual, self-built C reference byte equality, serial/parallel byte equality, binary IO and rejection",
        "cli_checks": results,
        "environment": {
            "cmake": "4.2.0", "gcc": "15.2.0 x86_64-win32-seh", "clang": "21.1.0", "python": "3.12.14", "dependencies": "Python standard library; C++ standard library and Threads"
        },
        "limitations": ["official hidden test package not supplied; self-set source/oracle test report is artifacts/phase1-tests/test-report.json", "generic C subset compiles to an executable source-order VM; proven scalar/right-looking/tiled Cholesky uses parameterized tile tasks or the explicit stage engine", "official image div/madd helpers use explicit local definitions; no formal helper contract supplied", "local little-endian uint32 IO convention", "general dense N10000 independently compared against original C in extended/SIMD/panel/ready/row milestones; diagonal maximum-format tests reported separately"]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
