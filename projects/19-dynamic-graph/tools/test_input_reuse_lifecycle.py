"""Original-C owned-lifetime, upper +0, backend fallback and failure tests."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,struct,subprocess,time
from analyze_source import analyze
from evaluate_source import compile_oracle,run_runtime,exact_compare
from benchmark_extended import stress_input
from research_reference import sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('input-reuse','input-reuse-auto'),default='input-reuse');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/f'artifacts/{args.variant}-lifecycle-extra';root.mkdir(exist_ok=True)
    binary=project/f'artifacts/baseline-{args.variant}-runtime.exe';source=project/'fixtures/official_naive_transcribed.c';started=time.perf_counter()
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':sha256(binary),'tool_sha256':sha256(Path(__file__)),'cases':[],'rejection':[],'contract':'M4 mixed sizes; arbitrary finite original A upper discarded for Cholesky output +0; upper data preserved when generic VM reads it; dense-only reuse v1; auto failed classification may also reuse v2; failed matrix after completed earlier matrix never publishes partial output'}
    destination=root/'test-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(report,indent=2)+'\n')
    fused=root/'explicit-fma.c';fused.write_text(source.read_text().replace('return x * y + z;','return fma(x,y,z);'))
    sources=[('left',project/'fixtures/cholesky_reference.c','cholesky_reference'),('right',source,'cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('fma',fused,'cholesky')]
    generic=root/'generic.c';generic.write_text('int transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=a[i]/2.0;return 0;}')
    sources.append(('generic',generic,'transform'))
    sizes=[3,17,33,129];base=root/'base.bin';stress_input(base,sizes,'near-rank-one');payload=bytearray(base.read_bytes());offset=4
    for n in sizes:
        offset+=4
        for i in range(n):
            for j in range(i+1,n):struct.pack_into('<d',payload,offset+8*(i*n+j),-0.0 if(i+j)%3==0 else(-19.75 if(i+j)%3==1 else 2.0**450))
        offset+=8*n*n
    ip=root/'mixed.bin';ip.write_bytes(payload)
    for label,path,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);meta=folder/'program.meta';analyze(path,meta,'clang',function);oracle=compile_oracle(path,function,folder,'gcc',label=='blocked');ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        for engine,structure in(('tiled','dense'),('tiled','auto'),('auto','dense'),('stage','dense'),('vm','dense')):
            for threads in(1,4):
                for simd in('auto','portable'):
                    out=folder/'runtime.bin';m=run_runtime(binary,meta,ip,out,engine=engine,structure=structure,threads=threads,simd=simd,block=7)
                    expected=0 if label=='generic' or (structure!='dense'and args.variant!='input-reuse-auto') or engine in('stage','vm') else(len(sizes)if engine=='tiled' else sum(n>=128 for n in sizes))
                    if m['input_buffers_reused']!=expected:raise AssertionError(('incorrect reuse dispatch',label,engine,structure,m))
                    report['cases'].append({'source':label,'source_sha256':sha256(path),**m,**exact_compare(ref,out)})
        print('PASS owned M/backend/upper '+label,flush=True);save()
    # The first valid matrix is written only into the temporary file; a later
    # bad pivot/nonfinite/truncated payload must discard the entire M result.
    good=bytes(payload[4:4+4+8*sizes[0]*sizes[0]]);n=257;bad=root/'bad-pivot.bin';stress_input(bad,[n],'near-rank-one');invalid=bytearray(bad.read_bytes()[4:]);struct.pack_into('<d',invalid,4+8*(n*n-1),-1.0)
    for kind,tail in(('late-pivot',bytes(invalid)),('late-nan',good[:4]+struct.pack('<d',float('nan'))+good[12:]),('late-truncated',good[:-1])):
        failed=root/'failure.bin';failed.write_bytes(struct.pack('<I',2)+good+tail)
        for threads in(1,4,16):
            for queue in('heap','bucket'):
                out=root/'rejected.bin';out.unlink(missing_ok=True);partial=Path(str(out)+'.partial');partial.unlink(missing_ok=True)
                command=[str(binary),'--metadata',str(root/'right/program.meta'),'--input',str(failed),'--output',str(out),'--engine','tiled','--structure','dense','--tile-size','64','--threads',str(threads),'--scheduler','parallel','--ready-queue',queue]
                cp=subprocess.run(command,capture_output=True,text=True,timeout=30)
                if cp.returncode==0 or out.exists()or partial.exists():raise AssertionError(('M failure published output',kind,cp.stderr))
                required={'late-pivot':'not positive definite','late-nan':'non-finite matrix element','late-truncated':'truncated'}[kind]
                if required not in cp.stderr:raise AssertionError(('unexpected failure',kind,cp.stderr))
                report['rejection'].append({'case':kind,'threads':threads,'queue':queue,'error':cp.stderr.strip(),'output_absent':True,'partial_absent':True});save()
    report['passed']=True;save();print(json.dumps({'passed':True,'cases':len(report['cases']),'rejection':len(report['rejection']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}))
if __name__=='__main__':main()
