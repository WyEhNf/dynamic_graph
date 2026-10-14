"""Complete shape/panel policy A/B, strict cached C truth and streaming RAM."""
from pathlib import Path
import argparse,json,shutil,statistics,struct,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference,sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('policy','notify'),default='policy');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts'/('thread-policy-milestone'if args.mode=='policy'else'bounded-notify-milestone');root.mkdir(exist_ok=True)
    variants={'shape_baseline':project/'artifacts/baseline-shape-runtime.exe','thread_policy':project/'artifacts/baseline-thread-policy-runtime.exe'}if args.mode=='policy'else{'thread_policy':project/'artifacts/baseline-thread-policy-runtime.exe','bounded_notify':project/'build-bounded-notify/cholesky_runtime.exe'}
    candidate='thread_policy'if args.mode=='policy'else'bounded_notify'
    started=time.perf_counter();source=project/'fixtures/official_naive_transcribed.c'
    report={'passed':False,'mode':args.mode,'benchmark_tool_sha256':sha256(Path(__file__)),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha256(source),'binary_sha256':{k:sha256(v)for k,v in variants.items()},'stress':[],'performance':[],'summary':[],'references':[],'contract':'full independently compiled original-C output bytes; auto geometry changes no per-cell FP64 reduction order','policy':'B32 single worker N<=1536 or multiple workers N<=1024; B96 >=8 workers and N>=4096; otherwise B64. P/T SIMD only B>=64. Policy-mode baseline auto B32/64 without P/T SIMD; notify-mode has same full policy, bounded notify releases mutex before wakeup and notifies min(released,threads-1) sleepers, completion/error wakes all.','concurrency_note':'shared host; rotated A/B and worker order, no frequency/temperature/affinity isolation','memory_method':'Win32 peak working set and peak commit; host available RAM and private bytes sampled every20ms'}
    report_name='thread-policy-report.json'if args.mode=='policy'else'bounded-notify-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/report_name).write_text(json.dumps(report,indent=2)+'\n')
    save();metas={}
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    for label,path,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(path,metas[label],'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked')
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129,193],mode);ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            stress_configs=[(b,4)for b in(4,7,16,31,32,64,96,128)]if args.mode=='policy'else[(b,t)for b in(7,32,64,96)for t in(4,8,16)]
            for b,count in stress_configs:
                out=folder/'runtime.bin';metrics=run_runtime(variants[candidate],metas[label],ip,out,engine='tiled',tile_size=b,threads=count,block=7,simd='auto',structure='dense')
                report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':mode,**metrics,**exact_compare(ref,out)})
            metrics=run_runtime(variants[candidate],metas[label],ip,out,engine='tiled',tile_size=96,threads=4,block=7,simd='portable',structure='dense')
            report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':mode,**metrics,**exact_compare(ref,out)});save()
        print(f'PASS policy FP {label}',flush=True)
    references={}
    for n in (512,1024,2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);references[n]=(ip,ref);report['references'].append(provenance)
    band=root.parent/'band-maximum-reference';record=json.loads((band/'reference-report.json').read_text())
    if not record['passed']or record['source_sha256']!=report['source_sha256']or sha256(band/'input.bin')!=record['input_sha256']or sha256(band/'oracle.bin')!=record['oracle_sha256']:raise AssertionError('banded reference provenance mismatch')
    report['band_reference']=record;save()
    workloads=[(f'dense-{n}',[n],(1,4)if n<=1024 else(1,4,8,16),3,'auto')for n in(512,1024,2048,4096,10000)]if args.mode=='policy'else[(f'dense-{n}',[n],(4,8,16),3 if n==10000 else 5,'auto')for n in(1024,2048,4096,10000)]
    workloads.extend([('mixed-stream',[4096,10000,4096],(4,8,16),3,'auto')])
    workloads.extend([('band-10000',[10000],(4,),3,'auto')]if args.mode=='policy'else[('dense-2048-B32',[2048],(4,8,16),5,32)])
    for label,sizes,workers,repeats,tile in workloads:
        folder=root/label;folder.mkdir(exist_ok=True)
        if label.startswith('band'):ip,ref=band/'input.bin',band/'oracle.bin'
        elif len(sizes)==1:ip,ref=references[sizes[0]]
        else:
            ip=folder/'input.bin';ref=folder/'oracle.bin'
            for destination,column in((ip,0),(ref,1)):
                with destination.open('wb')as stream:
                    stream.write(struct.pack('<I',len(sizes)))
                    for n in sizes:
                        with references[n][column].open('rb')as src:src.read(4);shutil.copyfileobj(src,stream)
            report['stream_provenance']={'sizes':sizes,'bytes':ref.stat().st_size,'input_sha256':sha256(ip),'oracle_sha256':sha256(ref),'construction':'concatenated verified original-C single-matrix payloads, only M header changed'};save()
        configs=[(count,variant)for count in workers for variant in variants]
        for repeat in range(repeats):
            order=configs[repeat%len(configs):]+configs[:repeat%len(configs)]
            for count,variant in order:
                if label=='dense-10000'and count==1 and repeat:continue
                out=folder/'runtime.bin';metrics=run_runtime(variants[variant],metas['page'],ip,out,engine='tiled',tile_size=tile,threads=count,probe_resources=True)
                if args.mode=='policy'and variant==candidate and not label.startswith('band'):
                    expected=[32 if n<=(1536 if count==1 else 1024)else 96 if count>=8 and n>=4096 else 64 for n in sizes]
                    if metrics['effective_tile_size']!=expected[-1]:raise AssertionError('auto B policy mismatch')
                report['performance'].append({'workload':label,'sizes':sizes,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if sizes[-1]>=4096:print(f'PASS {label} {variant} t{count} B{metrics["effective_tile_size"]} r{repeat}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for count,variant in configs:
            group=[r for r in report['performance']if(r['workload'],r['threads'],r['variant'])==(label,count,variant)]
            report['summary'].append({'workload':label,'sizes':sizes,'variant':variant,'threads':count,'repeats':len(group),'effective_tile_size':group[-1]['effective_tile_size'],'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'median_input_read_ms':statistics.median(r['input_read_ms']for r in group),'median_output_write_ms':statistics.median(r['output_write_ms']for r in group),'max_process_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in group),'max_process_peak_commit_bytes':max(r['process_peak_commit_bytes']for r in group),'host_available_ram_min_bytes':min(r['host_available_ram_min_bytes']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True)
        if len(sizes)>1:ip.unlink();ref.unlink()
        print(f'PASS complete policy {label}',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(root/report_name)}),flush=True)

if __name__=='__main__':main()
