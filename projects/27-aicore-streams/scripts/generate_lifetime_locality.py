"""Fresh irregular graphs controlling zero vs positive shared-root output."""
import argparse
import json
from pathlib import Path
from generate_irregular_consumers import irregular_case
from generate_cases import serial_witness


def main():
    p=argparse.ArgumentParser();p.add_argument("--seed",type=int,default=20261024);p.add_argument("--output",type=Path,default=Path("data/lifetime-locality.json"));args=p.parse_args();cases=[]
    for count in [12,32,96]:
        for f,family in enumerate(["local","dense","global"]):
            for retained in [0,1]:
                for root_memory in [0,5]:
                    x=irregular_case(args.seed+count*100+f*10+retained,count,family,retained)
                    for v in x["nodes"]:
                        if not v["inputs"]:v["output_memory"]=root_memory
                    by_id={v["id"]:v for v in x["nodes"]}
                    order=[by_id[t["op_id"]] for s in x["witness_plan"]["streams"] for t in s["tasks"]]
                    witness,T,P=serial_witness(order);x["witness_plan"]=witness;x["deadline_us"]=T;x["hardware"]["memory_limit"]=P
                    x["name"]+=f"_rootmem{root_memory}";x["generation"].update(root_output_memory=root_memory,witness_T=T,witness_peak=P)
                    cases.append(x)
    args.output.write_text(json.dumps({"format":"aicore-local-v1","generator_seed":args.seed,"cases":cases},separators=(",",":")))
    print(f"36 fresh shared-root lifetime graphs, seed{args.seed}")


if __name__=="__main__":main()
