"""Alternating frozen/current verification-only measurement, no scheduling."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from experiments.baseline_r28.isa_scheduler.verify import verify as frozen_verify
from isa_scheduler.verify import verify,interpret,IntegerSemantics
from isa_scheduler.evaluation import fingerprint,percentile


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--source",default="experiments/r29-verifier-pass")
    parser.add_argument("--round",default="r30-verifier-cost");parser.add_argument("--repeats",type=int,default=3)
    parser.add_argument("--baseline",choices=("r28","r40","r45","r51"),default="r28")
    parser.add_argument("--phase",choices=("verify","integer"),default="verify")
    args=parser.parse_args()
    baseline_verify=frozen_verify
    if args.baseline=="r40":
        from experiments.baseline_r40.isa_scheduler.verify import verify as baseline_verify
    elif args.baseline=="r45":
        from experiments.baseline_r45.isa_scheduler.verify import verify as baseline_verify
    import importlib
    baseline_module=importlib.import_module(f"experiments.baseline_{args.baseline}.isa_scheduler.verify")
    baseline_verify=baseline_module.verify
    if args.repeats<1 or not args.round.replace("-","").isalnum():raise ValueError("Positive repeats and safe round required")
    source=ROOT/args.source;destination=ROOT/"experiments"/args.round;destination.mkdir(exist_ok=False)
    source_report=json.loads((source/"report.json").read_text())
    corpus=(source/"inputs.jsonl").read_bytes();outputs=(source/"optimized_outputs.jsonl").read_bytes()
    if hashlib.sha256(corpus).hexdigest()!=source_report["corpus_sha256"] or hashlib.sha256(outputs).hexdigest()!=source_report["optimized_outputs_sha256"]:raise ValueError("Source changed")
    originals={fingerprint(case["input"]):case["input"] for case in map(json.loads,corpus.decode().splitlines())}
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")}
    baseline_manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/f"experiments/baseline_{args.baseline}/isa_scheduler").glob("*.py")}
    records=[];tick=perf_counter()
    for index,saved in enumerate(map(json.loads,outputs.decode().splitlines())):
        data=originals[saved["input_sha256"]];timings={"frozen":[],"current":[]}
        if args.phase=="integer":
            names=sorted({row['reg'] for row in data['instructions'] if row['op']=='GET'})
            initial={name:7+3*i for i,name in enumerate(names)}
            configs=((8,True),(16,False),(32,True))
            expected=tuple(baseline_module.interpret(data['instructions'],initial,baseline_module.IntegerSemantics(*config)) for config in configs)
            def frozen_integer(original,output):
                return tuple(baseline_module.interpret(output['optimized_instructions'],initial,baseline_module.IntegerSemantics(*config)) for config in configs)
            def current_integer(original,output):
                return tuple(interpret(output['optimized_instructions'],initial,IntegerSemantics(*config)) for config in configs)
            functions=(("frozen",frozen_integer),("current",current_integer))
        else:
            expected={"valid":True,"structural":True,"symbolic_equivalence":True}
            functions=(("frozen",baseline_verify),("current",verify))
        for repeat in range(args.repeats):
            order=functions
            if (index+repeat)%2:order=tuple(reversed(order))
            for name,function in order:
                started=perf_counter();result=function(data,saved["output"]);timings[name].append((perf_counter()-started)*1000)
                if result!=expected:raise ValueError("Independent validation result differs")
        before,after=(statistics.median(timings[name]) for name in ("frozen","current"))
        records.append({"input_sha256":saved["input_sha256"],"output_sha256":fingerprint(saved["output"]),
                        "node_count":len(data["instructions"]),"frozen_ms_median":before,"current_ms_median":after,
                        "speedup":before/after,"timings":timings})
    report={"source":args.source,"baseline":args.baseline,"phase":args.phase,"corpus_sha256":source_report["corpus_sha256"],"outputs_sha256":source_report["optimized_outputs_sha256"],
            "source_manifest_at_start":manifest,"baseline_source_manifest_at_start":baseline_manifest,"method":"single process; alternate frozen/current; symbolic verification or three fixed-width integer models on raw serialized core output; no scheduling; both independent of scheduling state",
            "repeats":args.repeats,"case_count":len(records),"elapsed_s":perf_counter()-tick,
            "median_speedup":statistics.median(row["speedup"] for row in records),
            "latency_medians_ms":{name:{f"p{int(q*100)}":percentile([row[name+"_ms_median"] for row in records],q) for q in (.5,.95,.99)} for name in ("frozen","current")},"records":records}
    (destination/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({k:v for k,v in report.items() if k!="records" and "manifest" not in k}))


if __name__=="__main__":main()
