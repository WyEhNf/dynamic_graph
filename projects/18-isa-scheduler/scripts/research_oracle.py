"""Ablate exact search ordering/dominance with independent output validation."""
import argparse
import collections
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint, percentile
from isa_scheduler.fuzz import generate
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, parse_block
from isa_scheduler.search import search
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=1000);parser.add_argument('--seed',type=int,default=30001)
    parser.add_argument('--hard',action='store_true');parser.add_argument('--time-budget-ms',type=float,default=250)
    parser.add_argument('--max-states',type=int,default=30000);parser.add_argument('--max-nodes',type=int,default=10)
    parser.add_argument('--output',default='experiments/oracle/report.json');args=parser.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    started=perf_counter();records=[];cases=[]
    configs=[('fifo',False,False),('progress',False,True),('progress_dominance',True,True)]
    if args.hard:
        pool=[]
        for family in ('balanced_tree','skew_tree','ladder_diamond','butterfly','sparse_shared','hazard_multi'):
            for size in (12,16):
                for bits in range(2,6):
                    pool.append(generate_workload(args.seed+len(pool),family,size,bits))
    else:
        pool=[generate(args.seed+i,('wide','branch','highfanout','hazard')[i%4],2+(i//4)%4)for i in range(args.count)]
    for i,data in enumerate(pool):
        cases.append(data);costs=[]
        for label,dominance,progress in configs[i%3:]+configs[:i%3]:
            tick=perf_counter();row={'seed':args.seed+i,'sha256':fingerprint(data),'variant':label,'status':'started'}
            try:
                result=search(parse_block(data),time_budget_ms=args.time_budget_ms,max_states=args.max_states,
                              exact_max_nodes=args.max_nodes,dominance=dominance,progress_tie=progress)
                row['search_ms']=(perf_counter()-tick)*1000
                verify(data,result)
                row.update(status='verified',copies=result['stats']['inserted_copy_count'],**result['stats']['search'])
                if row['outcome']=='optimal_under_model':costs.append(row['copies'])
            except BudgetExceeded as exc:row.update(status='budget_exhausted',error=str(exc))
            except InfeasibleSchedule as exc:row.update(status='proven_infeasible_under_model',error=str(exc));costs.append(None)
            row.setdefault('search_ms',(perf_counter()-tick)*1000);records.append(row)
        if len(set(costs))>1:
            (output.parent/'oracle-mismatch.json').write_text(json.dumps(data,indent=2))
            raise RuntimeError('Different full-model optimum/infeasibility outcomes')
    (output.parent/'inputs.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in cases))
    summary={}
    for label,_,_ in configs:
        group=[r for r in records if r['variant']==label]
        summary[label]={'status_counts':dict(collections.Counter(r['status']for r in group)),
                        'expanded_states':sum(r.get('explored_states',0)for r in group),
                        'dominated_enqueues':sum(r.get('dominated_enqueue_states',0)for r in group),
                        'latency_ms':{f'p{int(q*100)}':percentile([r['search_ms']for r in group],q)for q in (.5,.95,.99)}}
    report={'seed':args.seed,'case_count':len(pool),'hard':args.hard,'max_nodes':args.max_nodes,
            'time_budget_ms':args.time_budget_ms,'max_states':args.max_states,
            'scope':'original DAG; single emission; COPY only; hazard memory order; finite bounded search; partial budget outcomes are not proofs',
            'elapsed_seconds':perf_counter()-started,'summary':summary,'records':records}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
