"""Quantify all-reordering identity-model COPY room on new forced spines."""
import argparse,json,hashlib,sys,statistics
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.workloads import generate_workload
from isa_scheduler.spine_copy_bound import spine_copy_bound
from isa_scheduler.model import parse_block
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.evaluation import fingerprint


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--round',default='r65-spine-global-margin');parser.add_argument('--seed',type=int,default=3700001)
    parser.add_argument('--samples',type=int,default=4);parser.add_argument('--budget-ms',type=float,default=2000)
    args=parser.parse_args();folder=ROOT/'experiments'/args.round;folder.mkdir()
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (ROOT/'isa_scheduler').glob('*.py')}
    inputs=[];records=[];start=perf_counter()
    for size in (128,512,2048,8192):
        for bits in (2,3,4,5):
            for sample in range(args.samples):
                seed=args.seed+len(inputs);data=generate_workload(seed,'near_window_spine',size,bits);inputs.append(data)
                row={'input_sha256':fingerprint(data),'nodes':len(data['instructions']),'bit_width':bits,'seed':seed,'status':'failed'}
                tick=perf_counter();bound=spine_copy_bound(parse_block(data));row['bound_ms']=(perf_counter()-tick)*1000;row['certificate']=bound
                try:
                    tick=perf_counter();result=optimize(data,time_budget_ms=args.budget_ms);row['optimize_ms']=(perf_counter()-tick)*1000
                    tick=perf_counter();verify(data,result)
                    initial={r['reg']:-17+3*i for i,r in enumerate(data['instructions'])if r['op']=='GET'}
                    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
                        if interpret(data['instructions'],initial,semantics)!=interpret(result['optimized_instructions'],initial,semantics):raise ValueError('Independent integer mismatch')
                    row['verify_ms']=(perf_counter()-tick)*1000
                    copies=result['stats']['inserted_copy_count'];lower=bound['copy_lower_bound']
                    if lower>copies:raise ValueError('Global lower bound contradicted by verified schedule')
                    row.update(status='verified',copies=copies,lower_bound=lower,maximum_reducible_copies=copies-lower,
                               maximum_relative_copy_reduction=(copies-lower)/copies if copies else 0,
                               required_copy_output_ratio=lower/(row['nodes']+lower),
                               actual_copy_output_ratio=copies/(row['nodes']+copies),output_sha256=fingerprint(result['optimized_instructions']))
                except Exception as exc:row.update(exception_type=type(exc).__name__,error=str(exc))
                records.append(row)
                if len(records)%16==0:print(json.dumps({'progress':len(records),'elapsed_s':perf_counter()-start}),flush=True)
    corpus=folder/'inputs.jsonl';corpus.write_text('\n'.join(json.dumps(data,separators=(',',':'))for data in inputs)+'\n')
    valid=[r for r in records if r['status']=='verified']
    report={'seed':args.seed,'case_count':len(inputs),'verified':len(valid),'elapsed_s':perf_counter()-start,'budget_ms':args.budget_ms,
            'source_manifest_at_start':manifest,'corpus_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),
            'max_global_copy_reduction_large':max(r['maximum_relative_copy_reduction']for r in valid if r['nodes']>=2048),
            'method':'new forced-spine seeds; global necessary identity bound, auto output, fresh raw symbolic verification +3 integer semantics; not official application distribution',
            'records':records}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ('records','source_manifest_at_start')}))
    return 4 if len(valid)!=len(inputs) else 0


if __name__=='__main__':raise SystemExit(main())
