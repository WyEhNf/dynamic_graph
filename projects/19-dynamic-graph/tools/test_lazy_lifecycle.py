"""Prove worker exceptions terminate and do not publish partial output."""
from pathlib import Path
from array import array
import argparse,json,struct,subprocess,time
from datetime import datetime,timezone
from analyze_source import analyze
from research_reference import sha256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('lazy-graph','lazy-prefix','serial-walk','input-reuse'),default='lazy-graph');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/f'artifacts/{args.variant}-lifecycle';root.mkdir(exist_ok=True)
    runtime=project/f'artifacts/baseline-{args.variant}-runtime.exe';source=project/'fixtures/official_naive_transcribed.c';meta=root/'program.meta';analyze(source,meta,'clang','cholesky')
    started=time.perf_counter();report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':sha256(runtime),'source_sha256':sha256(source),'tool_sha256':sha256(Path(__file__)),'cases':[],'contract':'local finite SPD domain; injected non-positive pivots must fail, join all workers and remove unpublished .partial; no official invalid-domain behavior claim'}
    destination=root/'test-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(report,indent=2)+'\n')
    save();n=257
    for pivot in(0,31,64,129,256):
        ip=root/'input.bin'
        with ip.open('wb')as stream:
            stream.write(struct.pack('<II',1,n))
            for row in range(n):
                values=array('d',[0.125])*n;values[row]=-1.0 if row==pivot else float(n+2);stream.write(values.tobytes())
        for queue in('heap','bucket'):
            for threads in(1,4,16):
                out=root/f'failure-{pivot}-{queue}-{threads}.bin';out.unlink(missing_ok=True);partial=out.with_name(out.name+'.partial');partial.unlink(missing_ok=True)
                command=[str(runtime),'--metadata',str(meta),'--input',str(ip),'--output',str(out),'--engine','tiled','--structure','dense','--tile-size','64','--threads',str(threads),'--scheduler','parallel','--ready-queue',queue]
                begin=time.perf_counter();result=subprocess.run(command,capture_output=True,text=True,timeout=30)
                if result.returncode==0 or 'not positive definite at pivot'not in result.stderr:raise AssertionError((command,result.returncode,result.stderr))
                if out.exists()or partial.exists():raise AssertionError('failed job published or leaked its partial output')
                report['cases'].append({'pivot':pivot,'threads':threads,'queue':queue,'exit_code':result.returncode,'stderr':result.stderr.strip(),'wall_ms':(time.perf_counter()-begin)*1000,'output_absent':True,'partial_absent':True});save()
    report['passed']=True;save();print(json.dumps({'passed':True,'cases':len(report['cases']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}))

if __name__=='__main__':main()
