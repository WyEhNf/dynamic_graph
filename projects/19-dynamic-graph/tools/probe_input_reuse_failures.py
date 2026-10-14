"""Keep actual whole-process memory/CPU counters also for failed owned runs."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,struct,time
from benchmark_extended import stress_input
from analyze_source import analyze
from research_reference import sha256
from windows_resource_probe import monitored_run

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('input-reuse','input-reuse-auto'),default='input-reuse');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/f'artifacts/{args.variant}-failure-probe';root.mkdir(exist_ok=True)
    binary=project/f'artifacts/baseline-{args.variant}-runtime.exe';source=project/'fixtures/official_naive_transcribed.c';meta=root/'program.meta';analyze(source,meta,'clang','cholesky');started=time.perf_counter()
    r={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':sha256(binary),'source_sha256':sha256(source),'tool_sha256':sha256(Path(__file__)),'probe_sha256':sha256(project/'tools/windows_resource_probe.py'),'cases':[],'contract':'M2 first valid full193 then injected negative pivot/NaN/truncated; monitored original runtime process check=False with30s deadline; failed output andpartial absent; peak WS/commit, all-thread CPU and host load kept'}
    destination=root/'test-report.json'
    for n in(257,2049):
        good=root/'good.bin';stress_input(good,[193],'near-rank-one');base=good.read_bytes()[4:]
        bad=root/'bad.bin';stress_input(bad,[n],'near-rank-one');tail=bytearray(bad.read_bytes()[4:]);struct.pack_into('<d',tail,4+8*(n*n-1),-1.0)
        cases=[('late-pivot',bytes(tail)),('late-nan',base[:4]+struct.pack('<d',float('nan'))+base[12:]),('late-truncated',base[:-1])]
        if args.variant=='input-reuse-auto':
            stress_input(bad,[n],'signed-zero');band=bytearray(bad.read_bytes()[4:]);struct.pack_into('<d',band,4+8*(n*n-1),-1.0);cases.append(('late-band-pivot',bytes(band)))
        for kind,payload in cases:
            ip=root/'input.bin';ip.write_bytes(struct.pack('<I',2)+base+payload)
            for t in(1,4,16):
                out=root/'output.bin';out.unlink(missing_ok=True);partial=Path(str(out)+'.partial');partial.unlink(missing_ok=True)
                cmd=[str(binary),'--metadata',str(meta),'--input',str(ip),'--output',str(out),'--engine','tiled','--structure','auto'if args.variant=='input-reuse-auto'else'dense','--threads',str(t),'--scheduler','parallel','--tile-size','64']
                start=time.perf_counter();cp,m=monitored_run(cmd,check=False,timeout=30)
                if cp.returncode==0 or out.exists()or partial.exists():raise AssertionError(('failed process published output',kind,cp.stderr))
                expected={'late-pivot':'not positive definite','late-nan':'non-finite matrix element','late-truncated':'truncated','late-band-pivot':'not positive definite at band pivot'}[kind]
                if expected not in cp.stderr:raise AssertionError(('wrong error',kind,cp.stderr))
                r['cases'].append({'n':n,'case':kind,'threads':t,'exit_code':cp.returncode,'error':cp.stderr.strip(),'wall_ms':1000*(time.perf_counter()-start),'output_absent':True,'partial_absent':True,**m})
                r['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(r,indent=2)+'\n')
    r['passed']=True;r['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(r['cases']),'elapsed_seconds':r['elapsed_seconds'],'report':str(destination)}))
if __name__=='__main__':main()
