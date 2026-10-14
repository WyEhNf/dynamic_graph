"""Lossless Metadata size comparisons with independently compiled source oracles."""
from pathlib import Path
import argparse,json,subprocess
from analyze_source import analyze
from evaluate_source import make_input,compile_oracle,run_runtime,exact_compare
from symbolic_metadata import decode_symbols

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,default=Path('build-ready/cholesky_runtime.exe'));args=p.parse_args()
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/metadata-milestone';root.mkdir(exist_ok=True);runtime=args.runtime.resolve();records=[];sizes=[]
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    for label,source,function in sources:
        folder=root/label;folder.mkdir(exist_ok=True);ip=folder/'input.bin';make_input(ip,[3,7,17,33]);ref=folder/'oracle.bin';oracle=compile_oracle(source,function,folder,'gcc',label=='blocked');subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        graphs=[];programs=[]
        for mode,inline,compact in [('expanded',True,False),('dag',True,False),('dag',False,False),('dag',False,True)]:
            meta=folder/f'{mode}-{int(inline)}-{int(compact)}.meta';analysis=analyze(source,meta,'clang',function,mode,inline,compact)
            header,body=meta.read_text().split('PROGRAM\n');fields=dict(line.split('=',1)for line in header.splitlines()[1:]);loops=json.loads(fields['symbolic_loops']);accesses=json.loads(fields['symbolic_accesses'])
            if mode=='dag':loops,accesses=decode_symbols(json.loads(fields['symbolic_expr_pool']),loops,accesses)
            graphs.append((loops,accesses));programs.append([(v[0],float(v[1])if len(v)>1 else 0.0)for v in(line.split()for line in body.splitlines())])
            for engine in ('vm','tiled'):
                out=folder/'runtime.bin';metrics=run_runtime(runtime,meta,ip,out,engine=engine,tile_size=7,threads=4,block=7,ready_queue='bucket')
                records.append({'source':label,'format':mode,'inline_provenance':inline,'compact_program':compact,**metrics,**exact_compare(ref,out)})
            sizes.append({'source':label,'format':mode,'inline_provenance':inline,'compact_program':compact,'metadata_bytes':analysis['metadata_bytes'],'instructions':analysis['instructions']})
        if not all(g==graphs[0]for g in graphs)or not all(code==programs[0]for code in programs):raise AssertionError('Metadata compression changed semantic graph or bytecode')
        print(f'PASS Metadata {label}: all symbolic graphs/programs equivalent and strict source C output',flush=True)
    report={'passed':True,'comparison':'identical reconstructed symbolic IR/instructions plus independent source full-file bytes','sizes':sizes,'runs':records}
    (root/'metadata-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'runs':len(records),'sizes':sizes},indent=2),flush=True)

if __name__=='__main__':main()
