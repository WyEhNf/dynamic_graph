"""Reuse proven original-C large files; no runtime generates reference bytes."""
import argparse,hashlib,json,time
from pathlib import Path
from evaluate_source import exact_compare,run_runtime

def main():
    p=argparse.ArgumentParser();p.add_argument('--local-runtime',type=Path,required=True)
    p.add_argument('--memory-runtime',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
    root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=False);project=Path(__file__).resolve().parents[1]
    r={'passed':False,'scope':'Maximum dynamic Shape and owned structured paths; original C cached full-file references. Times are validation observations, not a paired speed claim.','rows':[]};start=time.perf_counter()
    cases=[('dense-10000',project/'artifacts/maximum-dense-oracle/input.bin',project/'artifacts/maximum-dense-oracle/oracle.bin',
       '4015abfccfe5851a9c959939ff61ee44acf0290fcbf6192cdfd59a3a217eef13'),
       ('band-10000',project/'artifacts/band-maximum-reference/input.bin',project/'artifacts/band-maximum-reference/oracle.bin',
       'fb50d92b7bb6519d52bb69afba48b36745ac56f9bf7cf3e109adbcb53154a0c2')]
    for label,ip,ref,expected in cases:
        for profile,runtime in [('local',args.local_runtime),('memory',args.memory_runtime)]:
            output=root/f'{profile}-{label}.bin';m=run_runtime(runtime,args.metadata,ip,output,threads=16)
            check=exact_compare(ref,output);assert check['sha256']==expected
            row=dict(profile=profile,case=label,runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
                     input=str(ip),oracle=str(ref),metrics=m,correctness=check)
            r['rows'].append(row);print(json.dumps({'profile':profile,'case':label,'passed':True}),flush=True)
    r.update(passed=True,comparisons=len(r['rows']),wall_seconds=time.perf_counter()-start)
    (root/'report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
