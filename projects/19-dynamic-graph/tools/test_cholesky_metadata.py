"""Primary gate: three actual Cholesky C sources, all eight complete encodings.

Reference files are generated only by independently compiled original C.
Generic VM/changed-arithmetic controls belong to separate source_pipeline tests.
"""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
from analyze_source import PreparedSource
from evaluate_source import compile_oracle,make_input,run_runtime,exact_compare
from test_smallest_metadata_stage2 import expanded

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--gcc',required=True)
    parser.add_argument('--clang',required=True)
    args=parser.parse_args();root=args.output_dir.resolve()
    if root.exists():raise SystemExit('Refusing to overwrite Cholesky acceptance evidence')
    root.mkdir(parents=True);start=time.perf_counter();project=Path(__file__).resolve().parents[1]
    os.environ.update(TEMP=str(root),TMP=str(root))
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report={'passed':False,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Primary actual Cholesky only; strict full binary files versus independent original C',
            'runtime_sha256':sha(args.runtime),'sources':[]}
    count=0
    for label,file,function,blocks in [('page','official_naive_transcribed.c','cholesky',[7]),
        ('scalar','cholesky_reference.c','cholesky_reference',[7]),
        ('blocked','cholesky_blocked.c','cholesky_blocked',[1,7,32,100])]:
        folder=root/label;folder.mkdir();source=project/'fixtures'/file
        prepared=PreparedSource(source,args.clang);variants=[];graphs=[]
        for schema in (2,3):
            for mode in ('dag','table','expanded','packed'):
                meta=folder/f'{schema}-{mode}.meta'
                prepared.emit(meta,function=function,metadata_schema=schema,symbolic_format=mode,emit_ir=False)
                variants.append(meta);graphs.append(expanded(meta))
        assert all(g==graphs[0] for g in graphs)
        default=folder/'default.meta';prepared.emit(default,function=function,emit_ir=False)
        assert default.read_bytes()==variants[0].read_bytes()
        minimum=folder/'minimum.meta';prepared.emit(minimum,function=function,smallest_metadata=True,emit_ir=False)
        assert minimum.read_bytes()==min(variants,key=lambda p:p.stat().st_size).read_bytes()
        oracle=compile_oracle(source,function,folder,args.gcc,label=='blocked');runs=[]
        for family in ('dense','diagonal-signed-zero'):
            ip=folder/f'{family}.bin';make_input(ip,[3,7,31,65,129],family!='dense',family!='dense')
            # VM includes the N=129 native boundary; it executes the original source order.
            for block in blocks:
                reference=folder/f'{family}-{block}-oracle.bin'
                subprocess.run([str(oracle),str(ip),str(reference),str(block)],check=True)
                for meta in variants:
                    for engine,threads in [('vm',1),('tiled',1),('tiled',4)]:
                        output=folder/'actual.bin'
                        metrics=run_runtime(args.runtime,meta,ip,output,engine=engine,threads=threads,block=block,tile_size=7)
                        runs.append(dict(metadata=meta.name,family=family,block=block,engine=engine,threads=threads,
                                         **exact_compare(reference,output),compute_ms=metrics['compute_ms']))
                        count+=1
        report['sources'].append(dict(label=label,source=str(source),source_sha256=sha(source),
           helper_contract='local separate multiply/subtract, division, zero-initialized L' if label=='page' else 'self-authored mathematical Cholesky fixture',
           complete_graph_program_header_equal=True,default_unchanged=True,runs=runs))
        print(json.dumps({'source':label,'runs':len(runs),'passed':True}),flush=True)
    report.update(passed=True,runtime_comparisons=count,wall_seconds=time.perf_counter()-start)
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'runtime_comparisons':count}),flush=True)

if __name__=='__main__':main()
