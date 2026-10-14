"""Rotated worker scalability and real process/host memory; cached C truth."""
from pathlib import Path
import json,shutil,statistics,struct,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import run_runtime,exact_compare
from research_reference import ensure_dense_reference,sha256

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/scaling-milestone';root.mkdir(exist_ok=True);runtime=project/'artifacts/baseline-shape-runtime.exe';metadata=root/'program.meta';analyze(project/'fixtures/official_naive_transcribed.c',metadata,'clang','cholesky');started=time.perf_counter()
    report={'passed':False,'runtime_sha256':sha256(runtime),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'performance':[],'summary':[],'references':[],'contract':'complete original-C output bytes; no newly generated expensive oracle when valid references exist','memory_method':'Win32 GetProcessMemoryInfo PROCESS_MEMORY_COUNTERS_EX peak working set/peak commit; PrivateUsage sampled; GlobalMemoryStatusEx host available RAM sampled every20ms; host is shared, not attributable only to this process','concurrency_note':'4/8/16 workers requested for resource scalability study; independent project load remains possible; no CPU affinity/frequency/temperature isolation; monitored launcher adds sampling overhead outside native compute'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'scaling-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();references={}
    for n in (2048,4096,10000):
        ip,ref,provenance=ensure_dense_reference(project,n);references[n]=(ip,ref);report['references'].append(provenance)
    configs=[('dense-2048',[2048],5),('dense-4096',[4096],5),('dense-10000',[10000],3),('mixed-stream',[4096,10000,4096],3)]
    for label,sizes,repeats in configs:
        folder=root/label;folder.mkdir(exist_ok=True)
        if len(sizes)==1:ip,ref=references[sizes[0]]
        else:
            ip=folder/'input.bin';ref=folder/'oracle.bin'
            for destination,column in ((ip,0),(ref,1)):
                with destination.open('wb')as stream:
                    stream.write(struct.pack('<I',len(sizes)))
                    for n in sizes:
                        with references[n][column].open('rb')as source:source.read(4);shutil.copyfileobj(source,stream)
            report['stream_provenance']={'sizes':sizes,'input_sha256':sha256(ip),'oracle_sha256':sha256(ref),'bytes':ref.stat().st_size,'construction':'concatenated verified original-source single-matrix payloads, only M header changed'};save()
        for repeat in range(repeats):
            workers=[4,8,16];workers=workers[repeat%3:]+workers[:repeat%3]
            for count in workers:
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metadata,ip,out,engine='tiled',tile_size=64,threads=count,probe_resources=True);report['performance'].append({'workload':label,'sizes':sizes,'repeat':repeat,**metrics,**exact_compare(ref,out)});save();print(f'PASS {label} t{count} r{repeat}: compute {metrics["compute_ms"]:.3f}ms; peak WS {metrics["process_peak_working_set_bytes"]/2**20:.1f}MiB; host available min {metrics["host_available_ram_min_bytes"]/2**30:.2f}GiB',flush=True)
        for count in (4,8,16):
            group=[r for r in report['performance']if r['workload']==label and r['threads']==count]
            report['summary'].append({'workload':label,'sizes':sizes,'threads':count,'repeats':len(group),'median_compute_ms':statistics.median(r['compute_ms']for r in group),'min_compute_ms':min(r['compute_ms']for r in group),'max_compute_ms':max(r['compute_ms']for r in group),'median_wall_ms':statistics.median(r['wall_ms']for r in group),'median_graph_ms':statistics.median(r['graph_ms']for r in group),'median_kernel_ms':statistics.median(r['kernel_ms']for r in group),'max_process_peak_working_set_bytes':max(r['process_peak_working_set_bytes']for r in group),'max_process_peak_commit_bytes':max(r['process_peak_commit_bytes']for r in group),'host_available_ram_min_bytes':min(r['host_available_ram_min_bytes']for r in group),'sha256':group[-1]['sha256']})
        save();(folder/'runtime.bin').unlink(missing_ok=True)
        if len(sizes)>1:ip.unlink();ref.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'comparisons':len(report['performance']),'report':str(root/'scaling-report.json')}),flush=True)

if __name__=='__main__':main()
