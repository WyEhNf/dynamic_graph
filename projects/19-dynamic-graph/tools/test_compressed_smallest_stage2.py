"""Compare every complete container, one frontend compile, native/C semantics."""
import hashlib,json,shutil,struct,subprocess,time,zlib
from pathlib import Path
from unittest.mock import patch
import analyze_source
from metadata_container import decode
from test_smallest_metadata_stage2 import expanded
from evaluate_source import compile_oracle,run_runtime,exact_compare

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def standard_encode(raw):
    payload=zlib.compress(raw,9)
    return b'DYNCHZ01'+struct.pack('<II',len(raw),len(payload))+payload

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-compressed-smallest';root.mkdir(exist_ok=False)
    frozen=project/'artifacts/stage2-smallest-metadata';previous=project/'artifacts/stage2-metadata-zlib'
    prior=json.loads((previous/'manifest.json').read_text());runtime=previous/'cholesky_runtime.exe';codec=previous/'metadata_container_codec.exe'
    assert sha(runtime)==prior['runtime_sha256'] and sha(codec)==prior['codec_sha256']
    assert sha(project/'build/cholesky_runtime.exe')==prior['unchanged_installed_ordinary_sha256']
    shutil.copyfile(runtime,root/'runtime.exe');shutil.copyfile(codec,root/'codec.exe');hashes={}
    for name in ('tools/analyze_source.py','tools/metadata_container.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/c_frontend.py','tools/semantic_cholesky.py','tools/evaluate_source.py','tools/test_compressed_smallest_stage2.py','tools/test_metadata_zlib_stage2.py','tools/test_smallest_metadata_stage2.py'):
        path=root/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,path);hashes[name]=sha(path)
    report={'passed':False,'runtime_sha256':sha(runtime),'codec_sha256':sha(codec),'ordinary_runtime_sha256':sha(project/'build/cholesky_runtime.exe'),'prior_manifest_sha256':sha(previous/'manifest.json'),'source_sha256':hashes,'sources':[],'scope':'Six complete equivalent containers scored by actual final bytes; independently encoded, expanded and native-decoded; actual source C entire output files; no native math/build change','tie_rule':'lowest final bytes then schema2 before schema3 then dag/table/expanded','python_zlib_runtime':zlib.ZLIB_RUNTIME_VERSION}
    started=time.perf_counter();original_run=subprocess.run;comparisons=0
    functions={'scalar':'cholesky_reference','page':'cholesky','blocked':'cholesky_blocked','generic':'transform','negative-zero':'zeros','noop':'noop'}
    for label,function in functions.items():
        folder=root/label;folder.mkdir();source=folder/'source.c';shutil.copyfile(frozen/label/'source.c',source)
        candidates=[];graphs=[]
        # Independent physical candidate files; no AST/IR generation for each candidate.
        # Their full raw bytes come from previously frozen, independently checked encodings.
        for schema in (2,3):
            for mode in ('dag','table','expanded'):
                raw=(frozen/label/f'{schema}-{mode}.meta').read_bytes();container=standard_encode(raw)
                path=folder/f'{schema}-{mode}.container.meta';path.write_bytes(container)
                rawpath=folder/f'{schema}-{mode}.raw.meta';rawpath.write_bytes(decode(container));assert rawpath.read_bytes()==raw
                graphs.append(expanded(rawpath))
                output=folder/f'{schema}-{mode}.native.raw.meta';original_run([str(codec),'decode',str(path),str(output)],check=True)
                assert output.read_bytes()==raw
                original_run([str(codec),'parse',str(path),str(folder/f'{schema}-{mode}.parse')],check=True)
                candidates.append({'metadata_schema':schema,'symbolic_format':mode,'metadata_bytes':len(container),'sha256':sha(path),'uncompressed_metadata_bytes':len(raw),'uncompressed_metadata_sha256':sha(rawpath),'path':str(path)})
        assert all(graph==graphs[0]for graph in graphs)
        expected=min(candidates,key=lambda item:(item['metadata_bytes'],item['metadata_schema'],('dag','table','expanded').index(item['symbolic_format'])))
        calls=[]
        def tracked(command,*args,**kwargs):calls.append(command);return original_run(command,*args,**kwargs)
        minimum=folder/'minimum.container.meta'
        with patch.object(analyze_source.subprocess,'run',tracked):
            analysis=analyze_source.analyze(source,minimum,'C:/Program Files/LLVM/bin/clang.exe',function,smallest_metadata=True,compress_metadata=True)
        counts={'ast':sum('-ast-dump=json'in cmd for cmd in calls),'llvm_ir':sum('-emit-llvm'in cmd for cmd in calls)}
        assert counts=={'ast':1,'llvm_ir':1} and minimum.read_bytes()==Path(expected['path']).read_bytes()
        assert analysis['metadata_schema']==expected['metadata_schema'] and analysis['minimum_cost_metric']=='final_container_bytes'
        fields=('metadata_schema','symbolic_format','metadata_bytes','sha256','uncompressed_metadata_bytes','uncompressed_metadata_sha256')
        assert [{key:row[key]for key in fields}for row in candidates]==analysis['encoding_candidates']
        assert analysis['uncompressed_metadata_sha256']==expected['uncompressed_metadata_sha256']
        newraw=folder/'minimum.raw.meta';newraw.write_bytes(decode(minimum.read_bytes()));assert expanded(newraw)==graphs[0]
        oldraw=(frozen/label/'minimum.meta').read_bytes();oldcompressed=standard_encode(oldraw)
        assert minimum.stat().st_size<=len(oldcompressed)
        # Uncompressed and explicit-format paths retain their own prior contracts.
        oldmin=folder/'uncompressed-minimum.meta';analyze_source.analyze(source,oldmin,'C:/Program Files/LLVM/bin/clang.exe',function,smallest_metadata=True)
        default=folder/'uncompressed-default.meta';analyze_source.analyze(source,default,'C:/Program Files/LLVM/bin/clang.exe',function)
        explicit=folder/'explicit-2-dag.container.meta';single=analyze_source.analyze(source,explicit,'C:/Program Files/LLVM/bin/clang.exe',function,compress_metadata=True)
        assert oldmin.read_bytes()==oldraw and default.read_bytes()==(frozen/label/'2-dag.meta').read_bytes()
        assert explicit.read_bytes()==Path(candidates[0]['path']).read_bytes() and not single['smallest_metadata'] and not single['encoding_candidates']
        oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked');runs=[]
        for family in ('dense','diagonal-signed-zero'):
            ip=folder/(family+'-input.bin');shutil.copyfile(frozen/label/(family+'-input.bin'),ip)
            ref=folder/(family+'-oracle.bin');original_run([str(oracle),str(ip),str(ref),'7'],check=True)
            for engine in ('vm','tiled'):
                output=folder/(family+'-'+engine+'.bin');metrics=run_runtime(runtime,minimum,ip,output,engine=engine,threads=1,block=7,tile_size=7)
                runs.append({'family':family,'engine':engine,'input_sha256':sha(ip),'reference_sha256':sha(ref),**metrics,**exact_compare(ref,output)});comparisons+=1
        result={'source':label,'source_sha256':sha(source),'oracle_sha256':sha(oracle),'candidates':candidates,'selection':{key:expected[key]for key in fields},'prior_compressed_minimum_bytes':len(oldcompressed),'prior_compressed_minimum_sha256':hashlib.sha256(oldcompressed).hexdigest(),'compilation_counts':counts,'uncompressed_default_and_minimum_unchanged':True,'explicit_single_format_preserved':True,'runs':runs}
        report['sources'].append(result);print(json.dumps({'source':label,'old':len(oldcompressed),'new':minimum.stat().st_size,'schema':expected['metadata_schema'],'format':expected['symbolic_format'],'compilations':counts}),flush=True)
    # CLI combination must use final-byte selection too; conflicts still fail closed.
    cli=root/'cli.container.meta'
    original_run([str(project/'.venv/Scripts/python.exe'),str(project/'tools/analyze_source.py'),str(root/'page/source.c'),'--clang','C:/Program Files/LLVM/bin/clang.exe','--function','cholesky','--output',str(cli),'--smallest-metadata','--compress-metadata'],check=True,capture_output=True,text=True)
    assert cli.read_bytes()==(root/'page/minimum.container.meta').read_bytes()
    for i,flags in enumerate((['--metadata-schema','2'],['--symbolic-format','expanded'],['--full-bytecode-args'])):
        invalid=root/f'invalid-{i}.meta';run=original_run([str(project/'.venv/Scripts/python.exe'),str(project/'tools/analyze_source.py'),str(root/'page/source.c'),'--output',str(invalid),'--smallest-metadata','--compress-metadata',*flags],capture_output=True,text=True)
        assert run.returncode!=0 and 'mutually exclusive' in run.stderr and not invalid.exists()
    assert all(sha(project/name)==value for name,value in hashes.items())
    assert sha(project/'build/cholesky_runtime.exe')==report['ordinary_runtime_sha256'] and sha(runtime)==report['runtime_sha256']
    report.update(passed=True,comparisons=comparisons,whole_container_candidates=36,cli_combination_passed=True,conflicting_cli_options_rejected=3,wall_seconds=time.perf_counter()-started)
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'comparisons':comparisons,'wall_seconds':report['wall_seconds']}),flush=True)

if __name__=='__main__':main()
