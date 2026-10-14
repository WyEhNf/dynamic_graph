"""Independent complete/budgeted capacity audit; preserve input/source hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.branch_capacity import branch_capacity_oracle
from isa_scheduler.evaluation import fingerprint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="experiments/r18-failure-audit/inputs.jsonl")
    parser.add_argument("--round",default="r25-branch-capacity")
    parser.add_argument("--time-budget-ms",type=float,default=1000)
    parser.add_argument("--max-states",type=int,default=200000)
    args=parser.parse_args()
    if not args.round.replace("-","").replace("_","").isalnum():raise ValueError("Safe round name required")
    destination=ROOT/"experiments"/args.round;destination.mkdir(exist_ok=False)
    corpus=(ROOT/args.source).read_bytes();records=[]
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")}
    tick=perf_counter();selected=[]
    for case in map(json.loads,corpus.decode("utf8").splitlines()):
        data=case["input"]
        if case["family"]!="cross_group_shared":continue
        selected.append(case)
        result=branch_capacity_oracle(data,time_budget_ms=args.time_budget_ms,max_states=args.max_states)
        records.append({"block_id":data["block_id"],"input_sha256":fingerprint(data),"seed":case["seed"],"node_count":len(data["instructions"]),**result})
    (destination/"inputs.jsonl").write_text("".join(json.dumps(case,separators=(",",":"))+"\n" for case in selected),encoding="utf8")
    report={"source_corpus_sha256":hashlib.sha256(corpus).hexdigest(),"source_manifest_at_start":manifest,
            "time_budget_ms":args.time_budget_ms,"max_states":args.max_states,"elapsed_s":perf_counter()-tick,"records":records}
    (destination/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":main()
