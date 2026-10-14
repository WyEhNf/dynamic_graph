"""Larger closed subsets using age-free DP; no runnable-witness claims."""
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
from isa_scheduler.model import BudgetExceeded,parse_block
from isa_scheduler.relaxed_capacity import capacity_oracle


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="experiments/r20-closed-obstructions")
    parser.add_argument("--round",default="r22-capacity-obstructions")
    parser.add_argument("--max-nodes",type=int,default=32)
    parser.add_argument("--max-candidates",type=int,default=12)
    parser.add_argument("--time-budget-ms",type=float,default=1000)
    args=parser.parse_args()
    if not args.round.replace("-","").replace("_","").isalnum():raise ValueError("Safe round name required")
    source=ROOT/args.source;previous=json.loads((source/"report.json").read_text(encoding="utf-8"))
    corpus=(ROOT/previous["source"]/"inputs.jsonl").read_bytes()
    if hashlib.sha256(corpus).hexdigest()!=previous["source_corpus_sha256"]:raise ValueError("Corpus changed")
    cases={fingerprint(case["input"]):case for case in map(json.loads,corpus.decode("utf-8").splitlines())}
    destination=ROOT/"experiments"/args.round;destination.mkdir(parents=True,exist_ok=False)
    records=[];started=perf_counter()
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"isa_scheduler").glob("*.py")}
    for previous_row in previous["records"]:
        if previous_row["status"]!="unresolved":continue
        case=cases[previous_row["input_sha256"]];data=case["input"];block=parse_block(data)
        row={"input_sha256":fingerprint(data),"family":case["family"],"seed":case["seed"],"status":"unresolved"};probes=[]
        for indices in candidate_closures(block,args.max_nodes,args.max_candidates):
            projected=closed_subset_data(data,indices);probe={"nodes":len(indices),"sha256":fingerprint(projected)}
            try:
                result=capacity_oracle(parse_block(projected),max_nodes=args.max_nodes,max_states=200000,
                                       time_budget_ms=args.time_budget_ms,depth_first=True)
                probe.update(status=result["outcome"],capacity_dp=result)
                if result["outcome"].startswith("proven"):
                    row.update(status="closed_capacity_obstruction",original_indices=indices,obstruction_input=projected)
            except BudgetExceeded as exc:probe.update(status="budget_exhausted",error=str(exc))
            probes.append(probe)
            if row["status"]!="unresolved":break
        row["probes"]=probes;records.append(row)
        print(json.dumps({"progress":len(records),"family":row["family"],"status":row["status"],"probes":len(probes)}),flush=True)
    report={"source":args.source,"source_corpus_sha256":hashlib.sha256(corpus).hexdigest(),"source_manifest_at_start":manifest,
            "max_nodes":args.max_nodes,"max_candidates":args.max_candidates,"budget_ms":args.time_budget_ms,
            "elapsed_s":perf_counter()-started,"records":records,
            "scope":"pure closed projections; full age-free capacity DP; identity-preserving single emission; no alias/recompute/reread/spill"}
    (destination/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"elapsed_s":report["elapsed_s"],"statuses":dict(collections.Counter(row["status"] for row in records))}))


if __name__=="__main__":main()
