"""Strict source/FP/tail tests, then independent C-backed column-workspace A/B.

Compute includes allocation, graph, kernel, lower-to-row-major export and final
validation. Kernel alone excludes export. Existing ordinary C references are
verified and reused; no structured analytic answer substitutes for dense truth.
"""
from pathlib import Path
import argparse,json,shutil,statistics,struct,subprocess,time,sys
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference,sha256

def main(*,milestone='column-workspace',variants=('thread-policy','column-workspace'),stress_variants=('column-workspace',),stress_queues=('heap',),perf_threads=(1,4,16),perf_sizes=(512,1024,2048,4096,10000),stream_threads=(4,16),extra_geometry=(),large_single_repeats=1,contract=None):
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('stress','performance'),default='stress');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/f'artifacts/{milestone}-milestone';root.mkdir(exist_ok=True)
    binaries={label:project/f'artifacts/baseline-{label}-runtime.exe'for label in variants}
    hashes={k:sha256(v)for k,v in binaries.items()};source=project/'fixtures/official_naive_transcribed.c';started=time.perf_counter()
    report={'passed':False,'phase':args.phase,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha256(source),'benchmark_tool_sha256':sha256(Path(__file__)),'binary_sha256':hashes,'stress':[],'performance':[],'summary':[],'references':[],'contract':'original-C complete bytes; lower tile-column workspace initialized +0; output allocated +0, lower triangle exported after tasks finish; source ascending reduction and left*right operand order unchanged','concurrency_note':'shared host, rotated candidates; no affinity/frequency/temperature isolation; compute includes final export; retained full output allocation means no promised peak RAM saving'}
    if contract:report['contract']=contract
    report['benchmark_driver_sha256']=sha256(Path(sys.argv[0]))
    report['support_tool_sha256']={name:sha256(project/'tools'/name)for name in('windows_resource_probe.py','research_reference.py','evaluate_source.py')}
    destination=root/f'{milestone}-{args.phase}-report.json'
    def save():
        report['elapsed_seconds']=time.perf_counter()-started
        # A reader sees the prior complete checkpoint, never a truncated JSON.
        temporary=destination.with_suffix('.json.partial')
        temporary.write_text(json.dumps(report,indent=2)+'\n')
        for attempt in range(10):
            try:temporary.replace(destination);break
            except PermissionError:
                if attempt==9:raise
                time.sleep(0.02)
    save()
    if args.phase=='stress':
        sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
        fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
        for label,path,function in sources:
            folder=root/label;folder.mkdir(exist_ok=True);meta=folder/'program.meta';analyze(path,meta,'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked')
            for mode in('subnormal','large','near-rank-one','signed-zero'):
                ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129,193,257],mode);ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                configs=[(b,'auto',4)for b in(2,7,16,31,32,64,96,128,1024)]+[(96,'portable',1),(96,'portable',4),(64,'auto',16)]
                for variant,b,simd,count,queue in[(v,b,s,t,q)for v in stress_variants for b,s,t in configs for q in stress_queues]:
                    out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],meta,ip,out,engine='tiled',tile_size=b,threads=count,block=7,simd=simd,structure='dense',ready_queue=queue);report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':mode,'variant':variant,**metrics,**exact_compare(ref,out)})
                save()
            ip=folder/'tiny-tile.bin';stress_input(ip,[3,7,17],'signed-zero');ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for variant,count,queue in[(v,t,q)for v in stress_variants for t in(1,4)for q in stress_queues]:
                out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],meta,ip,out,engine='tiled',tile_size=1,threads=count,block=7,simd='auto',structure='dense',ready_queue=queue);report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':'B1-small','variant':variant,**metrics,**exact_compare(ref,out)})
            if label=='blocked':
                ip=folder/'block-boundary.bin';stress_input(ip,[17,33,65,129,257],'near-rank-one')
                for block in(1,32,100):
                    subprocess.run([str(oracle),str(ip),str(ref),str(block)],check=True)
                    for variant,count,b,queue in[(v,t,b,q)for v in stress_variants for t,b in((1,7),(4,32),(16,96))for q in stress_queues]:
                        out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],meta,ip,out,engine='tiled',tile_size=b,threads=count,block=block,structure='dense',ready_queue=queue);report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':'source-block-boundary','variant':variant,**metrics,**exact_compare(ref,out)})
            save();print(f'PASS {milestone} {label}: separate/FMA, portable/ISA, odd tail, B>N, B1, 1/4/16 threads',flush=True)
    else:
        evidence=json.loads((root/f'{milestone}-stress-report.json').read_text())
        if not evidence['passed']or evidence['binary_sha256']!=hashes:raise AssertionError('strict stress must pass for exact candidate binaries before performance')
        metadata=root/'performance.meta';analyze(source,metadata,'clang','cholesky');references={}
        for n in perf_sizes:
            ip,ref,provenance=ensure_dense_reference(project,n);references[n]=(ip,ref);report['references'].append(provenance)
        jobs=[(f'dense-{n}',[n],3,'auto',perf_threads)for n in perf_sizes]+[('mixed-stream',[4096,10000,4096],2,'auto',stream_threads)]
        jobs.extend((f'dense-{n}-B{tile}',[n],3,tile,counts)for n,tile,counts in extra_geometry)
        for label,sizes,repeats,geometry,counts in jobs:
            folder=root/label;folder.mkdir(exist_ok=True)
            if len(sizes)==1:ip,ref=references[sizes[0]]
            else:
                ip=folder/'input.bin';ref=folder/'oracle.bin'
                for destination_file,column in((ip,0),(ref,1)):
                    with destination_file.open('wb')as stream:
                        stream.write(struct.pack('<I',len(sizes)))
                        for n in sizes:
                            with references[n][column].open('rb')as src:src.read(4);shutil.copyfileobj(src,stream)
                report['stream_provenance']={'sizes':sizes,'bytes':ref.stat().st_size,'input_sha256':sha256(ip),'oracle_sha256':sha256(ref),'construction':'verified original-C payload concatenation, changed M only'}
            configs=[(t,v)for t in counts for v in binaries]
            for repeat in range(repeats):
                order=configs[repeat%len(configs):]+configs[:repeat%len(configs)]
                for count,variant in order:
                    if sizes==[10000]and count==1 and repeat>=large_single_repeats:continue
                    out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],metadata,ip,out,engine='tiled',tile_size=geometry,threads=count,probe_resources=True,structure='dense');report['performance'].append({'workload':label,'sizes':sizes,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                    print(f'PASS {label} {variant} t{count} r{repeat}: compute {metrics["compute_ms"]:.3f}, graph {metrics["graph_ms"]:.3f}, kernel {metrics["kernel_ms"]:.3f}, export {metrics.get("export_ms",0):.3f}ms',flush=True)
            for count,variant in configs:
                group=[r for r in report['performance']if(r['workload'],r['threads'],r['variant'])==(label,count,variant)]
                result={'workload':label,'sizes':sizes,'variant':variant,'threads':count,'repeats':len(group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'max_process_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in group),'max_process_peak_commit_bytes':max(r['process_peak_commit_bytes']for r in group),'host_available_ram_min_bytes':min(r['host_available_ram_min_bytes']for r in group),'sha256':group[-1]['sha256']}
                for field in('compute_ms','wall_ms','graph_ms','kernel_ms','export_ms','input_read_ms','output_write_ms'):result[f'median_{field}']=statistics.median(r.get(field,0)for r in group)
                for field in('process_cpu_time_ms','host_busy_percent_during_process','host_other_cpu_ms_estimate','resident_task_states_peak'):
                    values=[r[field]for r in group if r.get(field)is not None];result[f'median_{field}']=statistics.median(values)if values else None
                result['max_task_metadata_bytes_peak']=max(r['task_metadata_bytes_peak']for r in group)
                report['summary'].append(result)
            save();(folder/'runtime.bin').unlink(missing_ok=True)
            if len(sizes)>1:ip.unlink();ref.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'phase':args.phase,'stress':len(report['stress']),'performance':len(report['performance']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}),flush=True)

if __name__=='__main__':main()
