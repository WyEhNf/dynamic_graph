"""Frozen/current isolated-process allocation comparison; not throughput."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research_resources import peak_rss
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--variant',choices=('r40','r66','current','bound'),default='current')
    parser.add_argument('--variants',default='r40,current')
    parser.add_argument('--size',type=int,default=8192)
    parser.add_argument('--bits',type=int,default=5)
    parser.add_argument('--seed',type=int,default=18001)
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',default='experiments/r42-token-resources.json')
    args=parser.parse_args()
    if args.worker:
        if args.variant=='r40':
            from experiments.baseline_r40.isa_scheduler.optimizer import optimize
            directory=ROOT/'experiments/baseline_r40/isa_scheduler'
        elif args.variant=='r66':
            from experiments.baseline_r66.isa_scheduler.optimizer import optimize
            directory=ROOT/'experiments/baseline_r66/isa_scheduler'
        else:
            from isa_scheduler.optimizer import optimize
            directory=ROOT/'isa_scheduler'
        manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.py')}
        tracemalloc.start();started=perf_counter()
        data=generate_workload(args.seed,'near_window_spine',args.size,args.bits)
        result=optimize(data,'bound_portfolio' if args.variant=='bound' else 'auto',time_budget_ms=20000)
        verify(data,result)
        elapsed=perf_counter()-started
        peak=tracemalloc.get_traced_memory()[1]
        core={'block_id':result['block_id'],'optimized_instructions':result['optimized_instructions']}
        print(json.dumps({'variant':args.variant,'input_sha256':fingerprint(data),
            'output_sha256':fingerprint(core),'source_manifest_at_start':manifest,
            'node_count':len(data['instructions']),'bit_width':args.bits,
            'copies':result['stats']['inserted_copy_count'],'verified':True,
            'selected_strategy':result['stats']['strategy'],'attempts':result['stats'].get('attempts'),
            'portfolio_elapsed_ms':result['stats'].get('portfolio_elapsed_ms'),
            'approximation_certificate':result['stats'].get('approximation_certificate'),
            'elapsed_with_tracing_s':elapsed,'peak_traced_bytes':peak,
            'peak_process_working_set_bytes':peak_rss()}));return
    path=Path(args.output)
    if path.exists():raise SystemExit('Evidence exists; choose a fresh output path')
    started=perf_counter();records=[]
    variants=tuple(args.variants.split(','))
    if not variants or any(variant not in ('r40','r66','current','bound') for variant in variants):raise ValueError('Invalid resource variants')
    for repeat in range(args.repeats):
        for variant in (variants if repeat%2==0 else variants[::-1]):
            command=[sys.executable,__file__,'--worker','--variant',variant,'--size',str(args.size),
                     '--bits',str(args.bits),'--seed',str(args.seed)]
            run=subprocess.run(command,capture_output=True,text=True,check=True)
            row=json.loads(run.stdout);row['repeat']=repeat;records.append(row)
            print(json.dumps({k:row[k] for k in ('variant','repeat','copies','peak_traced_bytes')}),flush=True)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'runtime':platform.platform(),'python':sys.version,
        'measurement':'isolated processes; alternating order; tracemalloc includes generation/optimization/independent symbolic verify; elapsed is not ordinary throughput',
        'elapsed_seconds':perf_counter()-started,'records':records},indent=2)+'\n')


if __name__=='__main__':main()
