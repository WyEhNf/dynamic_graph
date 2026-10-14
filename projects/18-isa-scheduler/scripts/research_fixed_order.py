"""Exact relay timing audit of saved outputs; no rescheduling hidden in baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from isa_scheduler.bounds import fixed_order_copy_bound
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.fixed_order import solve_fixed_order
from isa_scheduler.model import parse_block
from isa_scheduler.verify import IntegerSemantics, interpret, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="experiments/r10-prepared")
    parser.add_argument("--round", default="r11-fixed-order")
    parser.add_argument("--time-budget-ms", type=float, default=500)
    parser.add_argument("--max-states", type=int, default=100000)
    parser.add_argument("--max-window", type=int, default=8)
    args = parser.parse_args()
    destination = ROOT/"experiments"/args.round
    if not args.round.replace("-", "").replace("_", "").isalnum(): raise ValueError("Safe round name required")
    if destination.exists(): raise ValueError("Evidence directory exists; choose a fresh round")
    destination.mkdir(parents=True)
    source = ROOT/args.source
    corpus = source/"inputs.jsonl"
    report = json.loads((source/"report.json").read_text(encoding="utf-8"))
    if hashlib.sha256(corpus.read_bytes()).hexdigest() != report["corpus_sha256"]: raise ValueError("Corpus changed")
    inputs = {}
    for line in corpus.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        data = item.get("input",item)
        inputs[fingerprint(data)] = data
    records = {row["sha256"]: row for row in report["records"] if row["variant"] == report["paired_variants"]["after"]}
    # The serialized baseline deliberately omits stats, so its original order
    # is loaded from the per-output sidecar captured separately below. A graph
    # reference can reconstruct identity matching only with the saved trace.
    traces = source/"original_orders.jsonl"
    if not traces.exists(): raise ValueError("Original order sidecar required; do not infer scheduler identities from symbolic aliases")
    if hashlib.sha256(traces.read_bytes()).hexdigest()!=report["original_orders_sha256"]: raise ValueError("Order sidecar changed")
    if hashlib.sha256((source/"optimized_outputs.jsonl").read_bytes()).hexdigest()!=report["optimized_outputs_sha256"]: raise ValueError("Serialized baseline changed")
    orders = {row["input_sha256"]: row["original_order"] for row in map(json.loads,traces.read_text(encoding="utf-8").splitlines())}
    results = []
    started = perf_counter()
    with (destination/"optimized_outputs.jsonl").open("w",encoding="utf-8") as stream:
        for item in map(json.loads,(source/"optimized_outputs.jsonl").read_text(encoding="utf-8").splitlines()):
            digest, core = item["input_sha256"], item["output"]
            data, before = inputs[digest], records[digest]
            if fingerprint(core)!=before["output_sha256"]: raise ValueError("Baseline output hash mismatch")
            verify(data,core)
            block = parse_block(data)
            order = orders[digest]
            bound = fixed_order_copy_bound(block,order)
            record = {"input_sha256":digest,"block_id":data["block_id"],"window":block.window,
                      "before_copy":before["inserted_copies"],"lower_bound":bound["copy_lower_bound"]}
            if before["inserted_copies"] == bound["copy_lower_bound"]:
                record["status"] = "certified_order_optimal_by_lower_bound"
            elif block.window > args.max_window:
                record["status"] = "not_searched_window_limit"
            else:
                incumbent = {**core,"stats":{"inserted_copy_count":before["inserted_copies"],"original_order":order}}
                result = solve_fixed_order(block,order,incumbent,time_budget_ms=args.time_budget_ms,max_states=args.max_states)
                verify(data,result)
                registers = {name:i*11-17 for i,name in enumerate(sorted({row["reg"] for row in data["instructions"] if row["op"]=="GET"}))}
                for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
                    if interpret(data["instructions"],registers,semantics)!=interpret(result["optimized_instructions"],registers,semantics):
                        raise ValueError("Integer differential mismatch")
                after_core = {"block_id":result["block_id"],"optimized_instructions":result["optimized_instructions"]}
                record.update(status=result["stats"]["fixed_order_search"]["outcome"],after_copy=result["stats"]["inserted_copy_count"],
                              search=result["stats"]["fixed_order_search"],output_sha256=fingerprint(after_core))
                stream.write(json.dumps({"input_sha256":digest,"output":after_core},separators=(",",":"))+"\n")
            results.append(record)
    summary = {"source":args.source,"corpus_sha256":report["corpus_sha256"],"elapsed_s":perf_counter()-started,
               "scope":"fixed original-node order and identity-preserving COPY-only model; not global official optimum",
               "source_manifest":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")},
               "records":results}
    (destination/"report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    statuses = {status:sum(row["status"]==status for row in results) for status in {row["status"] for row in results}}
    print(json.dumps({"elapsed_s":summary["elapsed_s"],"statuses":statuses,
                      "improved":sum(row.get("after_copy",row["before_copy"])<row["before_copy"] for row in results)}))


if __name__ == "__main__": main()
