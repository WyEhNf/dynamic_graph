"""Batched panel-cache A/B; preserve identical original-source C reference files."""
from pathlib import Path
import json,hashlib,statistics,time,subprocess
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import run_runtime,exact_compare,compile_oracle
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/panel-milestone';root.mkdir(exist_ok=True)
    executables={'before':project/'artifacts/baseline-simd-runtime.exe','panel-cache':project/'artifacts/baseline-panel-runtime.exe'}
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest()for k,v in executables.items()},'stress':[],'performance':[],'summary':[],'contract':'independent original-source C, strict full-file bytes; per-cell source order unchanged','concurrency_note':'local rotated measurements; other project load is possible'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'panel-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();metas={}
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function,compact_bytecode=False);oracle=compile_oracle(source,function,folder,'gcc',label=='blocked')
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129],mode);ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for simd in ('portable','auto'):
                for b in (7,16,32,64):
                    out=folder/'runtime.bin';metrics=run_runtime(executables['panel-cache'],metas[label],ip,out,engine='tiled',tile_size=b,threads=4,block=7,simd=simd)
                    report['stress'].append({'source':label,'mode':mode,**metrics,**exact_compare(ref,out)})
            save()
        print(f'PASS packed panel {label}: source FP bytes, both SIMD/portable tails',flush=True)
    for n in (2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);report.setdefault('references',[]).append(provenance)
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        configs=[(label,count,b)for count in(1,4)for b in(32,64,96,128)for label in executables]
        for repeat in range(1 if n==10000 else 5):
            for label,count,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                out=folder/'runtime.bin';metrics=run_runtime(executables[label],metas['page'],ip,out,engine='tiled',tile_size=b,threads=count,simd='auto')
                report['performance'].append({'n':n,'variant':label,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS dense N10000 {label} B{b} t{count}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for label,count,b in configs:
            group=[r for r in report['performance']if(r['n'],r['variant'],r['threads'],r['tile_size'])==(n,label,count,b)]
            report['summary'].append({'n':n,'variant':label,'threads':count,'tile_size':b,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_read_ms':statistics.median(r['input_read_ms']for r in group),'median_write_ms':statistics.median(r['output_write_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS panel-cache dense n={n}: full independent C files, rotated A/B',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(root/'panel-report.json')}),flush=True)

if __name__=='__main__':main()
