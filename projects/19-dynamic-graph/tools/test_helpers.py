"""SSA-helper linear lowering, nested composition and unused integer checks."""
from pathlib import Path
import argparse
import json,hashlib,struct,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import evaluate
from test_project import reject

def deep_source(count):
    declarations=[];previous='x'
    for i in range(count):
        current=f't{i}';declarations.append(f'double {current}=({previous}+{previous})*0.5;');previous=current
    return 'static double h(double x){'+''.join(declarations)+f'return {previous};'+'}\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=h(a[i]);return 0;}'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=Path('build-policy/cholesky_runtime.exe'));parser.add_argument('--output-dir',type=Path,default=Path('artifacts/helper-milestone'));parser.add_argument('--gcc',default='gcc');parser.add_argument('--clang',default='clang');args=parser.parse_args()
    project=Path(__file__).resolve().parent.parent;root=args.output_dir.resolve();root.mkdir(exist_ok=True,parents=True);runtime=args.runtime.resolve();started=time.perf_counter()
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'cases':[],'rejections':[],'contract':'actual original-source separately compiled GCC strict complete files; no C oracle for undefined integer behavior'}
    sources={'deep-ssa-20':deep_source(20),'deep-ssa-40':deep_source(40),
      'same-helper-composition':'static int h(int x){return x+1;}\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=h(h(i-n));return 0;}',
      'nested-multiple-arguments':'static double h(double x,double y){return x+y+x;}\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=h(h(a[i],a[0]),h(a[0],a[i]));return 0;}',
      'ssa-branch-expression':'static double h(double x){double y=x*0.5;return y>0?y+y:-y;}\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=h(a[i]);return 0;}',
      'forward-prototype-composition':'static double h(double);\nint transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=h(h(a[i]));return 0;}\nstatic double h(double x){return x*0.5;}',
    }
    for label,text in sources.items():
        source=root/f'{label}.c';source.write_text(text,encoding='utf-8')
        begin=time.perf_counter();case=evaluate(source,'transform',runtime,root/label,[3,7,17,33],args.clang,args.gcc,(7,),(1,4),True,True)
        if case['optimized']!='none':raise AssertionError('generic helper arithmetic was incorrectly dispatched as Cholesky')
        report['cases'].append({'case':label,'end_to_end_seconds':time.perf_counter()-begin,**case});print(f'PASS helper {label}: original C, VM and all requested engines',flush=True)
    short,long=report['cases'][:2]
    if long['instructions']>2*short['instructions']or long['instructions']>1000:raise AssertionError('repeated SSA locals were expanded exponentially')
    valid=struct.pack('<II9d',1,3,4,0,0,0,9,0,0,0,16)
    official=(project/'fixtures/official_naive_transcribed.c').read_text()
    benign=root/'unused-double-cholesky.c';benign.write_text(official.replace('return x * y + z;','double ignored=x+y; return x * y + z;'))
    case=evaluate(benign,'cholesky',runtime,root/'unused-double-cholesky',[3,7,17,33],args.clang,args.gcc,(7,),(1,4),True,True)
    if case['optimized']!='none':raise AssertionError('discarded helper evaluations bypass native proof')
    report['cases'].append({'case':'unused-double-cholesky',**case})
    for label,text in {
      'cholesky-unused-integer-local':official.replace('return x * y + z;','int ignored=(x+1)*1e100; return x * y + z;'),
      'cholesky-unused-integer-argument':official.replace('double madd(double x, double y, double z)','double madd(double x, double y, double z, int ignored)').replace('madd(L[j*n+i], L[k*n+i], L[j*n+k])','madd(L[j*n+i], L[k*n+i], L[j*n+k], (int)(A[0]*1e100))'),
    }.items():
        source=root/f'{label}.c';source.write_text(text);metadata=root/f'{label}.meta';analysis=analyze(source,metadata,args.clang,'cholesky')
        if analysis['optimized']!='none':raise AssertionError('helper integer check discarded by native dispatch')
        for engine in ('auto','stage','tiled','vm'):
            report['rejections'].append(reject(runtime,metadata,valid,root,f'{label}-{engine}',('--engine',engine)))
    for label,text in {
      'unused-argument-overflow':'static double h(int ignored,double x){return x;}\nint transform(const double*a,double*l,int n){l[0]=h((int)(a[0]*1e100),a[0]);return 0;}',
      'unused-local-overflow':'static double h(double x){int ignored=x*1e100;return x;}\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',
    }.items():
        source=root/f'{label}.c';source.write_text(text,encoding='utf-8');metadata=root/f'{label}.meta';analyze(source,metadata,args.clang,'transform')
        report['rejections'].append(reject(runtime,metadata,valid,root,label,('--engine','vm')))
    for label,text in {
      'actual-helper-recursion':'static double h(double x){return h(x);}\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',
      'nonfinite-literal':'int transform(const double*a,double*l,int n){l[0]=1e309;return 0;}',
      'float-helper-return':'static float h(double x){return x;}\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',
      'unsigned-helper-return':'static unsigned h(double x){return x;}\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',
      'wide-helper-return':'static long long h(double x){return x;}\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',
      'integer-builtin-return':'extern int sqrt(double);\nint transform(const double*a,double*l,int n){l[0]=sqrt(a[0]);return 0;}',
      'float-builtin-argument':'extern double fabs(float);\nint transform(const double*a,double*l,int n){l[0]=fabs(a[0]);return 0;}',
    }.items():
        source=root/f'{label}.c';source.write_text(text,encoding='utf-8')
        try:analyze(source,root/f'{label}.meta',args.clang,'transform')
        except ValueError as error:report['rejections'].append({'case':label,'rejected':True,'message':str(error)})
        else:raise AssertionError('unsupported source accepted')
    report['passed']=True;report['elapsed_seconds']=time.perf_counter()-started
    (root/'helper-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'comparisons':sum(len(case['runs'])for case in report['cases']),'rejections':len(report['rejections']),'linear_ssa_instructions':[short['instructions'],long['instructions']],'report':str(root/'helper-report.json')}),flush=True)

if __name__=='__main__':main()
