"""Check all six emitted candidates independently and single-compilation selection."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from unittest.mock import patch
import analyze_source
from symbolic_metadata import decode_symbols,decode_record_table
from metadata_wire import decode_instruction
from evaluate_source import compile_oracle,make_input,run_runtime,exact_compare


def expanded(path):
    header,body=path.read_text(encoding='utf-8').split('PROGRAM\n')
    version=int(header.splitlines()[0].split()[1]);fields=dict(line.split('=',1) for line in header.splitlines()[1:])
    encoding=fields['symbolic_encoding']
    if encoding=='expr_tree_v1':
        graph=json.loads(fields['symbolic_loops']),json.loads(fields['symbolic_accesses'])
    else:
        if encoding=='expr_dag_record_table_v1':
            loops=decode_record_table(json.loads(fields['symbolic_loop_table']));accesses=decode_record_table(json.loads(fields['symbolic_access_table']))
        else:loops=json.loads(fields['symbolic_loops']);accesses=json.loads(fields['symbolic_accesses'])
        graph=decode_symbols(json.loads(fields['symbolic_expr_pool']),loops,accesses)
    program=[decode_instruction(line) if version==3 else line for line in body.splitlines()]
    headers={key:value for key,value in fields.items() if not key.startswith('symbolic_') and key!='bytecode_encoding'}
    return graph,program,headers


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1];root=args.output_dir.resolve() if args.output_dir else project/'artifacts/stage2-smallest-metadata'
    if root.exists():raise SystemExit('Refusing to overwrite minimum evidence')
    root.mkdir();started=time.perf_counter();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    runtime=args.runtime.resolve() if args.runtime else project/'artifacts/stage2-metadata-wire/candidate.exe';hashes={}
    for name in ('tools/analyze_source.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/test_smallest_metadata_stage2.py'):
        target=root/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target);hashes[name]=sha(target)
    (root/'source-manifest.json').write_text(json.dumps(hashes,indent=2));shutil.copyfile(runtime,root/'candidate.exe')
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('generic',project/'artifacts/stage2-metadata-wire/generic.c','transform'),('negative-zero',project/'artifacts/stage2-metadata-wire/negative-zero.c','zeros'),('noop',project/'artifacts/stage2-metadata-wire-overhead/noop.c','noop')]
    report={'passed':False,'runtime_sha256':sha(runtime),'source_hashes':hashes,'sources':[],'scope':'Six real supported C programs; all six explicit encodings decoded losslessly, minimum selected from one AST/one LLVM-IR compilation, exact original-C whole files'}
    original_run=subprocess.run;comparisons=0
    for label,source,function in sources:
        folder=root/label;folder.mkdir();shutil.copyfile(source,folder/'source.c')
        rows=[];graphs=[]
        # Separately invoking explicit options supplies independent physical byte sizes.
        # Only this verification does six compiles; --smallest-metadata itself does one.
        for schema in (2,3):
            for mode in ('dag','table','expanded'):
                path=folder/f'{schema}-{mode}.meta';analysis=analyze_source.analyze(source,path,'C:/Program Files/LLVM/bin/clang.exe',function,mode,metadata_schema=schema)
                rows.append({'schema':schema,'mode':mode,'bytes':path.stat().st_size,'sha256':sha(path),'path':str(path)})
                graphs.append(expanded(path))
        assert all(graph==graphs[0] for graph in graphs)
        calls=[]
        def tracked(command,*args,**kwargs):
            calls.append(command)
            return original_run(command,*args,**kwargs)
        minimum=folder/'minimum.meta'
        with patch.object(analyze_source.subprocess,'run',tracked):
            analysis=analyze_source.analyze(source,minimum,'C:/Program Files/LLVM/bin/clang.exe',function,smallest_metadata=True)
        ast_calls=sum('-ast-dump=json' in call for call in calls);llvm_calls=sum('-emit-llvm' in call for call in calls)
        assert ast_calls==1 and llvm_calls==1
        expected=min(rows,key=lambda row:(row['bytes'],row['schema'],('dag','table','expanded').index(row['mode'])))
        assert minimum.read_bytes()==Path(expected['path']).read_bytes()
        assert expanded(minimum)==graphs[0] and minimum.stat().st_size<=rows[0]['bytes']
        observed={(row['schema'],row['mode']):(row['bytes'],row['sha256']) for row in rows}
        declared={(row['metadata_schema'],row['symbolic_format']):(row['metadata_bytes'],row['sha256']) for row in analysis['encoding_candidates']}
        assert observed==declared
        oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked');runs=[]
        for family in ('dense','diagonal-signed-zero'):
            ip=folder/f'{family}-input.bin';make_input(ip,[3,7,17,31,33,65,127],diagonal=family!='dense',signed_zero=family!='dense')
            ref=folder/f'{family}-oracle.bin';original_run([str(oracle),str(ip),str(ref),'7'],check=True)
            for engine in ('vm','tiled'):
                out=folder/f'{family}-{engine}.bin';metrics=run_runtime(runtime,minimum,ip,out,engine=engine,tile_size=7,threads=1,block=7)
                runs.append({'family':family,'engine':engine,**metrics,**exact_compare(ref,out)});comparisons+=1
        row={'label':label,'source_sha256':sha(source),'candidates':rows,'selection':{'schema':analysis['metadata_schema'],'mode':expected['mode'],'bytes':minimum.stat().st_size,'sha256':sha(minimum)},'ast_compilations':ast_calls,'llvm_ir_compilations':llvm_calls,'runs':runs}
        report['sources'].append(row);print(json.dumps({'source':label,'old_bytes':rows[0]['bytes'],'selected':row['selection']}),flush=True)
    invalid=[['--metadata-schema','2'],['--metadata-schema','3'],['--symbolic-format','dag'],['--symbolic-format','table'],['--full-bytecode-args']]
    for options in invalid:
        run=original_run([str(project/'.venv/Scripts/python.exe'),str(project/'tools/analyze_source.py'),str(sources[0][1]),'--output',str(root/'invalid.meta'),'--smallest-metadata',*options],capture_output=True,text=True)
        assert run.returncode!=0 and 'mutually exclusive' in run.stderr and not (root/'invalid.meta').exists()
    assert all(sha(project/name)==value for name,value in hashes.items())
    report.update(passed=True,runtime_comparisons=comparisons,conflicting_cli_options_rejected=len(invalid),wall_seconds=time.perf_counter()-started)
    (root/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'passed':True,'comparisons':comparisons,'wall_seconds':report['wall_seconds']}),flush=True)


if __name__=='__main__':main()
