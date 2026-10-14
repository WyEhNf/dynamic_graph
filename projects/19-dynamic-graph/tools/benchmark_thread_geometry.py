"""Investigate whether coarse DAG geometry improves 8/16-worker scaling."""
from pathlib import Path
import json,statistics,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import run_runtime,exact_compare
from research_reference import ensure_dense_reference,sha256

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/thread-geometry-milestone';root.mkdir(exist_ok=True);runtime=project/'artifacts/baseline-shape-runtime.exe';metadata=root/'program.meta';analyze(project/'fixtures/official_naive_transcribed.c',metadata,'clang','cholesky');started=time.perf_counter()
    report={'passed':False,'runtime_sha256':sha256(runtime),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'performance':[],'summary':[],'references':[],'contract':'same binary and original-C whole-file truth; only worker count/physical tile geometry varies','hypothesis':'larger tiles reduce central queue retirements O((N/B)^3), potentially benefiting more workers; larger serial P/T tasks and cache footprint can offset this','concurrency_note':'shared host; no affinity/frequency/temperature isolation; rotate configurations; native compute excludes20ms Win32 resource launcher sampling'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'thread-geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();configs=[(4,64)]+[(count,b)for count in(8,16)for b in(64,96,128,192)]
    for n in (2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);report['references'].append(provenance);folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        for repeat in range(3):
            order=configs[repeat%len(configs):]+configs[:repeat%len(configs)]
            for count,b in order:
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metadata,ip,out,threads=count,engine='tiled',tile_size=b,probe_resources=True);report['performance'].append({'n':n,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
                if n==10000:print(f'PASS dense10000 t{count} B{b} r{repeat}: {metrics["compute_ms"]:.3f}ms',flush=True)
        for count,b in configs:
            group=[r for r in report['performance']if r['n']==n and r['threads']==count and r['tile_size']==b]
            report['summary'].append({'n':n,'threads':count,'tile_size':b,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'tasks':group[-1]['task_count'],'task_metadata_bytes':group[-1]['task_metadata_bytes_peak'],'max_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink();print(f'PASS worker/geometry milestone N={n}',flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'comparisons':len(report['performance']),'report':str(root/'thread-geometry-report.json')}),flush=True)

if __name__=='__main__':main()
