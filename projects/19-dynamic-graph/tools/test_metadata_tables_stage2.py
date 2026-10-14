"""Verify graph/bytecode preservation and actual compiled-C bytes for table IR."""
import hashlib,json,random,subprocess,time
from pathlib import Path
from analyze_source import analyze
from symbolic_metadata import decode_symbols,encode_record_table,decode_record_table
from evaluate_source import make_input,compile_oracle,run_runtime,exact_compare


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'artifacts/stage2-metadata-tables'
    if root.exists():raise SystemExit('Refusing to overwrite previous test')
    root.mkdir();started=time.perf_counter();rng=random.Random(191026)
    for _ in range(400):
        records=[{key:rng.choice([None,True,False,0,-17,[],[1,'x'],{'nested':None},'output'])
                  for key in ('id','parent','condition','custom') if rng.randrange(2)} for _ in range(rng.randrange(9))]
        decoded=decode_record_table(json.loads(json.dumps(encode_record_table(records))))
        assert decoded==records
    malformed=[None,[],[[],[],[]],[[1],[]],[['a','a'],[]],[[],0],[[],[[1,[]]]],
               [['a'],[[True,[1]]]],[['a'],[[-1,[]]]],[['a'],[[2,[1]]]],
               [['a'],[[1,[]]]],[['a'],[[0,[1]]]]]
    for bad in malformed:
        try:decode_record_table(bad)
        except ValueError:pass
        else:raise AssertionError('Invalid table accepted')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    runtime=project/'artifacts/stage2-packed-ready/baseline.exe'
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),
             ('page',project/'fixtures/official_naive_transcribed.c','cholesky'),
             ('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked')]
    report={'passed':False,'contract':'Identical expanded original symbolic graph and exact bytecode, then full compiled-C IEEE754 bytes',
            'scope':'Three concrete C programs and 400 generic sparse record roundtrips; not arbitrary C or an official score',
            'roundtrips':400,'invalid_tables_rejected':len(malformed),'baseline_binary_sha256':sha(runtime),'sources':[]}
    for label,source,function in sources:
        folder=root/label;folder.mkdir();ip=folder/'input.bin';make_input(ip,[3,7,17,31,33,65])
        oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked')
        ref=folder/'oracle.bin';subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        entry={'label':label,'source_sha256':sha(source),'formats':[]};graphs=[];programs=[]
        for mode in ('dag','table'):
            path=folder/f'{mode}.meta';analysis=analyze(source,path,'C:/Program Files/LLVM/bin/clang.exe',function,mode)
            header,program=path.read_text(encoding='utf-8').split('PROGRAM\n');fields=dict(line.split('=',1)for line in header.splitlines()[1:])
            if mode=='table':
                loops=decode_record_table(json.loads(fields['symbolic_loop_table']))
                accesses=decode_record_table(json.loads(fields['symbolic_access_table']))
            else:loops=json.loads(fields['symbolic_loops']);accesses=json.loads(fields['symbolic_accesses'])
            graphs.append(decode_symbols(json.loads(fields['symbolic_expr_pool']),loops,accesses));programs.append(program)
            runs=[]
            for engine in ('vm','tiled'):
                out=folder/'runtime.bin';metrics=run_runtime(runtime,path,ip,out,engine=engine,tile_size=7,threads=4,block=7)
                runs.append({'engine':engine,**metrics,**exact_compare(ref,out)})
            entry['formats'].append({'mode':mode,'metadata_bytes':analysis['metadata_bytes'],'sha256':sha(path),'runs':runs})
        assert graphs[0]==graphs[1] and programs[0]==programs[1]
        entry['bytes_reduction']=1-entry['formats'][1]['metadata_bytes']/entry['formats'][0]['metadata_bytes']
        report['sources'].append(entry)
        print(json.dumps({'source':label,'sizes':[r['metadata_bytes']for r in entry['formats']],'reduction':entry['bytes_reduction']}),flush=True)
    report.update(passed=True,wall_seconds=time.perf_counter()-started)
    (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'runtime_comparisons':12,'wall_seconds':report['wall_seconds']}),flush=True)


if __name__=='__main__':main()
