"""TOS2 only: real C files, frozen phase1, same-bytecode legacy and decode."""
import hashlib,json,shutil,subprocess,time
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,make_input,exact_compare
from benchmark_extended import stress_input
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
FRESH=[('fresh-fma-control','''#include <math.h>
static double shifted(double x,int parity) {
  double w=parity?-0.0:0.0;
  double y=fma(x,0.5,w);
  return x<0.0?y-x:y;
}
int transform(const double *a,double *l,int n) {
  int row=0;
  while(row<n) {
    for(int col=0;col<n;++col) {
      int idx=row*n+col;
      if((row+col)%3==0)l[idx]=shifted(a[idx],(row+col)%2);
      else l[idx]=(a[idx]+0.25)-0.25;
    }
    ++row;
  }
  return 0;
}
'''),('fresh-dependent-branches','''#include <math.h>
int transform(const double *a,double *l,int n) {
  for(int idx=0;idx<n*n;++idx) {
    double v;
    if(idx%5==0)v=a[idx]*-0.0;
    else v=fabs(a[idx]);
    if(idx>0 && idx%7==0)l[idx]=l[idx-1]*0.5+v*0.25;
    else l[idx]=v;
  }
  return 0;
}
''')]
def main():
    p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-prepared-vm-phase2';root=stage/'correctness';root.mkdir(exist_ok=False)
    old=stage/'phase1-baseline.exe';runtime=p/'build-stage2-vm-tos2/cholesky_runtime.exe';shutil.copyfile(runtime,root/'runtime.exe');runtime=root/'runtime.exe'
    assert sha(old)=='bf54f13b195f26547ded80dfd225f795062cfc427e2c3d1fb299c72010a96cdc'
    snapshot=root/'source';hashes={}
    paths=[p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),Path(__file__),p/'tools/analyze_source.py',p/'tools/c_frontend.py',p/'tools/semantic_cholesky.py',p/'tools/evaluate_source.py',p/'tools/benchmark_extended.py']
    for path in paths:
        name=path.relative_to(p);target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);hashes[name.as_posix()]=sha(target)
    native=json.loads(subprocess.run([str(p/'build-stage2-vm-tos2/prepared_vm_tos2_tests.exe')],capture_output=True,text=True,check=True).stdout)
    start=time.perf_counter();report={'passed':False,'status':'running','runtime_sha256':sha(runtime),'phase1_sha256':sha(old),'source_sha256':hashes,'native_contract':native,'sources':[],'runs':[],'failures':[],'functional_only':True}
    def save():report['elapsed_seconds']=time.perf_counter()-start;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    proof=json.loads((p/'artifacts/stage2-prepared-vm-phase1/correctness/report.json').read_text());save()
    sources=[(s['label'],Path(s['analysis']['source']),s['analysis']['function'],s['label']=='int-conversion',False)for s in proof['sources']]
    for label,text in FRESH:
        source=root/(label+'.c');source.write_text(text,encoding='utf-8');sources.append((label,source,'transform',False,True))
    fp=p/'artifacts/stage2-prepared-vm-phase1/fp-supplement/source.c';sources.append(('original-fp-builtin',fp,'transform',False,True))
    for label,source,function,integer,fresh in sources:
        folder=root/label;folder.mkdir();target=folder/'source.c';shutil.copyfile(source,target);metadata=folder/'program.meta';analysis=analyze(target,metadata,'C:/Program Files/LLVM/bin/clang.exe',function);assert analysis['optimized']=='none'
        oracle=compile_oracle(target,function,folder,'E:/mingw64/bin/gcc.exe');report['sources'].append({'label':label,'fresh':fresh,'analysis':analysis,'source_sha256':sha(target),'metadata_sha256':sha(metadata),'oracle_binary_sha256':sha(oracle),'harness_sha256':sha(folder/'oracle.c')})
        sizes=[3,11,67,139,193,257]if fresh else[3,7,17,31,33,63,64,65,127,129]
        for family in (('dense','signed-zero','subnormal')if integer else('dense','signed-zero','subnormal','large','near-rank-one')):
            ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin')
            if family=='dense':make_input(ip,sizes)
            else:stress_input(ip,sizes,family)
            subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True);rows=[]
            for backend in('phase1-decoded','legacy','decoded','decoded-tos2','new-default'):
                exe=old if backend=='phase1-decoded'else runtime;mode='decoded'if backend=='phase1-decoded'else backend
                output=folder/(family+'-'+backend+'.bin');command=[str(exe),'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--threads','4']
                if mode!='new-default':command+=['--vm-backend',mode]
                begin=time.perf_counter();r=subprocess.run(command,capture_output=True,text=True,check=True);metrics=json.loads(r.stdout);assert metrics['selected_engine']=='vm' and metrics['vm_backend']==('legacy'if mode=='new-default'else mode)
                row={'source':label,'family':family,'backend':backend,'source_sha256':sha(target),'input_sha256':sha(ip),'reference_sha256':sha(ref),'wall_ms':(time.perf_counter()-begin)*1000,**metrics,**exact_compare(ref,output)};rows.append(row);report['runs'].append(row);save()
            assert len({row['vm_steps']for row in rows})==1
            print(json.dumps({'source':label,'family':family,'comparisons':len(rows),'steps':rows[0]['vm_steps']}),flush=True)
    for failure in proof['failures']:
        label=failure['source'];oldfolder=p/'artifacts/stage2-prepared-vm-phase1/correctness'/('failure-'+label);folder=root/('failure-'+label);folder.mkdir();metadata=folder/'program.meta';shutil.copyfile(oldfolder/'program.meta',metadata)
        results=[]
        for backend in('phase1-decoded','legacy','decoded','decoded-tos2'):
            output=folder/(backend+'.bin');exe=old if backend=='phase1-decoded'else runtime;mode='decoded'if backend=='phase1-decoded'else backend
            r=subprocess.run([str(exe),'--metadata',str(metadata),'--input',str(p/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin'),'--output',str(output),'--engine','auto','--vm-backend',mode],capture_output=True,text=True)
            assert r.returncode==1 and r.stderr==failure['results'][0]['stderr'] and not output.exists() and not Path(str(output)+'.partial').exists();results.append({'backend':backend,'code':r.returncode,'stderr':r.stderr})
        report['failures'].append({'source':label,'results':results});save()
    assert all(sha(p/name)==digest for name,digest in hashes.items())
    assert sha(p/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    report.update(passed=True,status='complete',comparisons=len(report['runs']));save();print(json.dumps({'passed':True,'comparisons':len(report['runs']),'sources':len(report['sources']),'elapsed_seconds':report['elapsed_seconds']}),flush=True)
if __name__=='__main__':main()
