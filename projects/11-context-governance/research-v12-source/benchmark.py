"""Reproducible local timing evidence; no model or official scoring is involved."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
from .core import ByteEstimate, Item, govern, render


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def make_workload(count: int, total_units: int = 128 * 1024) -> list[Item]:
    items = [Item(f"item-{i:03}", "memory", "", False, (i % 7) / 7)
             for i in range(count)]
    payload_units = total_units - ByteEstimate().count(render(items))
    quotient, remainder = divmod(payload_units, count)
    result = []
    for i, item in enumerate(items):
        length = quotient + (i < remainder)
        seed = f"parser file_{i} pending memory context unrelated trace sample "
        payload = (seed * (length // len(seed) + 1))[:length]
        result.append(Item(item.id, item.kind, payload, i == 0, item.utility))
    assert ByteEstimate().count(render(result)) == total_units
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/importance-benchmark.json"))
    parser.add_argument("--repetitions", type=int, default=30)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    cases = []
    for count in (16, 64, 256):
        items = make_workload(count)
        budget = 96 * 1024
        for _ in range(3):
            govern("parser trace", items, budget)
        outputs = [govern("parser trace", items, budget)["metrics"]
                   for _ in range(args.repetitions)]
        timings = {}
        for metric in ("importance_analysis_ms", "governance_ms"):
            samples = [entry[metric] for entry in outputs]
            timings[metric] = {"p50": statistics.median(samples),
                               "p95": percentile(samples, .95),
                               "maximum": max(samples), "samples": samples}
        cases.append({"item_count": count, "input_units": outputs[0]["input_units"],
                      "budget_units": budget, "output_units": outputs[0]["output_units"],
                      "timings": timings,
                      "importance_all_samples_within_100ms":
                          timings["importance_analysis_ms"]["maximum"] <= 100})
    report = {"schema_version": 1, "workload": "synthetic ASCII context, 128 KiB including labels",
              "counter": ByteEstimate.name,
              "limitations": ["Byte units are not model tokens; this is not a 128K-token window test.",
                              "Local timing evidence only; no official dataset, quality or TTFT evaluation.",
                              "The 100ms check applies to importance evaluation, not total governance."],
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "processor": platform.processor(),
                              "logical_cpu_count": os.cpu_count()},
              "warmup_iterations": 3, "repetitions": args.repetitions, "cases": cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": [
        {"items": x["item_count"], "importance_p95_ms": x["timings"]["importance_analysis_ms"]["p95"],
         "governance_p95_ms": x["timings"]["governance_ms"]["p95"]} for x in cases]}, indent=2))


if __name__ == "__main__":
    main()
