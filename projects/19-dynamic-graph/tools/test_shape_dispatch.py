"""One milestone for thread-aware B and AVX row boundaries against original C."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from research_reference import ensure_dense_reference,sha256

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/shape-final-milestone';root.mkdir(exist_ok=True);runtime=project/'build-shape-final/cholesky_runtime.exe';started=time.perf_counter();sizes=[127,128,1024,1025,1536,1537,2047,2048,2049]
    report={'passed':False,'runtime_sha256':sha256(runtime),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'runs':[],'policy_checks':[],'sizes':sizes,'references':[],'contract':'all complete output bytes match independent original C, including physical geometry and vector row boundaries'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'shape-final-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();ip=root/'input.bin';references={}
    with ip.open('wb')as stream:
        stream.write(struct.pack('<I',len(sizes)))
        for n in sizes:
            source,reference,provenance=ensure_dense_reference(project,n);references[n]=(source,reference);report['references'].append(provenance)
            with source.open('rb')as original:original.read(4);shutil.copyfileobj(original,stream)
    fused=root/'explicit-fma.c';fused.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'))
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('fma',fused,'cholesky')]
    metas={}
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metadata=folder/'program.meta';metas[label]=metadata;analyze(source,metadata,'clang',function);oracle=compile_oracle(source,function,folder/'oracle-build','gcc',label=='blocked');ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        for engine in ('auto','tiled'):
            for threads in (1,4):
                for simd in ('auto','portable'):
                    out=folder/'runtime.bin';metrics=run_runtime(runtime,metadata,ip,out,threads=threads,simd=simd,engine=engine,tile_size='auto',block=7);report['runs'].append({'source':label,**metrics,**exact_compare(ref,out)})
                    if metrics['tile_size_min']!=32 or metrics['tile_size_max']!=64:raise AssertionError('mixed shape B32/B64 metrics incorrect')
                    if simd=='auto' and metrics['vector_rows']!=4:raise AssertionError('last matrix did not use four rows')
                    save()
        ref.unlink();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS shape boundaries {label}: 9 shapes, all dispatch/ISA/thread modes',flush=True)
    for n in (1025,1536,1537):
        inp,ref=references[n]
        for threads in (1,4):
            out=root/'policy.bin';metrics=run_runtime(runtime,metas['page'],inp,out,threads=threads,engine='tiled',tile_size='auto');expected=32 if n<=(1536 if threads==1 else 1024)else 64
            if metrics['effective_tile_size']!=expected:raise AssertionError('thread-aware size policy mismatch')
            report['policy_checks'].append({'n':n,'expected_tile':expected,**metrics,**exact_compare(ref,out)});save()
    (root/'policy.bin').unlink();ip.unlink();report['passed']=True;save();print(json.dumps({'passed':True,'comparisons':len(report['runs'])+len(report['policy_checks']),'report':str(root/'shape-final-report.json')}),flush=True)

if __name__=='__main__':main()
