"""Owned row profile versus auto recycling hybrid profile: whole profiles, strict C, structural fallback and resources."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,statistics,struct,subprocess,sys,time
from benchmark_column_workspace import main as common_main
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from structured_workloads import make_workload
from research_reference import ensure_dense_reference,sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('stress','structure-stress','performance'),default='stress');parser.add_argument('--resume',type=Path);args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/input-reuse-auto-milestone';root.mkdir(exist_ok=True)
    binaries={v:project/f'artifacts/baseline-{v}-runtime.exe'for v in('owned-row-control','input-reuse-auto')};hashes={v:sha256(p)for v,p in binaries.items()}
    source=project/'fixtures/official_naive_transcribed.c';destination=root/('auto-performance-report.json'if args.phase=='performance'else'auto-stress-report.json');started=time.perf_counter()
    report={'passed':False,'phase':args.phase,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':hashes,'source_sha256':sha256(source),'tool_sha256':sha256(Path(__file__)),'cases':[],'rejection':[],'performance':[],'summary':[],'references':[],'contract':'same current sources and owned API; whole profiles: row output+packed vs hybrid packed with input reused after failed structure classification; auto band retains full conventional L; both vector scans and FP order unchanged; not isolated kernel speed claim; all bytes original C; input destruction and upper clearing/export inside compute','concurrency_note':'shared CPU/GPU, no affinity/frequency/temperature isolation; whole process CPU and RAM retained; last input_validation/scan names with accumulated times'}
    prior_elapsed=0
    if args.resume:
        previous=json.loads(args.resume.read_text())
        if args.phase!='performance' or previous['passed']or previous['binary_sha256']!=hashes or previous['source_sha256']!=sha256(source):raise AssertionError('resume requires matching incomplete performance evidence')
        if any(not x['byte_identical']for x in previous['performance']):raise AssertionError('resume cannot retain failed comparisons')
        report['performance']=previous['performance'];prior_elapsed=previous['elapsed_seconds']
        report['resume']={'checkpoint_sha256':sha256(args.resume),'retained_successful_comparisons':len(report['performance']),'prior_elapsed_seconds':prior_elapsed,'prior_tool_sha256':previous['tool_sha256'],'reason':'report Path was shadowed by M concatenation variable; stop, preserve original-C-verified ordinary cases, fix destination, regenerate verified M payloads; elapsed is sum of active segments, excludes interruption gap'}
        print('RESUME retained '+str(len(report['performance']))+' original-C-verified performance cases',flush=True)
    def save():
        report['elapsed_seconds']=prior_elapsed+time.perf_counter()-started;t=destination.with_suffix('.json.partial');t.write_text(json.dumps(report,indent=2)+'\n')
        for attempt in range(10):
            try:t.replace(destination);break
            except PermissionError:
                if attempt==9:raise
                time.sleep(.02)
    save()
    if args.phase!='performance':
        if args.phase=='stress':common_main(milestone='input-reuse-auto',variants=tuple(binaries),stress_variants=('input-reuse-auto',),stress_queues=('heap','bucket'))
        common=json.loads((root/'input-reuse-auto-stress-report.json').read_text())
        if not common['passed']or common['binary_sha256']!=hashes:raise AssertionError('strict dense heap/bucket must pass for exact binaries')
        unit=project/'artifacts/vector-scan-tests.exe';completed=subprocess.run([str(unit)],check=True,capture_output=True,text=True)
        report['unit']={'binary_sha256':sha256(unit),'source_sha256':sha256(project/'tests/vector_scan_tests.cpp'),'stdout':completed.stdout.strip()}
        fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'))
        sources=[('left',project/'fixtures/cholesky_reference.c','cholesky_reference'),('right',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('fma',fused,'cholesky')]
        data=[(w,[3,7,17,31,33,65,127,129,193,257]if w<=7 else[129,193],mode)for w in(0,1,7,31)for mode in('normal','subnormal','large','tiny')]
        data.extend((w,[513,517]if w<=128 else[517],'normal')for w in(127,128,129))
        for label,path,function in sources:
            folder=root/label;folder.mkdir(exist_ok=True);meta=folder/'program.meta';analyze(path,meta,'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked')
            for width,sizes,mode in data:
                ip=folder/'input.bin';ref=folder/'oracle.bin';make_workload(ip,sizes,'band',width,mode);subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                for simd in('auto','portable'):
                    controls={}
                    for variant,binary in binaries.items():
                        out=folder/'runtime.bin';m=run_runtime(binary,meta,ip,out,engine='tiled',tile_size=31,threads=4,block=7,simd=simd)
                        if controls and(m['selected_engine'],m['structure_bandwidth'])!=(controls['selected_engine'],controls['structure_bandwidth']):raise AssertionError('structure classification differs')
                        controls=m
                        # selected_engine names only the last matrix in M; earlier
                        # smaller shapes may legitimately fail the band limit.
                        if variant=='owned-row-control'and m['input_buffers_reused']!=0:raise AssertionError('row control incorrectly recycled')
                        if not 0<=m['input_buffers_reused']<=m['matrices']:raise AssertionError('invalid aggregate reuse count')
                        if width==0 and m['input_buffers_reused']!=0:raise AssertionError('all diagonal shapes incorrectly recycled')
                        report['cases'].append({'source':label,'source_sha256':sha256(path),'width':width,'mode':mode,'variant':variant,**m,**exact_compare(ref,out)})
            for family in('toeplitz','low-rank'):
                ip=folder/'input.bin';ref=folder/'oracle.bin';make_workload(ip,[257,1025],family);subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                for variant,binary in binaries.items():
                    for simd in('auto','portable'):
                        out=folder/'runtime.bin';m=run_runtime(binary,meta,ip,out,engine='tiled',threads=4,block=7,simd=simd);report['cases'].append({'source':label,'source_sha256':sha256(path),'family':family,'variant':variant,**m,**exact_compare(ref,out)})
            save();print('PASS scans original C '+label,flush=True)
        # Non-finite probes are local rejected-input tests, not oracle datasets.
        meta=root/'right/program.meta';ip=root/'nonfinite.bin';make_workload(ip,[17],'band',1);base=ip.read_bytes()
        for bits in(0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000001,0xfff8000000000001,0x7ff0000000000001,0xfff0000000000001):
            for position in(0,1,3,4,7,8,15,16,31,32,287,288):
                payload=bytearray(base);struct.pack_into('<Q',payload,8+position*8,bits);ip.write_bytes(payload)
                for variant,binary in binaries.items():
                    for simd in('auto','portable'):
                        out=root/'rejected.bin';out.unlink(missing_ok=True);partial=out.with_name(out.name+'.partial');partial.unlink(missing_ok=True)
                        cp=subprocess.run([str(binary),'--metadata',str(meta),'--input',str(ip),'--output',str(out),'--engine','tiled','--threads','4','--scheduler','parallel','--simd',simd],capture_output=True,text=True,timeout=20)
                        if cp.returncode==0 or'non-finite matrix element'not in cp.stderr or out.exists()or partial.exists():raise AssertionError(('non-finite rejection failed',variant,simd,position,cp.stderr))
                        report['rejection'].append({'variant':variant,'simd':simd,'bits':hex(bits),'position':position,'error':cp.stderr.strip(),'output_absent':True,'partial_absent':True})
        save()
    else:
        for evidence_file in(root/'input-reuse-auto-stress-report.json',root/'auto-stress-report.json'):
            e=json.loads(evidence_file.read_text())
            if not e['passed']or e['binary_sha256']!=hashes:raise AssertionError('all strict source, bit, guard and rejected-input tests must pass for exact binaries')
        meta=root/'performance.meta';analyze(source,meta,'clang','cholesky');refs={}
        for n in(2048,4096,10000):
            ip,ref,proof=ensure_dense_reference(project,n);refs[n]=(ip,ref);report['references'].append(proof)
        band=project/'artifacts/band-maximum-reference';proof=json.loads((band/'reference-report.json').read_text());ip=band/'input.bin';ref=band/'oracle.bin'
        if not proof['passed']or proof['source_sha256']!=sha256(source)or proof['input_sha256']!=sha256(ip)or proof['oracle_sha256']!=sha256(ref):raise AssertionError('retained original-C maximum band reference missing/changed: regenerate with tools/prepare_banded_maximum.py')
        report['references'].append(proof)
        jobs=[('ordinary-dense-'+str(n),*refs[n],t,'auto')for n in refs for t in(1,4,16)]+[('band-10000-w7',ip,ref,4,simd)for simd in('auto','portable')]
        stream_files=(root/'stream-input.bin',root/'stream-oracle.bin')
        for stream_destination,column in zip(stream_files,(0,1)):
            with stream_destination.open('wb')as output:
                output.write(struct.pack('<I',3))
                for size in(4096,10000,4096):
                    with refs[size][column].open('rb')as original:original.read(4);shutil.copyfileobj(original,output)
        report['stream_provenance']={'sizes':[4096,10000,4096],'input_sha256':sha256(stream_files[0]),'oracle_sha256':sha256(stream_files[1]),'bytes':stream_files[1].stat().st_size,'construction':'verified original C payloads concatenated; changed M only'}
        if args.resume and report['stream_provenance']!=previous['stream_provenance']:raise AssertionError('reconstructed M oracle differs from prior independently verified C manifest')
        jobs.extend(('mixed-stream',*stream_files,t,'auto')for t in(4,16))
        for label,ip,ref,threads,simd in jobs:
            out=root/'performance-output.bin'
            for repeat in range(2 if label=="mixed-stream" else 3):
                order=list(binaries.items());order=order[repeat%2:]+order[:repeat%2]
                for variant,binary in order:
                    if any((x['workload'],x['variant'],x['repeat'],x['threads'],x['simd'])==(label,variant,repeat,threads,simd)for x in report['performance']):continue
                    m=run_runtime(binary,meta,ip,out,engine='tiled',threads=threads,simd=simd,probe_resources=True)
                    expected=0 if label.startswith('band-')or variant=='owned-row-control'else(3 if label=='mixed-stream'else 1)
                    if m['input_buffers_reused']!=expected:raise AssertionError(('owned auto dispatch missing',label,variant,m))
                    report['performance'].append({'workload':label,'variant':variant,'simd':simd,'repeat':repeat,**m,**exact_compare(ref,out)});save();print(f'PASS {label} {variant} {simd} t{threads} r{repeat}: compute {m["compute_ms"]:.3f} validate {m["input_validation_ms"]:.3f} structure {m["structure_scan_ms"]:.3f}',flush=True)
            out.unlink(missing_ok=True)
            for variant in binaries:
                group=[x for x in report['performance']if(x['workload'],x['variant'],x['threads'],x['simd'])==(label,variant,threads,simd)]
                a={'workload':label,'variant':variant,'threads':threads,'simd':simd,'repeats':len(group),'min_compute_ms':min(x['compute_ms']for x in group),'max_compute_ms':max(x['compute_ms']for x in group),'peak_working_set_bytes':max(x['process_peak_working_set_bytes']for x in group),'host_available_ram_min_bytes':min(x['host_available_ram_min_bytes']for x in group)}
                for field in('compute_ms','wall_ms','input_validation_ms','structure_scan_ms','graph_ms','kernel_ms','input_read_ms','output_write_ms','process_cpu_time_ms','host_busy_percent_during_process','host_other_cpu_ms_estimate'):a['median_'+field]=statistics.median(x[field]for x in group)
                report['summary'].append(a)
            save()
        for temporary in stream_files:temporary.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'phase':args.phase,'cases':len(report['cases']),'rejection':len(report['rejection']),'performance':len(report['performance']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}),flush=True)

if __name__=='__main__':main()
