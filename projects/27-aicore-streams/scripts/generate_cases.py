"""Generate local JSON cases with independently computable feasibility witnesses."""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path


def task(op, waits=(), record=-1):
    return {"op_id": op, "wait_before": list(waits), "record_after": record}


def plan(*streams):
    return {"streams": [{"tasks": list(s)} for s in streams]}


def node(i, kind, cores, duration, work, output, inputs=()):
    return dict(id=i, core_type=kind, core_num=cores, exec_time=duration,
                workspace_memory=work, output_memory=output, inputs=list(inputs))


def hardware(aic=8, aiv=8, streams=8, memory=1000, record=2, wait=3):
    return dict(aic_core_num=aic, aiv_core_num=aiv, stream_num=streams,
                memory_limit=memory, event_record_time=record, event_wait_time=wait)


def serial_witness(nodes):
    """Nodes are in a known topological order. Count original DIRECT consumer ends."""
    index = {x["id"]: x for x in nodes}
    users = {x["id"]: 0 for x in nodes}
    for x in nodes:
        for p in x["inputs"]:
            users[p] += 1
    live = peak = duration = 0
    finished = set()
    for x in nodes:
        assert all(p in finished for p in x["inputs"])
        live += x["workspace_memory"] + x["output_memory"]
        peak = max(peak, live)
        live -= x["workspace_memory"]
        for p in x["inputs"]:
            users[p] -= 1
            if users[p] == 0:
                live -= index[p]["output_memory"]
        duration += x["exec_time"]
        finished.add(x["id"])
    return plan([task(x["id"]) for x in nodes]), duration, peak


def case(name, hw, nodes, deadline, witness=None, expected=True):
    x = dict(name=name, hardware=hw, nodes=nodes, deadline_us=deadline,
             expected_feasible=expected)
    if witness is not None:
        x["witness_plan"] = witness
    return x


def official_samples():
    n1 = [node(0,"AIV",4,40,60,40), node(1,"AIV",6,50,70,50,[0]),
          node(2,"AIC",12,120,160,80,[1]), node(3,"AIC",6,70,90,20,[2]),
          node(4,"AIC",8,90,100,30,[2]), node(5,"AIV",8,60,80,10,[3,4])]
    p1=plan([task(0),task(1),task(2,record=0),task(4),task(5,[1])], [task(3,[0],1)])
    n2=[node(0,"AIC",8,100,20,10),node(1,"AIV",4,80,15,10),node(2,"AIV",4,20,10,5,[0,1])]
    p2=plan([task(0,record=0)], [task(1),task(2,[0])])
    n3=[node(0,"AIC",4,60,20,10),node(1,"AIV",4,50,20,5),node(2,"AIC",4,100,5,5,[1])]
    p3=plan([task(0,[0])],[task(1,record=0),task(2)])
    return [case("official_1",hardware(16,12,3,400,2,3),n1,400,p1),
            case("official_2",hardware(8,8,2,200,2,2),n2,200,p2),
            case("official_3_extra_event",hardware(8,8,2,50,2,3),n3,220,p3)]


def synthetic(seed, n, shape, variant):
    rng=random.Random(seed)
    ids=[1000000000+i*29 for i in range(n)]
    if variant=="shuffled_ids": rng.shuffle(ids)
    nodes=[]
    for i, identity in enumerate(ids):
        if shape=="chain": preds=[i-1] if i else []
        elif shape=="layered":
            width=8; start=max(0,(i//width-1)*width);stop=(i//width)*width
            preds=rng.sample(range(start,stop), min(3, stop-start)) if stop else []
        elif shape=="sinks": preds=[i-1] if i and i<n//2 else ([rng.randrange(n//2)] if i>=n//2 and n>1 else [])
        else: preds=sorted({rng.randrange(i) for _ in range(rng.randrange(4))}) if i else []
        duration=rng.randrange(1,101) if variant!="time64" else 1000000000
        work=rng.randrange(0,51);output=rng.randrange(0,21)
        cores=rng.randrange(1,5) if variant!="core128" else 128
        nodes.append(node(identity,"AIC" if rng.randrange(2) else "AIV",cores,duration,work,output,[ids[p] for p in preds]))
    witness, total, peak=serial_witness(nodes)
    # Tight memory equals known witness peak. Permuted IDs use an order-independent upper bound.
    limit=peak if variant!="shuffled_ids" else sum(x["output_memory"] for x in nodes)+max((x["workspace_memory"] for x in nodes),default=0)
    ev=1000000 if variant=="large_event" else (0 if variant=="zero_event" else 3)
    cap=128 if variant=="core128" else 8
    hw=hardware(cap,cap,8,max(1,limit),ev,ev)
    rng.shuffle(nodes)
    x=case(f"{shape}_{variant}_n{n}_seed{seed}",hw,nodes,total,witness)
    x["generation"]={"seed":seed,"feasibility":"explicit serial witness", "witness_T":total,"witness_peak":peak}
    return x


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("data/stress.json"))
    parser.add_argument("--quick",action="store_true")
    parser.add_argument("--seed",type=int,default=20261010)
    args=parser.parse_args()
    cases=official_samples()
    sizes=[4,16,64] if args.quick else [4,16,64,256,1024,4096]
    variants=["normal","zero_event","large_event","shuffled_ids","time64","core128"]
    for n in sizes:
        for j,variant in enumerate(variants):
            for k,shape in enumerate(["random","layered","sinks","chain"]):
                cases.append(synthetic(args.seed+n*100+j*10+k,n,shape,variant))
    for n in [16,64,128,256]:
        hw=hardware(128,128,n,1000000,0,0)
        nodes=[node(100+i*7,"AIC" if i%2 else "AIV",1,100,1,1) for i in range(n)]
        witness=plan(*[[task(x["id"])] for x in nodes])
        cases.append(case(f"tight_parallel_n{n}",hw,nodes,100,witness))
    cases.append(case("proven_impossible_deadline",hardware(),[node(777,"AIC",1,100,0,0)],99,expected=False))
    cases.append(case("empty_graph",hardware(),[],0,plan([])))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"format":"aicore-local-v1","generator_seed":args.seed,"cases":cases},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"generated {len(cases)} local cases -> {args.output}")


if __name__=="__main__": main()
