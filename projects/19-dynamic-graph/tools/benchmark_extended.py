"""Second milestone: compact symbolic edges, difficult FP values and real dense scale.

Long oracle runs deliberately use the original C source, independently compiled;
completed cases are checkpointed so an interrupted run cannot masquerade as a pass.
"""
from __future__ import annotations
import argparse
from array import array
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import statistics
import struct
import subprocess
import time
from analyze_source import analyze
from evaluate_source import compile_oracle,exact_compare,make_input,run_runtime

def stress_input(path,sizes,mode):
    with path.open('wb')as stream:
        stream.write(struct.pack('<I',len(sizes)))
        for n in sizes:
            stream.write(struct.pack('<I',n))
            scales=[2.0**(-515 if mode=='subnormal'else 450 if mode=='large'else(i%9-4)*12)for i in range(n)]
            for i in range(n):
                row=array('d')
                for j in range(n):
                    if mode=='near-rank-one':value=1.0 if i==j else 1.0-2.0**-40
                    elif mode=='signed-zero':value=float(4**(i%4))if i==j else(-0.0 if(i+j)%2 else 0.0)
                    else:
                        base=n+2 if i==j else((((min(i,j)*1315423911)^(max(i,j)*2654435761)^91)%1001-500)/32768.0)
                        value=base*scales[i]*scales[j]
                    row.append(value)
                stream.write(row.tobytes())

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sizes',default='2048,4096,10000');p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--runtime',type=Path,default=Path('build/cholesky_runtime.exe'))
    p.add_argument('--baseline',type=Path,default=Path('artifacts/baseline-tile-v1-runtime.exe'))
    p.add_argument('--output-dir',type=Path,default=Path('artifacts/extended-milestone'))
    p.add_argument('--gcc',default='gcc');p.add_argument('--clang',default='clang')
    p.add_argument('--skip-stress',action='store_true');p.add_argument('--keep-large-files',action='store_true')
    args=p.parse_args();project=Path(__file__).resolve().parent.parent
    root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    runtime=args.runtime.resolve();baseline=args.baseline.resolve();started=time.perf_counter()
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'milestone':'compact formula edges and real dense scale','stress':[],'performance':[],'summary':[],'general_dense_n10000_executed':False,'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'baseline_tile_v1_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'contract':'strict complete-file original-source C oracle, default FP environment, no implicit FMA','concurrency_note':'other projects may run concurrently; local observations, not official scores'}
    def save():
        report['elapsed_seconds']=time.perf_counter()-started
        (root/'extended-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    save()
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text(encoding='utf-8').replace('return x * y + z;','return fma(x,y,z);'),encoding='utf-8');sources.append(('fma',fused,'cholesky'))
    metadata={};oracles={}
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metadata[label]=folder/'program.meta'
        analysis=analyze(source,metadata[label],args.clang,function,compact_bytecode=False)
        oracles[label]=compile_oracle(source,function,folder,args.gcc,label=='blocked')
        if args.skip_stress:continue
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'stress.bin';stress_input(ip,[3,7,17,31,33,65,127,129],mode)
            ref=folder/'oracle.bin';subprocess.run([str(oracles[label]),str(ip),str(ref),'7'],check=True)
            for engine,tile,count in [('tiled',1,4),('tiled',7,1),('tiled',16,4),('tiled',32,4),('tiled',64,4),('auto',32,4)]:
                target=folder/'runtime.bin';metrics=run_runtime(runtime,metadata[label],ip,target,engine=engine,tile_size=tile,threads=count,block=7)
                report['stress'].append({'source':label,'mode':mode,**metrics,**exact_compare(ref,target)})
            save()
        print(f'PASS stress {label}: subnormal/large/near-rank-one/signed-zero, six schedules',flush=True)
    for n in [int(x)for x in args.sizes.split(',')]:
        if not 3<=n<=10000:raise ValueError('size must be in [3,10000]')
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True);ip=folder/'input.bin'
        print(f'BEGIN full general dense n={n}: deterministic SPD input and original-source C oracle',flush=True)
        begin=time.perf_counter();make_input(ip,[n]);input_ms=(time.perf_counter()-begin)*1000
        ref=folder/'oracle.bin';begin=time.perf_counter();subprocess.run([str(oracles['page']),str(ip),str(ref),'32'],check=True)
        oracle_ms=(time.perf_counter()-begin)*1000
        print(f'ORACLE dense n={n}: {oracle_ms/1000:.3f}s, input {input_ms/1000:.3f}s',flush=True)
        configs=[(label,exe,engine,b,count)for count in (1,4)for b in (32,64)for label,exe,engine in [('tile-v1',baseline,'tiled'),('compact',runtime,'tiled')]]
        if n<10000:configs.append(('auto',runtime,'auto',32,4))
        for repeat in range(1 if n==10000 else args.repeats):
            for label,exe,engine,tile,count in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                target=folder/'runtime.bin';metrics=run_runtime(exe,metadata['page'],ip,target,engine=engine,tile_size=tile,threads=count)
                record={'n':n,'variant':label,'repeat':repeat,'input_generation_ms':input_ms,'oracle_wall_ms':oracle_ms,**metrics,**exact_compare(ref,target)}
                report['performance'].append(record);save()
                print(f'PASS dense n={n} {label} B{tile} t{count}: {metrics["compute_ms"]:.3f}ms, {metrics.get("graph_ms",0):.3f}ms graph',flush=True)
        if n==10000:report['general_dense_n10000_executed']=True
        for label,_,_,tile,count in configs:
            group=[r for r in report['performance']if r['n']==n and r['variant']==label and r['tile_size']==tile and r['threads']==count]
            report['summary'].append({'n':n,'variant':label,'tile_size':tile,'threads':count,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r.get('graph_ms',0)for r in group),'median_kernel_ms':statistics.median(r.get('kernel_ms',0)for r in group),'tasks':group[-1].get('task_count',0),'task_metadata_bytes':group[-1].get('task_metadata_bytes_peak',0),'packed_bytes':group[-1].get('packed_bytes_peak',0),'sha256':group[-1]['sha256']})
        save()
        if n>=4096 and not args.keep_large_files:
            for name in ('input.bin','oracle.bin','runtime.bin'):(folder/name).unlink(missing_ok=True)
        print(f'PASS dense n={n}: completed entire original-source C comparison',flush=True)
    report['passed']=True;save()
    print(json.dumps({'passed':True,'stress_runs':len(report['stress']),'performance_runs':len(report['performance']),'report':str(root/'extended-report.json')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
