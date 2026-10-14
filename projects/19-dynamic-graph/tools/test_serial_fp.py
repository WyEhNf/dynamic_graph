"""Independent original-C stress for closed single-worker traversal."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import sha256

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/serial-walk-fp';root.mkdir(exist_ok=True)
    binary=project/'artifacts/baseline-serial-walk-runtime.exe';source=project/'fixtures/official_naive_transcribed.c'
    fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'))
    sources=[('left',project/'fixtures/cholesky_reference.c','cholesky_reference'),('right',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('fma',fused,'cholesky')]
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':sha256(binary),'tool_sha256':sha256(Path(__file__)),'cases':[],'contract':'all single-worker auto/portable, original C whole bytes; FP extremes/signed zero/tails/B1/B>N; assert actual closed traversal with zero resident states and ready queue'}
    destination=root/'test-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for label,path,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);meta=folder/'program.meta';analyze(path,meta,'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked')
        for mode in('subnormal','large','near-rank-one','signed-zero'):
            ip=folder/'input.bin';ref=folder/'oracle.bin';stress_input(ip,[3,7,17,31,33,65,127,129,193,257],mode);subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            for b in(1,7,31,64,96,128,1024):
                for simd in('auto','portable'):
                    out=folder/'runtime.bin';m=run_runtime(binary,meta,ip,out,engine='tiled',tile_size=b,threads=1,block=7,simd=simd,structure='dense')
                    if m['resident_task_states_peak']!=0 or m['ready_peak']!=0 or m['ready_queue']!='closed_serial':raise AssertionError(('serial dispatch not active',m))
                    report['cases'].append({'source':label,'source_sha256':sha256(path),'mode':mode,**m,**exact_compare(ref,out)});save()
        print('PASS serial FP '+label,flush=True)
    report['passed']=True;save();print(json.dumps({'passed':True,'cases':len(report['cases']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}))

if __name__=='__main__':main()
