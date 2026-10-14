"""Batch verify automatic physical tile selection and its boundary/cost tradeoff."""
from pathlib import Path
import hashlib,json,statistics,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import make_input,compile_oracle,run_runtime,exact_compare
from research_reference import ensure_dense_reference

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/policy-milestone';root.mkdir(exist_ok=True);runtime=project/'build-policy/cholesky_runtime.exe'
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'boundaries':[],'performance':[],'summary':[],'references':[],'contract':'original C full bytes, B changes task geometry only','policy':'N<=1024 B32, larger B64; auto engine tiled for proven N>=128','concurrency_note':'local possible concurrent project load;5 repeats below maximum,3 maximum t4 repeats; maximum t1 once'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'policy-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();metas={}
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function)
        oracle=compile_oracle(source,function,folder,'gcc',label=='blocked');ip=folder/'input.bin';ref=folder/'oracle.bin'
        shapes=[3,7,127,128,129,255,256,257,511,512,513,1023,1024,1025];make_input(ip,shapes)
        subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        for simd in ('portable','auto'):
            for count in(1,4):
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metas[label],ip,out,threads=count,block=7,simd=simd)
                if (metrics['tile_size_min'],metrics['tile_size_max'],metrics['effective_tile_size'])!=(32,64,64):raise AssertionError('automatic physical tile metrics do not cover actual shape policy')
                report['boundaries'].append({'source':label,'shapes':shapes,**metrics,**exact_compare(ref,out)})
        save();print(f'PASS automatic policy {label}: stage/tile and 1024/1025 boundaries, strict C',flush=True)
    for n in(129,256,512,1024,1025,2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);report['references'].append(provenance);folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        configs=[(count,label,engine,b)for count in(1,4)for label,engine,b in [('auto','auto',None),('B32','tiled',32),('B64','tiled',64)]]
        for repeat in range(3 if n==10000 else 5):
            for count,label,engine,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                if n==10000 and count==1 and repeat:continue
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metas['page'],ip,out,threads=count,engine=engine,tile_size=b)
                chosen=32 if n<=1024 else 64
                if metrics['effective_tile_size']!=(chosen if label=='auto'else b):raise AssertionError('selected tile does not match override/policy')
                report['performance'].append({'n':n,'variant':label,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS policy dense N10000 {label} t{count} r{repeat}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for count,label,_,b in configs:
            group=[r for r in report['performance']if(r['n'],r['variant'],r['threads'])==(n,label,count)]
            report['summary'].append({'n':n,'variant':label,'threads':count,'effective_tile_size':group[-1]['effective_tile_size'],'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'median_input_read_ms':statistics.median(r['input_read_ms']for r in group),'median_output_write_ms':statistics.median(r['output_write_ms']for r in group),'packed_bytes_peak':group[-1]['packed_bytes_peak'],'task_metadata_bytes_peak':group[-1]['task_metadata_bytes_peak'],'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS policy dense N={n}: full C and overridden B32/B64',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'boundaries':len(report['boundaries']),'performance':len(report['performance']),'report':str(root/'policy-report.json')}),flush=True)

if __name__=='__main__':main()
