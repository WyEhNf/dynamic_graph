"""Recheck saved obstructions using independent age-free capacity DP."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.closed_subgraph import closed_subset_data
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.model import parse_block
from isa_scheduler.relaxed_capacity import capacity_oracle


def main():
    parser=argparse.ArgumentParser();parser.add_argument("directory",default="experiments/r20-closed-obstructions",nargs="?")
    args=parser.parse_args();folder=ROOT/args.directory
    report=json.loads((folder/"report.json").read_text(encoding="utf-8"))
    source=(ROOT/report["source"]/"inputs.jsonl").read_bytes()
    if hashlib.sha256(source).hexdigest()!=report["source_corpus_sha256"]:raise ValueError("Source corpus changed")
    originals={fingerprint(case["input"]):case["input"] for case in map(json.loads,source.decode("utf-8").splitlines())}
    records=[];started=perf_counter()
    for row in report["records"]:
        if row["status"]!="closed_projection_obstruction":continue
        expected=closed_subset_data(originals[row["input_sha256"]],row["original_indices"])
        if expected!=row["obstruction_input"]:raise ValueError("Closed projection embedding mismatch")
        result=capacity_oracle(parse_block(expected),time_budget_ms=5000,max_states=1<<20)
        records.append({"original_sha256":row["input_sha256"],"projection_sha256":fingerprint(expected),
                        "family":row["family"],"seed":row["seed"],"capacity_dp":result})
    output={"elapsed_s":perf_counter()-started,"source_report_sha256":hashlib.sha256((folder/"report.json").read_bytes()).hexdigest(),
            "source_code_sha256":hashlib.sha256((ROOT/"isa_scheduler/relaxed_capacity.py").read_bytes()).hexdigest(),"records":records,
            "independent_capacity_obstructions":sum(row["capacity_dp"]["outcome"].startswith("proven") for row in records),
            "scope":"age-free relaxation; feasible DP does not refute age-window obstruction and is not an ISA witness"}
    (folder/"independent-capacity-replay.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    print(json.dumps({"count":len(records),"independent_capacity_obstructions":output["independent_capacity_obstructions"],"elapsed_s":output["elapsed_s"]}))


if __name__=="__main__":main()
