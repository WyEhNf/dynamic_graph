"""Batch evaluation shared by CLI and deterministic fuzz harness."""
import csv
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule, InvalidBlock, VerificationFailed, parse_block
from .optimizer import optimize
from .verify import IntegerSemantics, interpret, verify


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def evaluate_case(data, strategy="auto", *, source="synthetic", seed=None,
                  time_budget_ms=100, max_states=30000, numeric=True, memory_order="hazard"):
    started = perf_counter()
    row = {"source": source, "seed": seed, "sha256": fingerprint(data), "strategy": strategy, "memory_order": memory_order,
           "block_id": data.get("block_id") if isinstance(data, dict) else None,
           "status": "invalid_input", "parse_ms": 0.0, "schedule_ms": 0.0, "verify_ms": 0.0}
    stage = "parse"
    checked = perf_counter()
    try:
        checked = perf_counter()
        block = parse_block(data, memory_order)
        row["parse_ms"] = (perf_counter() - checked) * 1000
        row["original_instruction_count"] = len(block.instructions)
        row["bit_width"] = block.bit_width
        row["status"] = "heuristic_failure"
        stage = "schedule"
        checked = perf_counter()
        result = optimize(data, strategy, time_budget_ms=time_budget_ms, max_states=max_states, memory_order=memory_order)
        elapsed = (perf_counter() - checked) * 1000
        row.update(result["stats"])
        row["selected_strategy"] = result["stats"]["strategy"]
        row["strategy"] = strategy
        row["schedule_ms"] = result["stats"].get("pure_schedule_ms", elapsed)
        row["parse_ms"] += result["stats"].get("optimizer_parse_ms", 0)
        row["verify_ms"] = result["stats"].get("candidate_verify_ms", 0)
        row["status"] = "verification_failure"
        stage = "verify"
        checked = perf_counter()
        verify(data, result)
        numeric_passed = 0
        numeric_skipped = []
        if numeric:
            regs = {node.reg for node in block.instructions if node.op == "GET"}
            cases = [({reg: i + 2 for i, reg in enumerate(sorted(regs))}, IntegerSemantics()),
                     ({reg: -3 if i % 2 else 7 for i, reg in enumerate(sorted(regs))}, IntegerSemantics(8, True)),
                     ({reg: 255 - i for i, reg in enumerate(sorted(regs))}, IntegerSemantics(16, False))]
            for inputs, semantics in cases:
                try:
                    before = interpret(data["instructions"], inputs, semantics)
                    after = interpret(result["optimized_instructions"], inputs, semantics)
                except InvalidBlock as exc:
                    if "Unbounded integer safety limit" in str(exc) and semantics.word_bits is None:
                        numeric_skipped.append("unbounded integer safety limit; fixed-width checks still run")
                        continue
                    raise
                if before != after:
                    raise InvalidBlock("Numeric differential failed")
                numeric_passed += 1
        row["verify_ms"] += (perf_counter() - checked) * 1000
        row["status"] = "verified"
        row["numeric_configurations"] = numeric_passed
        row["numeric_skipped"] = numeric_skipped
        row["total_ms"] = (perf_counter() - started) * 1000
        return row, result
    except BudgetExceeded as exc:
        row["status"] = "budget_exhausted"
        row["error"] = str(exc)
    except InfeasibleSchedule as exc:
        row["status"] = ("proven_infeasible_under_model" if "proven_infeasible_under_model" in str(exc)
                         else "heuristic_failure")
        row["error"] = str(exc)
    except VerificationFailed as exc:
        row["status"] = "verification_failure"
        row["error"] = str(exc)
    except (InvalidBlock, ValueError, KeyError, TypeError) as exc:
        row["error"] = str(exc)
    row[{"parse": "parse_ms", "schedule": "schedule_ms", "verify": "verify_ms"}[stage]] += (perf_counter() - checked) * 1000
    row["total_ms"] = (perf_counter() - started) * 1000
    return row, None


