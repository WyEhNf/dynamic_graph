"""One batched, strict-source-oracle comparison of ordered 4/8/16 lane kernels."""
from pathlib import Path
import json,statistics,time,hashlib,subprocess
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,exact_compare,run_runtime
from benchmark_extended import stress_input

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/microkernel-milestone';root.mkdir(exist_ok=True)
    executables={4:project/'artifacts/baseline-compact4-runtime.exe',8:project/'artifacts/baseline-micro8-runtime.exe',16:project/'artifacts/baseline-micro16-runtime.exe'}
    records=[];stress=[];started=time.perf_counter()
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    metadata={}
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metadata[label]=folder/'program.meta';analyze(source,metadata[label],'clang',function,compact_bytecode=False)
        oracle=compile_oracle(source,function,folder,'gcc',label=='blocked')
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129],mode);ref=folder/'oracle.bin'
            subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for width in (8,16):
                for b in (7,16,32,64):
                    out=folder/'runtime.bin';metrics=run_runtime(executables[width],metadata[label],ip,out,engine='tiled',tile_size=b,threads=4,block=7)
                    stress.append({'source':label,'mode':mode,'width':width,**metrics,**exact_compare(ref,out)})
        print(f'PASS lane kernels {label}: bit-identical difficult FP/tile-tail values',flush=True)
    for n in (512,1024,2048):
        folder=project/'artifacts/tile-milestone'/f'dense-{n}';ip=folder/'input.bin';ref=folder/'oracle.bin'
        configs=[(width,count,b)for count in(1,4)for b in(32,64)for width in(4,8,16)]
        for repeat in range(5):
            for width,count,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                out=root/'result.bin';metrics=run_runtime(executables[width],metadata['page'],ip,out,engine='tiled',tile_size=b,threads=count)
                records.append({'n':n,'width':width,'repeat':repeat,**metrics,**exact_compare(ref,out)})
        print(f'PASS lane performance n={n}: 5 rotated repetitions, threads1/4, B32/64',flush=True)
    summary=[]
    for n in (512,1024,2048):
        for width,count,b in configs:
            group=[r for r in records if(r['n'],r['width'],r['threads'],r['tile_size'])==(n,width,count,b)]
            summary.append({'n':n,'width':width,'threads':count,'tile_size':b,'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group)})
    report={'passed':True,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'stress':stress,'performance':records,'summary':summary,'runtime_sha256':{w:hashlib.sha256(exe.read_bytes()).hexdigest()for w,exe in executables.items()},'elapsed_seconds':time.perf_counter()-started,'contract':'independent original-source C oracle, strict full bytes, per-cell ascending FP operations','concurrency_note':'N10000 source oracle and other projects may run concurrently; rotated local observations'}
    (root/'microkernel-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'stress':len(stress),'performance':len(records),'summary':summary},indent=2),flush=True)

if __name__=='__main__':main()
