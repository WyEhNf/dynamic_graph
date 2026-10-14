"""Milestone batch for exact band specialization and other dense SPD families."""
from pathlib import Path
import argparse,hashlib,json,statistics,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from structured_workloads import make_workload
from research_reference import ensure_dense_reference,sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=Path('build-banded/cholesky_runtime.exe'));parser.add_argument('--skip-maximum',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/structured-milestone';root.mkdir(exist_ok=True);runtime=args.runtime.resolve();baseline=project/'artifacts/baseline-hybrid-runtime.exe';started=time.perf_counter()
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':{'banded':sha256(runtime),'dense_hybrid':sha256(baseline)},'correctness':[],'performance':[],'references':[],'contract':'every comparison is whole-file bytes against separately compiled original C; banded and dense families labelled separately; no tolerance substitution','concurrency_note':'other projects may execute concurrently; four workers maximum for this runtime; C oracle one core'}
    def save():report['elapsed_seconds']=time.perf_counter()-started;(root/'structured-report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();fma=root/'explicit-fma.c';fma.write_text((project/'fixtures/official_naive_transcribed.c').read_text().replace('return x * y + z;','return fma(x,y,z);'))
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference',False),('page',project/'fixtures/official_naive_transcribed.c','cholesky',False),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked',True),('fma',fma,'cholesky',False)];metas={};oracles={}
    for label,source,function,blocked in sources:
        folder=root/label;folder.mkdir(exist_ok=True);metas[label]=folder/'program.meta';analyze(source,metas[label],'clang',function);oracles[label]=compile_oracle(source,function,folder/'oracle-build','gcc',blocked)
    configs=[dict(engine='auto',threads=4),dict(engine='stage',threads=1),dict(engine='tiled',tile_size=7,threads=4),dict(engine='tiled',tile_size=32,threads=4,structure='dense',simd='portable'),dict(engine='tiled',tile_size=64,threads=4,structure='dense',ready_queue='bucket'),dict(engine='tiled',tile_size=32,threads=4,band_limit=0)]
    for width,sizes in ((1,[3,7,17,33,65,129,193]),(7,[3,7,17,33,65,129,193]),(31,[65,129,193]),(127,[257,513,517]),(128,[513,517]),(129,[517])):
        for mode in (('normal','subnormal','large','tiny')if width<=31 else('normal',)):
            folder=root/f'band-{width}-{mode}';folder.mkdir(exist_ok=True);ip=folder/'input.bin';make_workload(ip,sizes,'band',width,mode)
            for label,_,_,_ in sources:
                ref=folder/f'{label}-oracle.bin';subprocess.run([str(oracles[label]),str(ip),str(ref),'7'],check=True)
                for index,config in enumerate(configs):
                    out=folder/'runtime.bin';metrics=run_runtime(runtime,metas[label],ip,out,block=7,**config);report['correctness'].append({'source':label,'family':'band','width':width,'mode':mode,'sizes':sizes,'config':index,**metrics,**exact_compare(ref,out)})
                    if index<3 and width*4<sizes[-1] and width<=128 and metrics['selected_engine']!='banded':raise AssertionError('eligible final matrix was not specialized')
                    if metrics['selected_engine']=='banded' and metrics['worker_threads']!=1:raise AssertionError('structured serial path claims parallel workers')
                    save()
                ref.unlink()
            (folder/'runtime.bin').unlink(missing_ok=True);ip.unlink();print(f'PASS exact band w={width} {mode}, four original C sources and six dispatch modes',flush=True)
    # Generic VM must remain a real source execution, even on eligible data.
    small=root/'small-vm';small.mkdir(exist_ok=True);ip=small/'input.bin';make_workload(ip,[3,7,17,33],'band',1,'tiny')
    for label,_,_,_ in sources:
        ref=small/f'{label}.bin';out=small/'runtime.bin';subprocess.run([str(oracles[label]),str(ip),str(ref),'7'],check=True);metrics=run_runtime(runtime,metas[label],ip,out,block=7,engine='vm');report['correctness'].append({'source':label,'family':'band','mode':'tiny','width':1,'sizes':[3,7,17,33],**metrics,**exact_compare(ref,out)});save()
    for family in ('toeplitz','low-rank'):
        folder=root/family;folder.mkdir(exist_ok=True);ip=folder/'input.bin';make_workload(ip,[257,1025,2047,2048,2049],family)
        for label,_,_,_ in sources:
            ref=folder/f'{label}.bin';subprocess.run([str(oracles[label]),str(ip),str(ref),'7'],check=True)
            for threads in (1,4):
                out=folder/'runtime.bin';metrics=run_runtime(runtime,metas[label],ip,out,block=7,engine='tiled',tile_size='auto',threads=threads);report['correctness'].append({'source':label,'family':family,'sizes':[257,1025,2047,2048,2049],**metrics,**exact_compare(ref,out)});save()
            ref.unlink()
        ip.unlink();(folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS dense family {family}, including adaptive row-group 2047/2048/2049',flush=True)
    for n in (512,1024,2048,4096):
        ip,ref,provenance=ensure_dense_reference(project,n);report['references'].append(provenance);folder=root/f'dense-{n}';folder.mkdir(exist_ok=True)
        for repeat in range(5):
            order=[('dense_hybrid',baseline),('banded',runtime)];order=order[repeat%2:]+order[:repeat%2]
            for variant,binary in order:
                out=folder/'runtime.bin';metrics=run_runtime(binary,metas['page'],ip,out,engine='tiled',tile_size=64,threads=4);report['performance'].append({'family':'general-dense','n':n,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save()
        (folder/'runtime.bin').unlink(missing_ok=True);print(f'PASS dense N={n}, no-structure overhead A/B batch',flush=True)
    if not args.skip_maximum:
        folder=project/'artifacts/band-maximum-reference';provenance=json.loads((folder/'reference-report.json').read_text());ip=folder/'input.bin';ref=folder/'oracle.bin'
        if not provenance['passed'] or provenance['input_sha256']!=sha256(ip) or provenance['oracle_sha256']!=sha256(ref):raise AssertionError('maximum original-source C reference incomplete or changed')
        report['references'].append(provenance);out=root/'maximum-runtime.bin'
        for repeat in range(3):
            order=[('dense_hybrid',baseline),('banded',runtime)];order=order[repeat%2:]+order[:repeat%2]
            for variant,binary in order:
                metrics=run_runtime(binary,metas['page'],ip,out,engine='tiled',tile_size=64,threads=4);report['performance'].append({'family':'band','width':7,'n':10000,'variant':variant,'repeat':repeat,**metrics,**exact_compare(ref,out)});save();print(f'PASS band N10000 {variant} r{repeat}: compute {metrics["compute_ms"]:.3f} ms, wall {metrics["wall_ms"]:.3f} ms',flush=True)
        out.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'correctness':len(report['correctness']),'performance':len(report['performance']),'report':str(root/'structured-report.json')}),flush=True)

if __name__=='__main__':main()
