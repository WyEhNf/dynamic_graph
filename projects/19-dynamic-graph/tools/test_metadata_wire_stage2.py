"""Independent wire golden, graph/program equality and full compiled-C bytes."""
import argparse,hashlib,json,subprocess,time,shutil
from pathlib import Path
from analyze_source import analyze
from metadata_wire import encode_instruction,decode_instruction
from symbolic_metadata import decode_symbols,decode_record_table
from evaluate_source import make_input,compile_oracle,run_runtime,exact_compare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',type=Path,default=Path('build-stage2-wire/cholesky_runtime.exe'))
    parser.add_argument('--output-dir',type=Path,default=Path('artifacts/stage2-metadata-wire'))
    args=parser.parse_args();project=Path(__file__).resolve().parents[1]
    root=args.output_dir.resolve();runtime=args.runtime.resolve()
    if root.exists():raise SystemExit('Refusing to overwrite prior wire evidence')
    root.mkdir();started=time.perf_counter();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    frozen=root/'source';frozen.mkdir()
    files=['CMakeLists.txt','src/runtime.cpp','include/cholesky/runtime.hpp','tools/analyze_source.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/test_metadata_wire_stage2.py','tests/metadata_wire_tests.cpp']
    hashes={}
    for name in files:
        target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target);hashes[name]=sha(target)
    (root/'source-manifest.json').write_text(json.dumps(hashes,indent=2))
    shutil.copyfile(runtime,root/'candidate.exe')
    # Literal golden independent of either language's table.
    names='CONST LOAD STORE UNINIT READ WRITE DUP POP ADD SUB MUL DIV IDIV MOD NEG NOT BOOL TRUNC SQRT ABS MIN MAX FMA LT LE GT GE EQ NE JUMP JZ JNZ RETURN'.split()
    codes='0123456789ABCDEFGHIJKLMNOPQRSTUVW'
    for code,name in zip(codes,names):
        arg=' -0.0' if name=='CONST' else ' 1' if name in ('LOAD','STORE','UNINIT','READ','WRITE','JUMP','JZ','JNZ') else ''
        assert encode_instruction(name+arg)==code+arg
        assert decode_instruction(code+arg)==name+arg
    numeric=['-0.0','+0.0','1e-300','-1.7976931348623157e308','.5','1.','+2E+3']
    for token in numeric:assert decode_instruction(encode_instruction('CONST '+token))=='CONST '+token
    malformed=['','X','Z','a','00 0','CONST 0','0','8 0','8 ','0  1','0 1 ','0 1 2','0 nan','0 inf','0 1e999','0 0x1p0','0 .','0 1e','0 +','0\t1']
    for line in malformed:
        try:decode_instruction(line)
        except ValueError:pass
        else:raise AssertionError('invalid wire accepted: '+repr(line))
    # Generic and signed-zero programs also exercise the fallback, not Cholesky dispatch.
    generic=root/'generic.c'
    generic.write_text('''#include <math.h>
int transform(const double *a,double *l,int n) {
  int i=0;
  while(i<n*n) {
    int q=i/3; int r=i%3;
    double x=a[i];
    if (!(x<0.0) && q>=0) l[i]=fma(fmin(fabs(x),4.0),0.5,fmax(sqrt(fabs(x)),1.0));
    else l[i]=r!=0 ? -x : x/2.0;
    i=i+1;
  }
  return 0;
}
''')
    zero=root/'negative-zero.c'
    zero.write_text('''int zeros(const double *a,double *l,int n) {
 for(int i=0;i<n*n;i=i+1) l[i]=-0.0;
 return 0;
}
''')
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('generic',generic,'transform'),('negative-zero',zero,'zeros')]
    report={'passed':False,'schema_default':2,'candidate_sha256':sha(runtime),'frozen_candidate_sha256':sha(root/'candidate.exe'),
            'source_hashes':hashes,'protocol_golden_opcodes':33,'argument_text_roundtrips':len(numeric),'python_malformed_rejected':len(malformed),
            'scope':'Five actual C programs, two data families, source-order VM and tiled/fallback; finite tests, not arbitrary C or official Metadata points',
            'reference':'https://llvm.org/docs/BitCodeFormat.html#abbreviations','reference_inference':'Record IDs can avoid repeated mnemonic text. This is a custom UTF-8 wire format, not LLVM bitcode.',
            'sources':[]}
    comparisons=0
    for label,source,function in sources:
        folder=root/label;folder.mkdir();oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked')
        formats=[];graphs=[];programs=[];headers=[]
        for schema,mode in ((2,'dag'),(2,'table'),(3,'table')):
            path=folder/f'schema{schema}-{mode}.meta';analysis=analyze(source,path,'C:/Program Files/LLVM/bin/clang.exe',function,mode,metadata_schema=schema)
            header,body=path.read_text(encoding='utf-8').split('PROGRAM\n');fields=dict(line.split('=',1) for line in header.splitlines()[1:])
            loops=decode_record_table(json.loads(fields['symbolic_loop_table'])) if mode=='table' else json.loads(fields['symbolic_loops'])
            accesses=decode_record_table(json.loads(fields['symbolic_access_table'])) if mode=='table' else json.loads(fields['symbolic_accesses'])
            graphs.append(decode_symbols(json.loads(fields['symbolic_expr_pool']),loops,accesses));programs.append([decode_instruction(line) if schema==3 else line for line in body.splitlines()])
            headers.append({key:value for key,value in fields.items() if not key.startswith('symbolic_') and key!='bytecode_encoding'})
            runs=[]
            for family in ('dense','diagonal-signed-zero'):
                ip=folder/f'{family}-input.bin';make_input(ip,[3,7,17,31,33,65,127],diagonal=family!='dense',signed_zero=family!='dense')
                ref=folder/f'{family}-oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                for engine in ('vm','tiled'):
                    out=folder/f'{family}-{schema}-{mode}-{engine}.bin'
                    metrics=run_runtime(runtime,path,ip,out,engine=engine,tile_size=7,threads=1,block=7)
                    runs.append({'family':family,'engine':engine,**metrics,**exact_compare(ref,out)});comparisons+=1
            formats.append({'schema':schema,'mode':mode,'metadata_bytes':analysis['metadata_bytes'],'sha256':sha(path),'runs':runs})
        assert graphs[0]==graphs[1]==graphs[2] and programs[0]==programs[1]==programs[2] and headers[0]==headers[1]==headers[2]
        row={'label':label,'source_sha256':sha(source),'formats':formats,'dag_to_schema3_table_reduction':1-formats[2]['metadata_bytes']/formats[0]['metadata_bytes'],'table_to_schema3_reduction':1-formats[2]['metadata_bytes']/formats[1]['metadata_bytes']}
        report['sources'].append(row);print(json.dumps({'source':label,'sizes':[f['metadata_bytes'] for f in formats]}),flush=True)
    assert sha(runtime)==report['candidate_sha256']
    assert all(sha(project/name)==value for name,value in hashes.items())
    report.update(passed=True,runtime_comparisons=comparisons,wall_seconds=time.perf_counter()-started)
    (root/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'passed':True,'comparisons':comparisons,'wall_seconds':report['wall_seconds']}),flush=True)


if __name__=='__main__':main()
