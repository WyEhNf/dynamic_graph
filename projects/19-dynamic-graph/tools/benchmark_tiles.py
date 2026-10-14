"""Milestone: independent source oracles, boundary coverage and interleaved A/B.

All reported speed comparisons use full general dense SPD data. Structured
maximum-shape testing is separate and is never used as a dense speed claim.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import statistics
import struct
import subprocess
import time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import make_input,exact_compare,compile_oracle,run_runtime


def variant_input(path,sizes):
    """SPD diagonal dominance with mixed normal scales and negative entries."""
    with path.open('wb') as stream:
        stream.write(struct.pack('<I',len(sizes)))
        for n in sizes:
            stream.write(struct.pack('<I',n))
            # A=D C D, with C strictly diagonally dominant and D spanning powers
            # of two. This remains SPD without cancellation-heavy construction.
            scales=[2.0**((i%9-4)*12) for i in range(n)]
            for i in range(n):
                row=array('d')
                for j in range(n):
                    base=n+2 if i==j else ((((min(i,j)*1315423911)^(max(i,j)*2654435761)^91)%1001-500)/32768.0)
                    row.append(base*scales[i]*scales[j])
                stream.write(row.tobytes())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',type=Path,default=Path('build/cholesky_runtime.exe'))
    parser.add_argument('--baseline',type=Path,default=Path('artifacts/baseline-phase1-runtime.exe'))
    parser.add_argument('--clang',default='clang');parser.add_argument('--gcc',default='gcc')
    parser.add_argument('--sizes',default='256,512,1024,2048')
    parser.add_argument('--tile-sizes',default='32,64,96,128')
    parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--threads',default='1,4')
    parser.add_argument('--output-dir',type=Path,default=Path('artifacts/tile-milestone'))
    parser.add_argument('--skip-boundaries',action='store_true')
    args=parser.parse_args()
    root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    project=Path(__file__).resolve().parent.parent
    runtime=args.runtime.resolve();baseline=args.baseline.resolve()
    sizes=[int(n)for n in args.sizes.split(',')];tiles=[int(n)for n in args.tile_sizes.split(',')];threads=[int(n)for n in args.threads.split(',')]
    if any(not 3<=n<=10000 for n in sizes)or any(not 1<=b<=1024 for b in tiles)or args.repeats<1:raise ValueError('invalid benchmark configuration')
    started=time.perf_counter();boundaries=[];performance=[]
    cases=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text(encoding='utf-8').replace('return x * y + z;','return fma(x,y,z);'),encoding='utf-8')
    cases.append(('fma',fused,'cholesky'))
    metadata={};oracles={}
    for label,source,function in cases:
        folder=root/label;folder.mkdir(exist_ok=True)
        metadata[label]=folder/'program.meta';analysis=analyze(source,metadata[label],args.clang,function,compact_bytecode=False)
        oracles[label]=compile_oracle(source,function,folder,args.gcc,label=='blocked')
        if args.skip_boundaries:continue
        for tile,shape in [(1,[3,7,17]),(2,[3,7,33]),(7,[3,17,31,32,33,65]),(16,[17,31,32,33,63,64,65,129]),(31,[33,63,65,127,129,193]),(64,[63,64,65,127,128,129,193,257])]:
            input_path=folder/'input.bin';variant_input(input_path,shape)
            for block in ([1,7,32,100]if label=='blocked'and tile in(7,64)else[7]):
                reference=folder/'oracle.bin';subprocess.run([str(oracles[label]),str(input_path),str(reference),str(block)],check=True)
                for count in (1,4):
                    target=folder/'tiled.bin';metrics=run_runtime(runtime,metadata[label],input_path,target,threads=count,block=block,engine='tiled',tile_size=tile)
                    boundaries.append({'source':label,'sizes':shape,**metrics,**exact_compare(reference,target)})
        print(f'PASS {label}: ordered tile DAG vs independent C, small/odd/tail shapes and mixed scales',flush=True)
    for n in sizes:
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        input_path=folder/'input.bin';make_input(input_path,[n])
        reference=folder/'oracle.bin';oracle_start=time.perf_counter()
        subprocess.run([str(oracles['page']),str(input_path),str(reference),'32'],check=True)
        oracle_ms=(time.perf_counter()-oracle_start)*1000
        for count in threads:
            configurations=[('baseline',baseline,'auto',64),('stage',runtime,'stage',64)] + [('tiled',runtime,'tiled',b)for b in tiles]
            # A/B orders rotate to reduce systematic thermal/concurrent-load bias.
            for repeat in range(args.repeats):
                rotated=configurations[repeat%len(configurations):]+configurations[:repeat%len(configurations)]
                for label,executable,engine,tile in rotated:
                    target=folder/'runtime.bin'
                    metrics=run_runtime(executable,metadata['page'],input_path,target,threads=count,engine=engine,tile_size=tile)
                    performance.append({'n':n,'variant':label,'repeat':repeat,'oracle_wall_ms':oracle_ms,**metrics,**exact_compare(reference,target)})
        print(f'PASS dense n={n}: interleaved before/stage/tiled configurations, strict C oracle',flush=True)
    summary=[]
    for n in sizes:
        for count in threads:
            baseline_ms=statistics.median(r['compute_ms']for r in performance if r['n']==n and r['threads']==count and r['variant']=='baseline')
            for label,tile in [('baseline',64),('stage',64)]+[('tiled',b)for b in tiles]:
                group=[r for r in performance if r['n']==n and r['threads']==count and r['variant']==label and r['tile_size']==tile]
                summary.append({'n':n,'threads':count,'variant':label,'tile_size':tile,'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r.get('graph_ms',0)for r in group),'median_kernel_ms':statistics.median(r.get('kernel_ms',0)for r in group),'tasks':group[-1].get('task_count',0),'packed_bytes':group[-1].get('packed_bytes_peak',0),'speedup_vs_phase1':baseline_ms/statistics.median(r['compute_ms']for r in group)})
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':True,'milestone':'ordered parameterized tile DAG + packed panels + four independent ordered accumulators','baseline_executable_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'runtime_executable_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'hardware':{'cpu':'AMD Ryzen 9 8945HX','physical_cores':16,'logical_processors':32,'physical_ram_bytes':33605316608},'concurrency_note':'other hackathon projects may run concurrently; interleaved observations are local, not official scores','repeats':args.repeats,'boundary_runs':boundaries,'performance':performance,'summary':summary,'elapsed_seconds':time.perf_counter()-started,'contract':'FP64 round-to-nearest/default environment, no implicit FMA; explicit fma retained; +0 initialized L; strict full-file C oracle','general_dense_n10000_executed':False}
    (root/'tile-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'boundary_runs':len(boundaries),'performance_runs':len(performance),'report':str(root/'tile-report.json'),'summary':summary},indent=2,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
