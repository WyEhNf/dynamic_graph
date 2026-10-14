"""Preserve a tiny-program negative result: encoding headers need amortization."""
import hashlib,json,subprocess
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,make_input,run_runtime,exact_compare

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-metadata-wire-overhead'
    if root.exists():raise SystemExit('Refusing to overwrite prior overhead evidence')
    root.mkdir();source=root/'noop.c';source.write_text('int noop(const double *a,double *l,int n){return 0;}\n')
    runtime=project/'artifacts/stage2-metadata-wire/candidate.exe';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={name:sha(project/name) for name in ('tools/analyze_source.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/test_metadata_wire_overhead_stage2.py')}
    ip=root/'input.bin';make_input(ip,[3,17,65]);oracle=compile_oracle(source,'noop',root,'E:/mingw64/bin/gcc.exe')
    ref=root/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
    rows=[]
    for schema,mode in ((2,'dag'),(2,'table'),(3,'dag'),(3,'table')):
        meta=root/f'{schema}-{mode}.meta';analysis=analyze(source,meta,'C:/Program Files/LLVM/bin/clang.exe','noop',mode,metadata_schema=schema)
        out=root/f'{schema}-{mode}.bin';metrics=run_runtime(runtime,meta,ip,out,engine='vm',threads=1)
        rows.append({'schema':schema,'symbolic_format':mode,'metadata_bytes':analysis['metadata_bytes'],'sha256':sha(meta),'run':{**metrics,**exact_compare(ref,out)}})
    report={'passed':True,'source_sha256':sha(source),'runtime_sha256':sha(runtime),'source_hashes':hashes,'runtime_comparisons':4,'rows':rows,'scope':'One tiny constant-return C source, three sizes; fixed encoding/record-table headers can exceed avoided mnemonic bytes.'}
    (root/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':True,'sizes':[row['metadata_bytes'] for row in rows]}),flush=True)

if __name__=='__main__':main()
