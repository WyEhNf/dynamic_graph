"""Milestone: CPU-detected ordered AVX2, independent source bytes and IO costs."""
from pathlib import Path
import json,hashlib,statistics,time,subprocess
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import make_input,run_runtime,exact_compare,compile_oracle
from benchmark_extended import stress_input
from research_reference import ensure_dense_reference

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/simd-milestone';root.mkdir(exist_ok=True)
    runtime=project/'artifacts/baseline-simd-runtime.exe';started=time.perf_counter()
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'stress':[],'performance':[],'summary':[],'contract':'original-source independently compiled C; strict entire files; no implicit FMA; AVX lanes do not change each cell reduction order','concurrency_note':'other projects may execute concurrently; repeated files generally warm disk cache'}
    def save():
        report['elapsed_seconds']=time.perf_counter()-started;(root/'simd-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'));sources.append(('fma',fused,'cholesky'))
    metas={};oracles={}
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function,compact_bytecode=False);oracles[label]=compile_oracle(source,function,folder,'gcc',label=='blocked')
        for mode in ('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';stress_input(ip,[3,7,17,31,33,65,127,129],mode);ref=folder/'oracle.bin';subprocess.run([str(oracles[label]),str(ip),str(ref),'7'],check=True)
            for simd in ('portable','auto'):
                for b in (7,16,32,64):
                    out=folder/'runtime.bin';metrics=run_runtime(runtime,metas[label],ip,out,engine='tiled',tile_size=b,threads=4,block=7,simd=simd)
                    report['stress'].append({'source':label,'mode':mode,**metrics,**exact_compare(ref,out)})
            save()
        print(f'PASS SIMD stress {label}: portable/AVX2 and difficult FP source oracle',flush=True)
    for n in (2048,4096,10000):
        folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        ip,ref,provenance=ensure_dense_reference(project,n);report.setdefault('references',[]).append(provenance);oracle_ms=provenance.get('oracle_wall_ms')
        configs=[(simd,count,b)for count in(1,4)for b in(32,64,96,128)for simd in('portable','auto')]
        for repeat in range(1 if n==10000 else 3):
            for simd,count,b in configs[repeat%len(configs):]+configs[:repeat%len(configs)]:
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metas['page'],ip,out,engine='tiled',tile_size=b,threads=count,simd=simd)
                report['performance'].append({'n':n,'repeat':repeat,'oracle_wall_ms':oracle_ms,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS general dense N10000 {simd} B{b} t{count}: compute {metrics["compute_ms"]:.3f}ms, read/write {metrics["input_read_ms"]:.3f}/{metrics["output_write_ms"]:.3f}ms',flush=True)
        for simd,count,b in configs:
            group=[r for r in report['performance']if(r['n'],r['simd_requested'],r['threads'],r['tile_size'])==(n,simd,count,b)]
            report['summary'].append({'n':n,'simd':simd,'threads':count,'tile_size':b,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_read_ms':statistics.median(r['input_read_ms']for r in group),'median_write_ms':statistics.median(r['output_write_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'vector_kernel':group[-1]['vector_kernel'],'tasks':group[-1]['task_count'],'packed_bytes':group[-1]['packed_bytes_peak'],'task_metadata_bytes':group[-1]['task_metadata_bytes_peak'],'sha256':group[-1]['sha256']})
        save();print(f'PASS SIMD dense n={n}: all configurations, full original-source C bytes',flush=True)
        out=folder/'runtime.bin';out.unlink(missing_ok=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'stress':len(report['stress']),'performance':len(report['performance']),'report':str(root/'simd-report.json')}),flush=True)

if __name__=='__main__':main()
