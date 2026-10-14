"""Pure int selector bounds, source conversion traps and fail-closed proof."""
from pathlib import Path
import argparse,hashlib,json,struct,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import evaluate
from test_project import reject
from test_while_proof import BLOCKED

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=Path('artifacts/baseline-thread-policy-runtime.exe'));parser.add_argument('--gcc',default='gcc');parser.add_argument('--clang',default='clang');parser.add_argument('--output-dir',type=Path,default=Path('artifacts/integer-selector-milestone'));args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=args.output_dir.resolve();root.mkdir(exist_ok=True,parents=True);runtime=args.runtime.resolve();started=time.perf_counter()
    helper='static int choose(int x,int y){return x<y?x:y;}\n'
    blocked=(project/'fixtures/cholesky_blocked.c').read_text()
    blocked=helper+blocked.replace('panel + block_size < n ? panel + block_size : n','choose(panel + block_size,n)').replace('row_tile + block_size < n ? row_tile + block_size : n','choose(row_tile + block_size,n)').replace('col_tile + block_size < j+1 ? col_tile + block_size : j+1','choose(col_tile + block_size,j+1)')
    while_source=helper+BLOCKED.replace('panel+block<n?panel+block:n','choose(panel+block,n)').replace('row_tile+block<n?row_tile+block:n','choose(row_tile+block,n)').replace('col_tile+block<j+1?col_tile+block:j+1','choose(col_tile+block,j+1)')
    sources={
      'blocked-min':(blocked,'cholesky_blocked',True,(1,7,32,100)),
      'blocked-min-fma':(blocked.replace('return x * y + z;','return fma(x,y,z);'),'cholesky_blocked',True,(1,7,32,100)),
      'while-blocked-min':(while_source,'factor',True,(1,7,32,100)),
      'generic-min-max':(helper+'static int greatest(int x,int y){return x>y?x:y;}\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=greatest(choose(i,n),i-n);return 0;}','transform',False,(7,)),
      'double-argument-conversion':(blocked.replace('choose(panel + block_size,n)','choose((double)(panel + block_size)+0.9,n)'),'cholesky_blocked',False,(7,)),
      'integer-local-copy':(blocked.replace('return x<y?x:y;','int copy=x;return copy<y?copy:y;'),'cholesky_blocked',False,(7,)),
    }
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'cases':[],'rejections':[],'contract':'only direct int comparison plus direct parameter selection has no intrinsic trap; actual argument expressions remain in complete native proof; full independent original-C bytes'}
    for label,(text,function,native,blocks)in sources.items():
        path=root/f'{label}.c';path.write_text(text);case=evaluate(path,function,runtime,root/label,[3,7,17,33,65,129],args.clang,args.gcc,blocks,(1,4),True,True)
        if (case['optimized']!='none')!=native:raise AssertionError(f'wrong native selector proof: {label} {case["optimized"]}')
        report['cases'].append({'case':label,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**case});print(f'PASS int selector {label}: {case["optimized"]}',flush=True)
    valid=struct.pack('<II9d',1,3,4,0,0,0,9,0,0,0,16)
    failures={
      'unused-integer-local':blocked.replace('return x<y?x:y;','int ignored=(int)1e100;return x<y?x:y;'),
      'explicit-argument-overflow':blocked.replace('choose(panel + block_size,n)','choose((int)(a[0]*1e100),n)'),
      'implicit-argument-overflow':blocked.replace('choose(panel + block_size,n)','choose(a[0]*1e100,n)'),
    }
    for label,text in failures.items():
        source=root/f'{label}.c';source.write_text(text);metadata=root/f'{label}.meta';analysis=analyze(source,metadata,args.clang,'cholesky_blocked')
        if analysis['optimized']!='none':raise AssertionError('integer evaluation removed by native selector proof')
        for engine in('auto','stage','tiled','vm'):report['rejections'].append(reject(runtime,metadata,valid,root,f'{label}-{engine}',('--engine',engine)))
    report['passed']=True;report['elapsed_seconds']=time.perf_counter()-started;(root/'integer-selector-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'comparisons':sum(len(c['runs'])for c in report['cases']),'rejections':len(report['rejections']),'report':str(root/'integer-selector-report.json')}),flush=True)

if __name__=='__main__':main()
