"""Bounded complete oracle on closed projections of unresolved pure graphs."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.closed_subgraph import candidate_closures,closed_subset_data
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.model import BudgetExceeded,InfeasibleSchedule,parse_block
from isa_scheduler.search import search
from isa_scheduler.spine_bounds import spine_capacity_bound
from isa_scheduler.verify import verify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="experiments/r18-failure-audit")
    parser.add_argument("--round",default="r20-closed-obstructions")
    parser.add_argument("--max-nodes",type=int,default=16)
    parser.add_argument("--max-candidates",type=int,default=60)
    parser.add_argument("--time-budget-ms",type=float,default=100)
    args=parser.parse_args()
    if not args.round.replace("-","").replace("_","").isalnum():raise ValueError("Safe round name required")
    destination=ROOT/"experiments"/args.round;destination.mkdir(parents=True,exist_ok=False)
    corpus=(ROOT/args.source/"inputs.jsonl").read_bytes()
    source=json.loads((ROOT/args.source/"report.json").read_text(encoding="utf-8"))
    if hashlib.sha256(corpus).hexdigest()!=source["audit_corpus_sha256"]:raise ValueError("Audit corpus changed")
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")}
    records=[];started=perf_counter()
    for case in map(json.loads,corpus.decode("utf-8").splitlines()):
        data=case["input"];block=parse_block(data)
        bound=spine_capacity_bound(block)
        if bound and bound["infeasible_under_model"]:continue
        tick=perf_counter();probes=[];row={"input_sha256":fingerprint(data),"family":case["family"],"seed":case["seed"],"status":"unresolved"}
        for indices in candidate_closures(block,args.max_nodes,args.max_candidates):
            projected=closed_subset_data(data,indices)
            probe={"nodes":len(indices),"indices":indices,"sha256":fingerprint(projected)}
            try:
                result=search(parse_block(projected),time_budget_ms=args.time_budget_ms,max_states=30000,
                              exact_max_nodes=args.max_nodes,dominance=True)
                verify(projected,result)
                probe.update(status="feasible_projection",copies=result["stats"]["inserted_copy_count"],search=result["stats"]["search"])
            except BudgetExceeded as exc:probe.update(status="budget_exhausted",error=str(exc))
            except InfeasibleSchedule as exc:
                if "proven_infeasible_under_model" not in str(exc):raise
                probe.update(status="proven_projection_infeasible_under_model",error=str(exc))
                row.update(status="closed_projection_obstruction",obstruction_input=projected,original_indices=indices)
            probes.append(probe)
            if row["status"]!="unresolved":break
        row.update(probes=probes,total_ms=(perf_counter()-tick)*1000);records.append(row)
        print(json.dumps({"progress":len(records),"family":case["family"],"status":row["status"],"probes":len(probes)}),flush=True)
    report={"source":args.source,"source_corpus_sha256":hashlib.sha256(corpus).hexdigest(),"source_manifest_at_start":manifest,
            "max_nodes":args.max_nodes,"max_candidates":args.max_candidates,"oracle_budget_ms":args.time_budget_ms,
            "elapsed_s":perf_counter()-started,"records":records,
            "scope":"exact bounded-size closed-subgraph oracle; identity preserving single emission COPY-only; pure unique disjoint registers; not general official infeasibility"}
    (destination/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"elapsed_s":report["elapsed_s"],"statuses":dict(collections.Counter(row["status"] for row in records))}))


if __name__=="__main__":main()
