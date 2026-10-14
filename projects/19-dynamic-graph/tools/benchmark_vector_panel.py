"""Milestone vectorization of independent output positions inside P/T tasks."""
from pathlib import Path
import hashlib,json,statistics,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/vector-panel-milestone';root.mkdir(exist_ok=True)
    variants={'hybrid':project/'artifacts/baseline-shape-runtime.exe','vector_panel':project/'build-vector-panel/cholesky_runtime.exe'}
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest()for k,v in variants.items()},'stress':[],'performance':[],'summary':[],'references':[],'contract':'original C source full bytes; no per-cell reordering; independently compiled reference','concurrency_note':'other projects may execute concurrently; rotated local observations; dense N10000 t4 repeated3, t1 once'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'vector-panel-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();metas={}
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function,compact_bytecode=False);oracle=compile_oracle(source,function,folder,'gcc',label=='blocked')
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129,193],mode);ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for variant in ('vector_panel',):
                for b in (4,7,16,31,32,64,96,128):
                    out=folder/'runtime.bin';metrics=run_runtime(variants[variant],metas[label],ip,out,engine='tiled',tile_size=b,threads=4,block=7,simd='auto',ready_queue='heap',structure='dense')
                    report['stress'].append({'source':label,'mode':mode,'variant':variant,**metrics,**exact_compare(ref,out)})
            save()
        print(f'PASS four-row {label}: FP/odd rows/tail blocks and worker wakeups',flush=True)
    for n in (512,2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);report['references'].append(provenance)
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        configs=[(variant,count,b)for count in((1,4,8,16)if n>=4096 else(1,4))for b in ((64,96)if n>=4096 else(32,64))for variant in variants]
        for repeat in range(3 if n==10000 else 5):
            for variant,count,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                if n==10000 and count==1 and repeat:continue
                out=folder/'runtime.bin';metrics=run_runtime(variants[variant],metas['page'],ip,out,engine='tiled',tile_size=b,threads=count,simd='auto',ready_queue='heap',structure='dense')
                report['performance'].append({'n':n,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS dense N10000 {variant} B{b} t{count} r{repeat}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for variant,count,b in configs:
            group=[r for r in report['performance']if(r['n'],r['variant'],r['threads'],r['tile_size'])==(n,variant,count,b)]
            report['summary'].append({'n':n,'variant':variant,'threads':count,'tile_size':b,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'median_input_read_ms':statistics.median(r['input_read_ms']for r in group),'median_output_write_ms':statistics.median(r['output_write_ms']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS four-row dense N={n}: strict C oracle and rotated A/B',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(root/'vector-panel-report.json')}),flush=True)

if __name__=='__main__':main()