def summarize(records):
    by_strategy = {}
    for strategy in sorted({r["strategy"] for r in records}):
        group = [r for r in records if r["strategy"] == strategy]
        success = [r for r in group if r["status"] == "verified"]
        statuses = {status: sum(r["status"] == status for r in group) for status in sorted({r["status"] for r in group})}
        inserted = sum(r["inserted_copy_count"] for r in success)
        total_copies = sum(r["total_copy_count"] for r in success)
        original_count = sum(r["original_instruction_count"] for r in success)
        output_count = sum(r["optimized_instruction_count"] for r in success)
        by_strategy[strategy] = {
            "attempted": len(group), "verified": len(success), "status_counts": statuses,
            "verified_rate_all_inputs": len(success) / len(group) if group else 0,
            "correctness_rate_emitted_outputs": len(success) / (len(success) + statuses.get("verification_failure", 0)) if success or statuses.get("verification_failure") else None,
            "failure_rate": 1 - len(success) / len(group) if group else 0,
            "mean_copy_ratio_output_successes": sum(r["copy_ratio_output"] for r in success) / len(success) if success else None,
            "mean_inserted_copy_ratio_original_successes": sum(r["inserted_copy_ratio_original"] for r in success) / len(success) if success else None,
            "weighted_copy_ratio_output_successes": total_copies / output_count if output_count else None,
            "weighted_inserted_copy_ratio_original_successes": inserted / original_count if original_count else None,
            "latency_ms_all_inputs": {metric: {f"p{int(q*100)}": percentile([r.get(metric, 0.0) for r in group], q)
                                               for q in (.5, .95, .99)}
                                      for metric in ("parse_ms", "schedule_ms", "verify_ms", "total_ms")},
        }
    return by_strategy


def write_report(report, destination, csv_path=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = Path(csv_path) if csv_path else destination.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["source", "seed", "sha256", "block_id", "strategy", "selected_strategy", "memory_order", "status", "bit_width",
               "original_instruction_count", "optimized_instruction_count", "inserted_copy_count", "total_copy_count",
               "copy_ratio_output", "inserted_copy_ratio_original", "parse_ms", "schedule_ms", "verify_ms", "total_ms", "error"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["records"])


def input_documents(path):
    path = Path(path)
    files = sorted(p for p in path.iterdir() if p.suffix.lower() in (".json", ".jsonl")) if path.is_dir() else [path]
    if not files:
        raise InvalidBlock("No JSON/JSONL input files found")
    for file in files:
        content = file.read_text(encoding="utf-8-sig")
        raw_entries = content.splitlines() if file.suffix.lower() == ".jsonl" else [content]
        for line, text in enumerate(raw_entries, 1):
            if not text.strip():
                continue
            source = str(file) + (f":{line}" if file.suffix.lower() == ".jsonl" else "")
            started = perf_counter()
            try:
                data = json.loads(text)
                yield source, data, None, (perf_counter() - started) * 1000, hashlib.sha256(text.encode()).hexdigest()
            except json.JSONDecodeError as exc:
                yield source, None, str(exc), (perf_counter() - started) * 1000, hashlib.sha256(text.encode()).hexdigest()


def batch(path, strategies=("stable", "ready", "auto"), time_budget_ms=100, max_states=30000, memory_order="hazard"):
    records = []
    for source, data, error, decode_ms, raw_hash in input_documents(path):
        for strategy in strategies:
            if error:
                records.append({"source": source, "strategy": strategy, "status": "invalid_input",
                                "sha256": raw_hash, "error": error, "parse_ms": decode_ms,
                                "schedule_ms": 0.0, "verify_ms": 0.0, "total_ms": decode_ms})
            else:
                record, _ = evaluate_case(data, strategy, source=source, time_budget_ms=time_budget_ms, max_states=max_states, memory_order=memory_order)
                record["parse_ms"] += decode_ms
                record["total_ms"] += decode_ms
                record["raw_sha256"] = raw_hash
                records.append(record)
    return {"dataset": "user supplied input; no claim of official dataset identity",
            "seed": None, "input": str(path), "time_budget_ms": time_budget_ms, "memory_order": memory_order,
            "max_states": max_states, "summary": summarize(records), "records": records}

