"""Repeat unresolved cases with a larger budget; save feasible witnesses only.

Failure at a larger budget is still not an impossibility proof. Verification
reconstructs from raw inputs and serialized output, never scheduler state.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import IntegerSemantics,interpret,verify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="experiments/milestone-v04")
    parser.add_argument("--round",default="r18-failure-audit")
    parser.add_argument("--time-budget-ms",type=float,default=1500)
    parser.add_argument("--max-states",type=int,default=100000)
    args=parser.parse_args()
    if not args.round.replace("-","").replace("_","").isalnum():raise ValueError("Safe round name required")
    source=ROOT/args.source
    corpus=(source/"inputs.jsonl").read_bytes()
    report=json.loads((source/"report.json").read_text(encoding="utf-8"))
    if hashlib.sha256(corpus).hexdigest()!=report["corpus_sha256"]:raise ValueError("Corpus changed")
    selected={row["sha256"]:row for row in report["records"] if row["variant"]==report["paired_variants"]["after"]
              and row["status"] in ("budget_exhausted","scheduling_failure")}
    cases=[case for case in map(json.loads,corpus.decode("utf-8").splitlines()) if fingerprint(case["input"]) in selected]
    destination=ROOT/"experiments"/args.round
    destination.mkdir(parents=True,exist_ok=False)
    (destination/"inputs.jsonl").write_text("".join(json.dumps(case,separators=(",",":"))+"\n" for case in cases),encoding="utf-8")
    started=perf_counter();records=[]
    source_manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")}
    with (destination/"witnesses.jsonl").open("w",encoding="utf-8") as stream:
        for case in cases:
            data=case["input"];digest=fingerprint(data);old=selected[digest]
            row={"input_sha256":digest,"family":case["family"],"seed":case["seed"],"before_status":old["status"],
                 "node_count":len(data["instructions"]),"bit_width":data["bit_width"],"status":"unresolved"}
            tick=perf_counter()
            phase='optimize'
            try:
                result=optimize(data,"auto",time_budget_ms=args.time_budget_ms,max_states=args.max_states)
                phase='independent_validate'
                core={"block_id":result["block_id"],"optimized_instructions":result["optimized_instructions"]}
                serialized=json.dumps(core,separators=(",",":"))
                reconstructed=json.loads(serialized)
                verify(data,reconstructed)
                registers={name:11*i-17 for i,name in enumerate(sorted({inst["reg"] for inst in data["instructions"] if inst["op"]=="GET"}))}
                for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
                    if interpret(data["instructions"],registers,semantics)!=interpret(reconstructed["optimized_instructions"],registers,semantics):
                        raise ValueError("Differential mismatch")
                row.update(status="verified_feasible_witness",output_sha256=fingerprint(core),
                           inserted_copies=result["stats"]["inserted_copy_count"],strategy=result["stats"]["strategy"],
                           attempts=result["stats"]["attempts"])
                stream.write(json.dumps({"input_sha256":digest,"output":core},separators=(",",":"))+"\n")
            except Exception as exc:
                row.update(exception=type(exc).__name__,error=str(exc))
                if phase=='independent_validate' or "mismatch" in str(exc).lower() or "Verification" in type(exc).__name__:raise
                row['failure_category']=('proven_infeasible_under_model' if 'proven_infeasible_under_model' in str(exc)
                                         else 'budget_exhausted' if 'Budget' in type(exc).__name__ else 'heuristic_failure')
            row["total_ms"]=(perf_counter()-tick)*1000;records.append(row)
    summary={"source":args.source,"source_corpus_sha256":report["corpus_sha256"],
             "audit_corpus_sha256":hashlib.sha256((destination/"inputs.jsonl").read_bytes()).hexdigest(),
             "time_budget_ms":args.time_budget_ms,"max_states":args.max_states,"elapsed_s":perf_counter()-started,
             "source_manifest_at_start":source_manifest,
             "statuses":dict(collections.Counter(row["status"] for row in records)),"records":records,
             "failure_categories":dict(collections.Counter(row.get('failure_category','verified_feasible_witness') for row in records)),
             "scope":"larger-budget witnesses; unresolved means no runnable witness; consult failure_category for model proof, budget or heuristic failure; no original-task impossibility claim"}
    (destination/"report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"count":len(records),"statuses":summary["statuses"],"elapsed_s":summary["elapsed_s"]}))


if __name__=="__main__":main()
