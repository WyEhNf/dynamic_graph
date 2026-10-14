"""Middle-shape cost batch: physical B32 versus B64, fixed hybrid kernel."""
from pathlib import Path
import hashlib,json,statistics,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/shape-cost-milestone';root.mkdir(exist_ok=True)
    variants={'hybrid':project/'build-hybrid/cholesky_runtime.exe'}
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest()for k,v in variants.items()},'stress':[],'performance':[],'summary':[],'references':[],'contract':'original C source full bytes; no per-cell reordering; independently compiled reference','concurrency_note':'other projects may execute concurrently; rotated local observations; dense N10000 t4 repeated3, t1 once'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'shape-cost-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();metas={}
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    for label,source,function in sources[:2]:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function)
    for n in (384,512,640,768,896,1023,1024,1152,1536,2048):
        ip,ref,provenance=ensure_dense_reference(project,n);report['references'].append(provenance)
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        configs=[(variant,count,b)for count in(1,4)for b in ((64,)if n==10000 else(32,64))for variant in variants]
        for repeat in range(3 if n==10000 else 5):
            for variant,count,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                if n==10000 and count==1 and repeat:continue
                out=folder/'runtime.bin';metrics=run_runtime(variants[variant],metas['page'],ip,out,engine='tiled',tile_size=b,threads=count,simd='auto',ready_queue='heap')
                report['performance'].append({'n':n,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS dense N10000 {variant} B{b} t{count} r{repeat}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for variant,count,b in configs:
            group=[r for r in report['performance']if(r['n'],r['variant'],r['threads'],r['tile_size'])==(n,variant,count,b)]
            report['summary'].append({'n':n,'variant':variant,'threads':count,'tile_size':b,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'median_input_read_ms':statistics.median(r['input_read_ms']for r in group),'median_output_write_ms':statistics.median(r['output_write_ms']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS shape-cost dense N={n}: strict C oracle and rotated A/B',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(root/'shape-cost-report.json')}),flush=True)

if __name__=='__main__':main()
