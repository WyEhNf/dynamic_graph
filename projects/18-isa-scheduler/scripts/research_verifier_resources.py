"""Allocation cost of a fresh raw-JSON verification, excluding input loading."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='experiments/r41-token-reuse')
    parser.add_argument('--variant',choices=('r40','current'),default='current')
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',default='experiments/r45-verifier-resources.json')
    args=parser.parse_args()
    source=ROOT/args.source
    if args.worker:
        report=json.loads((source/'report.json').read_text())
        target=max((r for r in report['records'] if r['variant']=='current_auto' and r['status']=='verified'),key=lambda r:r['output_count'])
        with (source/'inputs.jsonl').open() as stream:
            for line in stream:
                data=json.loads(line)['input']
                if fingerprint(data)==target['sha256']:break
            else:raise ValueError('Missing original')
        with (source/'optimized_outputs.jsonl').open() as stream:
            for line in stream:
                saved=json.loads(line)
                if saved['input_sha256']==target['sha256'] and saved['variant']=='current_auto':break
            else:raise ValueError('Missing output')
        if fingerprint(saved['output'])!=target['output_sha256']:raise ValueError('Output changed')
        if args.variant=='r40':
            from experiments.baseline_r40.isa_scheduler.verify import verify
            path=ROOT/'experiments/baseline_r40/isa_scheduler/verify.py'
        else:
            from isa_scheduler.verify import verify
            path=ROOT/'isa_scheduler/verify.py'
        tracemalloc.start();start=perf_counter();result=verify(data,saved['output'])
        elapsed=perf_counter()-start;peak=tracemalloc.get_traced_memory()[1]
        print(json.dumps({'variant':args.variant,'valid':result['valid'],'input_sha256':target['sha256'],
            'output_sha256':target['output_sha256'],'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'input_nodes':len(data['instructions']),'output_nodes':target['output_count'],
            'peak_verification_traced_bytes':peak,'elapsed_with_tracing_s':elapsed}));return
    path=ROOT/args.output
    if path.exists():raise SystemExit('Choose a fresh output; preserve evidence')
    rows=[];start=perf_counter()
    for repeat in range(args.repeats):
        for variant in (('r40','current') if repeat%2==0 else ('current','r40')):
            result=subprocess.run([sys.executable,__file__,'--worker','--variant',variant,'--source',args.source],check=True,capture_output=True,text=True)
            row=json.loads(result.stdout);row['repeat']=repeat;rows.append(row)
    path.write_text(json.dumps({'source':args.source,'measurement':'fresh independent raw-JSON verification; excludes input/output JSON loading and scheduler; isolated processes with tracemalloc; instrumentation time is not ordinary latency',
        'elapsed_s':perf_counter()-start,'records':rows},indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
