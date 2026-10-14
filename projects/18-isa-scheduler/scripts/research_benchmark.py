"""Paired frozen/current benchmarks; preserve all failures and input hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.baseline_v02.isa_scheduler.optimizer import optimize as old_optimize
from experiments.baseline_v14.isa_scheduler.optimizer import optimize as v14_optimize
from experiments.baseline_level_r91.optimizer import optimize as level_r91_optimize
from experiments.baseline_phase_r102.optimizer import optimize as phase_r102_optimize
from experiments.baseline_r1.isa_scheduler.optimizer import optimize as r1_optimize
from experiments.baseline_r2.isa_scheduler.optimizer import optimize as r2_optimize
from experiments.baseline_r3.isa_scheduler.optimizer import optimize as r3_optimize
from experiments.baseline_r4.isa_scheduler.optimizer import optimize as r4_optimize
from experiments.baseline_r6.isa_scheduler.optimizer import optimize as r6_optimize
from experiments.baseline_r7eager.isa_scheduler.optimizer import optimize as r7eager_optimize
from experiments.baseline_r7lazy.isa_scheduler.optimizer import optimize as r7lazy_optimize
from experiments.baseline_r8.isa_scheduler.optimizer import optimize as r8_optimize
from experiments.baseline_r9.isa_scheduler.optimizer import optimize as r9_optimize
from experiments.baseline_r13.isa_scheduler.optimizer import optimize as r13_optimize
from experiments.baseline_r14.isa_scheduler.optimizer import optimize as r14_optimize
from experiments.baseline_r17.isa_scheduler.optimizer import optimize as r17_optimize
from experiments.baseline_r22.isa_scheduler.optimizer import optimize as r22_optimize
from experiments.baseline_r24.isa_scheduler.optimizer import optimize as r24_optimize
from experiments.baseline_r28.isa_scheduler.optimizer import optimize as r28_optimize
from experiments.baseline_r30.isa_scheduler.optimizer import optimize as r30_optimize
from experiments.baseline_r31.isa_scheduler.optimizer import optimize as r31_optimize
from experiments.baseline_r32.isa_scheduler.optimizer import optimize as r32_optimize
from experiments.baseline_r33.isa_scheduler.optimizer import optimize as r33_optimize
from experiments.baseline_r40.isa_scheduler.optimizer import optimize as r40_optimize
from experiments.baseline_r51.isa_scheduler.optimizer import optimize as r51_optimize
from experiments.baseline_r54.isa_scheduler.optimizer import optimize as r54_optimize
from experiments.baseline_r66.isa_scheduler.optimizer import optimize as r66_optimize
from experiments.baseline_r69.isa_scheduler.optimizer import optimize as r69_optimize
from experiments.baseline_r70.isa_scheduler.optimizer import optimize as r70_optimize
from experiments.baseline_r76.isa_scheduler.optimizer import optimize as r76_optimize
from experiments.baseline_r77.isa_scheduler.optimizer import optimize as r77_optimize
from experiments.baseline_r78.isa_scheduler.optimizer import optimize as r78_optimize
from isa_scheduler.optimizer import optimize
from isa_scheduler.evaluation import fingerprint, percentile
from isa_scheduler.verify import IntegerSemantics, interpret, verify
from isa_scheduler.workloads import FAMILIES, generate_workload
from isa_scheduler.bounds import fixed_order_copy_bound
from isa_scheduler.spine_copy_bound import check_spine_copy_certificate
from isa_scheduler.consumer_copy_bound import check_consumer_copy_certificate
from isa_scheduler.pair_copy_bound import check_pair_copy_certificate
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.model import parse_block

OPTIMIZERS = {"v02_auto": old_optimize, "r1_auto": r1_optimize, "r2_auto": r2_optimize,
              "phase_r102":lambda data,strategy,**kwargs:phase_r102_optimize(data,'phase_portfolio',**kwargs),
              "r3_auto": r3_optimize, "r4_auto": r4_optimize, "r6_auto": r6_optimize,
              "r7eager_auto": r7eager_optimize, "r7lazy_auto": r7lazy_optimize, "r8_auto": r8_optimize,
              "r9_auto": r9_optimize, "r13_auto":r13_optimize, "r14_auto":r14_optimize,
              "r17_auto":r17_optimize,"r22_auto":r22_optimize,"r24_auto":r24_optimize,
              "r24_branch":lambda data,strategy,**kwargs:r24_optimize(data,"branch_dp",**kwargs),
              "r28_auto":r28_optimize,"r30_auto":r30_optimize,"r31_auto":r31_optimize,
              "r32_auto":r32_optimize,"r33_auto":r33_optimize,"r40_auto":r40_optimize,"r51_auto":r51_optimize,
              "r54_local":lambda data,strategy,**kwargs:r54_optimize(data,'local_swap',**kwargs),
              "r66_auto":r66_optimize,"r69_bound":lambda data,strategy,**kwargs:r69_optimize(data,'bound_portfolio',**kwargs),
              "r70_bound":lambda data,strategy,**kwargs:r70_optimize(data,'bound_portfolio',**kwargs),
              "bound_001":lambda data,strategy,**kwargs:optimize(data,'bound_portfolio',bound_tolerance=.001,**kwargs),
              "bound_002":lambda data,strategy,**kwargs:optimize(data,'bound_portfolio',bound_tolerance=.002,**kwargs),
              "bound_005":lambda data,strategy,**kwargs:optimize(data,'bound_portfolio',bound_tolerance=.005,**kwargs),
              "bound_010":lambda data,strategy,**kwargs:optimize(data,'bound_portfolio',bound_tolerance=.010,**kwargs),
              "bound_exact":lambda data,strategy,**kwargs:optimize(data,'bound_portfolio',bound_tolerance=0,**kwargs),
              "r76_bound":lambda data,strategy,**kwargs:r76_optimize(data,'bound_portfolio',**kwargs),
              "r77_bound":lambda data,strategy,**kwargs:r77_optimize(data,'bound_portfolio',**kwargs),
              "r78_auto":r78_optimize,
              "v14_auto": v14_optimize,"level_r91":lambda data,strategy,**kwargs:level_r91_optimize(data,'research_portfolio',**kwargs),"current_auto": optimize}


def run_case(data, variant, budget, max_states, output_stream=None, order_stream=None):
    started = perf_counter()
    record = {"variant": variant, "sha256": fingerprint(data), "block_id": data["block_id"],
              "bit_width": data["bit_width"], "node_count": len(data["instructions"]), "status": "failed"}
    phase = "optimize"
    try:
        function = OPTIMIZERS.get(variant, optimize)
        strategy = "auto" if variant in OPTIMIZERS else variant
        result = function(data, strategy, time_budget_ms=budget, max_states=max_states)
        record["optimizer_ms"] = (perf_counter() - started) * 1000
        checked = perf_counter()
        phase = "independent_verify"
        verify(data, result)
        witness=result['stats'].get('original_order')
        identity_applicable=result['stats'].get('fixed_order_lower_bound_applicable',True) and all(row['op']!='COPY'for row in data['instructions'])
        if identity_applicable and witness is not None:
            record['independent_identity_check']=check_identity_witness(data,result,witness)
            record['identity_check_status']='verified'
        else:
            record['identity_check_status']='unavailable_order_witness' if identity_applicable else 'not_applicable_copy_or_alias_input_model'
        certificate_key=next((key for key in ('approximation_certificate','optimality_certificate')if key in result['stats']),None)
        if certificate_key:
            certificate=result['stats'][certificate_key]
            if 'independent_identity_check' not in record:raise ValueError('Quality certificate requires independently checked original identity witness')
            checker={'distinct_consumer_identity_relay_sum':check_consumer_copy_certificate,'disjoint_terminal_root_pairs_age_sum':check_pair_copy_certificate}.get(certificate['kind'],check_spine_copy_certificate)
            proof=checker(data,certificate)
            copies=result['stats']['inserted_copy_count']
            if copies-proof['verified_global_copy_lower_bound']>copies*certificate['tolerance']:
                raise ValueError('Approximate stopping quality bound not established')
            record[certificate_key]=certificate
            record['independent_approximation_check']=proof
        names = sorted({r["reg"] for r in data["instructions"] if r["op"] == "GET"})
        for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
            inputs = {name: 7 + i * 3 for i, name in enumerate(names)}
            if interpret(data["instructions"], inputs, semantics) != interpret(result["optimized_instructions"], inputs, semantics):
                raise ValueError("Independent integer differential mismatch")
        record["independent_verify_ms"] = (perf_counter() - checked) * 1000
        analysis_started = perf_counter()
        if "original_order" in result["stats"] and result["stats"].get("fixed_order_lower_bound_applicable", True):
            bound = fixed_order_copy_bound(parse_block(data),result["stats"]["original_order"])
            record["fixed_order_copy_lower_bound"] = bound["copy_lower_bound"]
            record["fixed_order_peak_live"] = bound["fixed_order_peak_live"]
            record["copy_above_order_lower_bound"] = result["stats"]["inserted_copy_count"]-bound["copy_lower_bound"]
            if record["copy_above_order_lower_bound"] < 0:
                raise ValueError("Fixed-order COPY lower-bound mismatch")
        record["analysis_ms"] = (perf_counter()-analysis_started)*1000
        core = {"block_id":result["block_id"],"optimized_instructions":result["optimized_instructions"]}
        record["output_sha256"] = fingerprint(core)
        if output_stream is not None:
            output_stream.write(json.dumps({"input_sha256":record["sha256"],"variant":variant,"output":core},separators=(",",":"))+"\n")
        if order_stream is not None and "original_order" in result["stats"]:
            order_stream.write(json.dumps({"input_sha256":record["sha256"],"variant":variant,
                                           "original_order":result["stats"]["original_order"]},separators=(",",":"))+"\n")
        record.update(status="verified", inserted_copies=result["stats"]["inserted_copy_count"],
                      output_count=len(result["optimized_instructions"]),
                      selected_strategy=result["stats"]["strategy"],
                      schedule_ms=result["stats"].get("pure_schedule_ms", result["stats"]["elapsed_ms"]))
    except Exception as exc:
        record["exception_type"], record["error"] = type(exc).__name__, str(exc)
        if phase == "independent_verify":
            record["status"] = "verification_failure"
        elif "Budget" in type(exc).__name__:
            record["status"] = "budget_exhausted"
        elif "Verification" in type(exc).__name__ or "mismatch" in str(exc):
            record["status"] = "verification_failure"
        elif "proven_infeasible_under_model" in str(exc):
            record["status"] = "proven_infeasible_under_model"
        else:
            record["status"] = "scheduling_failure"
        record["optimizer_ms"] = (perf_counter() - started) * 1000
    record["total_ms"] = (perf_counter() - started) * 1000
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="r1")
    parser.add_argument("--seed", type=int, default=18001)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--sizes", default="32,128,512,2048")
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--bits", default="2,3,4,5")
    parser.add_argument("--variants", default="v02_auto,current_auto,pressure,demand,incremental")
    parser.add_argument("--before", default="v02_auto")
    parser.add_argument("--after", default="current_auto")
    parser.add_argument("--time-budget-ms", type=float, default=250)
    parser.add_argument("--max-states", type=int, default=30000)
    parser.add_argument("--input", help="Reuse an exact JSONL corpus from an earlier milestone")
    args = parser.parse_args()
    destination = ROOT / "experiments" / args.round
    if not args.round.replace("-", "").replace("_", "").isalnum(): raise ValueError("Safe round name required")
    if any((destination/name).exists() for name in ("inputs.jsonl","report.json","records.csv","optimized_outputs.jsonl","original_orders.jsonl")):
        raise ValueError("Evidence exists; choose a fresh round")
    destination.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    executed_harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    source_manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in (ROOT / "isa_scheduler").glob("*.py")}
    if args.input:
        cases = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        cases = []
        for family in args.families.split(","):
            for size in map(int, args.sizes.split(",")):
                for bits in map(int, args.bits.split(",")):
                    for sample in range(args.samples):
                        seed = args.seed + len(cases)
                        data = generate_workload(seed, family, size, bits)
                        cases.append({"family": family, "target_nodes": size, "seed": seed, "input": data})
    corpus = destination / "inputs.jsonl"
    corpus.write_text("".join(json.dumps(case, separators=(",", ":")) + "\n" for case in cases), encoding="utf-8")
    records, variants = [], args.variants.split(",")
    outputs_path = destination/"optimized_outputs.jsonl"
    outputs_stream = outputs_path.open("w",encoding="utf-8")
    orders_path = destination/"original_orders.jsonl"
    orders_stream = orders_path.open("w",encoding="utf-8")
    for case_index, case in enumerate(cases):
        # Alternate ordering avoids assigning all cold starts to one variant.
        ordering = variants[case_index % len(variants):] + variants[:case_index % len(variants)]
        for variant in ordering:
            record = run_case(case["input"], variant, args.time_budget_ms, args.max_states,
                              outputs_stream if variant == args.after else None,
                              orders_stream if variant == args.after else None)
            record.update(family=case["family"], seed=case["seed"], target_nodes=case["target_nodes"])
            records.append(record)
        if (case_index + 1) % 32 == 0:
            print(json.dumps({"progress": case_index + 1, "total": len(cases), "elapsed_s": perf_counter()-started}), flush=True)
    outputs_stream.close()
    orders_stream.close()
    summary = {}
    for variant in variants:
        group = [r for r in records if r["variant"] == variant]
        valid = [r for r in group if r["status"] == "verified"]
        summary[variant] = {"attempted": len(group), "verified": len(valid),
                            "statuses": {status: sum(r["status"] == status for r in group) for status in sorted({r["status"] for r in group})},
                            "total_inserted_copies_successes": sum(r["inserted_copies"] for r in valid),
                            "total_output_count_successes": sum(r["output_count"] for r in valid),
                            "optimizer_ms_all_inputs": {f"p{int(q*100)}": percentile([r["optimizer_ms"] for r in group], q) for q in (.5,.95,.99)}}
    # Preserve the prior last-record-per-hash behavior, but avoid scanning all
    # records for each input (10000 graphs previously spent ~68s pairing).
    indexed_records={}
    for record in records:indexed_records.setdefault(record['sha256'],{})[record['variant']]=record
    paired = []
    for case in cases:
        key = fingerprint(case["input"])
        row_map = indexed_records.get(key,{})
        if args.before not in row_map or args.after not in row_map:
            continue
        before, after = row_map[args.before], row_map[args.after]
        pair = {"sha256": key, "family": case["family"], "target_nodes": case["target_nodes"],
                "before_status": before["status"], "after_status": after["status"]}
        if before["status"] == after["status"] == "verified":
            pair.update(copy_delta=after["inserted_copies"]-before["inserted_copies"],
                        optimizer_speedup=before["optimizer_ms"] / max(after["optimizer_ms"], 1e-9),
                        before_ms=before["optimizer_ms"], after_ms=after["optimizer_ms"])
        paired.append(pair)
    report = {"round": args.round, "dataset": "synthetic research graphs; not official or real application traces",
              "seed": args.seed, "case_count": len(cases), "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
              "budget_ms": args.time_budget_ms, "max_states": args.max_states,
              "paired_variants": {"before": args.before, "after": args.after},
              "runtime": {"python": sys.version, "platform": platform.platform(), "single_process": True},
              "current_source_manifest_at_start": source_manifest,
              "executed_harness_sha256":executed_harness_sha256,
              "frozen_baselines":{variant:{'module':OPTIMIZERS[variant].__module__,
                  'optimizer_path':str(Path(sys.modules[OPTIMIZERS[variant].__module__].__file__).relative_to(ROOT)),
                  'source_manifest':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in Path(sys.modules[OPTIMIZERS[variant].__module__].__file__).parent.glob('*.py')}}
                  for variant in variants if variant=='v14_auto'},
              'level_r91_frozen_source_manifest':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in (ROOT/'experiments/baseline_level_r91').glob('*.py')}if 'level_r91'in variants else None,
              'phase_r102_frozen_source_manifest':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in (ROOT/'experiments/baseline_phase_r102').glob('*.py')}if 'phase_r102'in variants else None,
              "optimized_outputs_sha256":hashlib.sha256(outputs_path.read_bytes()).hexdigest(),
              "original_orders_sha256":hashlib.sha256(orders_path.read_bytes()).hexdigest(),
              "elapsed_seconds": perf_counter()-started, "summary": summary, "paired": paired, "records": records}
    output = destination / "report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    import csv
    columns = sorted({key for row in records for key in row})
    with (destination / "records.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader(); writer.writerows(records)
    print(json.dumps({"report": str(output), "summary": summary}, ensure_ascii=False), flush=True)
    if any(r["status"] == "verification_failure" for r in records):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
