"""NaN factor poison proof regression, then shared-geometry lightweight A/B/C."""
from pathlib import Path
import argparse,json,shutil,statistics,struct,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference,sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('stress','performance'),default='stress');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/lazy-pack-milestone';root.mkdir(exist_ok=True)
    binaries={label:project/f'artifacts/baseline-{label}-runtime.exe'for label in('thread-policy','unlock-notify','poison-pack','lazy-pack')}
    hashes={k:sha256(v)for k,v in binaries.items()};source=project/'fixtures/official_naive_transcribed.c';started=time.perf_counter()
    report={'passed':False,'phase':args.phase,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha256(source),'benchmark_tool_sha256':sha256(Path(__file__)),'binary_sha256':hashes,'stress':[],'performance':[],'summary':[],'references':[],'contract':'original-C complete bytes; POISON initializes every packed slot to NaN, NONE omits redundant packed fill, L always initializes +0; identical FP operations and task geometry','concurrency_note':'shared host; kernel first-touch/page-fault cost remains in compute; graph reduction alone is not a speedup; rotated three configurations and threads, no affinity/frequency/temperature isolation'}
    destination=root/f'lazy-pack-{args.phase}-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(report,indent=2)+'\n')
    save()
    if args.phase=='stress':
        sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
        fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
        for label,path,function in sources:
            folder=root/label;folder.mkdir(exist_ok=True);meta=folder/'program.meta';analyze(path,meta,'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked')
            for mode in('subnormal','large','near-rank-one','signed-zero'):
                ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129,193,257],mode);ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                for variant in('poison-pack','lazy-pack'):
                    for b,simd in[(b,'auto')for b in(7,32,64,96,1024)]+[(96,'portable')]:
                        out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],meta,ip,out,engine='tiled',tile_size=b,threads=4,block=7,simd=simd,structure='dense');report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':mode,'variant':variant,**metrics,**exact_compare(ref,out)})
                save()
            ip=folder/'tiny-tile.bin';stress_input(ip,[3,7,17],'signed-zero');ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for variant in('poison-pack','lazy-pack'):
                for count in(1,4):
                    out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],meta,ip,out,engine='tiled',tile_size=1,threads=count,block=7,simd='auto',structure='dense');report['stress'].append({'source':label,'source_sha256':sha256(path),'mode':'B1-small','variant':variant,**metrics,**exact_compare(ref,out)})
            save();print(f'PASS initialized-before-use {label}: NaN poison / no fill, ISA, tail, B>N and B1',flush=True)
    else:
        evidence=json.loads((root/'lazy-pack-stress-report.json').read_text())
        if not evidence['passed']or evidence['binary_sha256']!=hashes:raise AssertionError('stress must pass for exact candidate binaries before performance')
        metadata=root/'performance.meta';analyze(source,metadata,'clang','cholesky');references={}
        for n in(2048,4096,10000):
            ip,ref,provenance=ensure_dense_reference(project,n);references[n]=(ip,ref);report['references'].append(provenance)
        variants=('thread-policy','unlock-notify','lazy-pack')
        for label,sizes,repeats in[(f'dense-{n}',[n],3)for n in(2048,4096,10000)]+[('mixed-stream',[4096,10000,4096],2)]:
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
            configs=[(t,v)for t in(4,16)for v in variants]
            for repeat in range(repeats):
                order=configs[repeat%len(configs):]+configs[:repeat%len(configs)]
                for count,variant in order:
                    out=folder/'runtime.bin';metrics=run_runtime(binaries[variant],metadata,ip,out,engine='tiled',tile_size='auto',threads=count,probe_resources=True);report['performance'].append({'workload':label,'sizes':sizes,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                    print(f'PASS {label} {variant} t{count} r{repeat}: compute {metrics["compute_ms"]:.3f}, graph {metrics["graph_ms"]:.3f}, kernel {metrics["kernel_ms"]:.3f}ms',flush=True)
            for count,variant in configs:
                group=[r for r in report['performance']if(r['workload'],r['threads'],r['variant'])==(label,count,variant)]
                report['summary'].append({'workload':label,'sizes':sizes,'variant':variant,'threads':count,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'max_process_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in group),'max_process_peak_commit_bytes':max(r['process_peak_commit_bytes']for r in group),'host_available_ram_min_bytes':min(r['host_available_ram_min_bytes']for r in group),'sha256':group[-1]['sha256']})
            save();(folder/'runtime.bin').unlink(missing_ok=True)
            if len(sizes)>1:ip.unlink();ref.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'phase':args.phase,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(destination)}),flush=True)

if __name__=='__main__':main()
