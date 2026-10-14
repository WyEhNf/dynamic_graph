"""Full actual-C checks; frozen old cases plus a new source/shape holdout."""
import hashlib,json,shutil,subprocess,time
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,make_input,exact_compare
from benchmark_extended import stress_input
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
HOLDOUT='''#include <math.h>
static double blend(double x,double carry,int parity) {
  return parity?fma(x,0.75,carry):(x*0.75)+carry;
}
int transform(const double *a,double *l,int n) {
  int row=0;
  while(row<n) {
    double carry=-0.0;
    for(int col=0;col<n;++col) {
      int idx=row*n+col;
      double v=blend(a[idx],carry,(row+col)%2);
      if(col%4==0)carry=v*0.125;
      else carry=col%3==0?-0.0:0.0;
      l[idx]=idx>0 && col%7==0?v+l[idx-1]*0.25:v;
    }
    ++row;
  }
  return 0;
}
'''
def main():
    p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-prepared-vm-phase3';root=stage/'correctness';root.mkdir(exist_ok=False)
    small=json.loads((stage/'small-contract-manifest.json').read_text());proof=json.loads((p/'artifacts/stage2-prepared-vm-phase2/correctness/report.json').read_text());start=time.perf_counter()
    backend_exes={'phase1-decoded':stage/'phase1-baseline.exe','legacy':stage/'candidate.exe','decoded':stage/'candidate.exe','decoded-threaded':stage/'candidate.exe','portable-threaded':stage/'portable-candidate.exe','new-default':stage/'candidate.exe'}
    assert sha(backend_exes['phase1-decoded'])=='bf54f13b195f26547ded80dfd225f795062cfc427e2c3d1fb299c72010a96cdc'
    assert sha(stage/'candidate.exe')==small['executable_sha256']['candidate.exe'] and sha(stage/'portable-candidate.exe')==small['executable_sha256']['portable-candidate.exe']
    report={'passed':False,'status':'running','functional_only':True,'small_manifest_sha256':sha(stage/'small-contract-manifest.json'),'backends':{k:{'exe':str(v),'sha256':sha(v)}for k,v in backend_exes.items()},'sources':[],'runs':[],'failures':[],'cached_phase2_report_sha256':sha(p/'artifacts/stage2-prepared-vm-phase2/correctness/report.json'),'old_source_count':12,'fresh_source_count':1,'fresh_shapes':[5,19,71,131,211,263]}
    def save():report['elapsed_seconds']=time.perf_counter()-start;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def family_run(label,family,source,metadata,ip,ref,expected_steps=None):
        rows=[];source_sha=sha(source);meta_sha=sha(metadata);input_sha=sha(ip);ref_sha=sha(ref)
        for backend,exe in backend_exes.items():
            assert sha(source)==source_sha and sha(metadata)==meta_sha and sha(ip)==input_sha and sha(ref)==ref_sha
            assert sha(exe)==report['backends'][backend]['sha256']
            mode='decoded'if backend=='phase1-decoded'else'decoded-threaded'if backend=='portable-threaded'else backend
            output=root/label/(family+'-'+backend+'.bin');command=[str(exe),'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--threads','4']
            if backend!='new-default':command+=['--vm-backend',mode]
            begin=time.perf_counter();r=subprocess.run(command,capture_output=True,text=True,check=True);metrics=json.loads(r.stdout)
            effective='decoded-fallback'if backend=='portable-threaded'else'legacy'if backend=='new-default'else mode
            assert metrics['selected_engine']=='vm'and metrics['vm_backend']==effective
            if expected_steps is not None:assert metrics['vm_steps']==expected_steps
            row={'source':label,'family':family,'backend':backend,'output':str(output),'metadata':str(metadata),'input':str(ip),'reference':str(ref),'source_sha256':source_sha,'metadata_sha256':meta_sha,'input_sha256':input_sha,'reference_sha256':ref_sha,'wall_ms':(time.perf_counter()-begin)*1000,**metrics,**exact_compare(ref,output)}
            report['runs'].append(row);rows.append(row);save()
        assert len({r['vm_steps']for r in rows})==1
        print(json.dumps({'source':label,'family':family,'comparisons':len(rows),'steps':rows[0]['vm_steps']}),flush=True)
    save()
    for entry in proof['sources']:
        label=entry['label'];old=p/'artifacts/stage2-prepared-vm-phase2/correctness'/label;folder=root/label;folder.mkdir()
        for name,digest in [('source.c',entry['source_sha256']),('program.meta',entry['metadata_sha256']),('oracle.exe',entry['oracle_binary_sha256']),('oracle.c',entry['harness_sha256'])]:
            assert sha(old/name)==digest,(label,name);shutil.copyfile(old/name,folder/name)
        copied=dict(entry);copied.update(fresh_source=False,fresh_shape=False,cached_actual_C=True,cached_original_directory=str(old),source=str(folder/'source.c'),metadata=str(folder/'program.meta'));report['sources'].append(copied)
        families=[r for r in proof['runs']if r['source']==label and r['backend']=='phase1-decoded']
        for row in families:
            family=row['family'];ip=old/(family+'-input.bin');ref=old/(family+'-oracle.bin')
            assert sha(ip)==row['input_sha256'] and sha(ref)==row['reference_sha256']
            family_run(label,family,folder/'source.c',folder/'program.meta',ip,ref,row['vm_steps'])
    label='fresh-carry-fma-plain';folder=root/label;folder.mkdir();source=folder/'source.c';source.write_text(HOLDOUT,encoding='utf-8');metadata=folder/'program.meta'
    analysis=analyze(source,metadata,'C:/Program Files/LLVM/bin/clang.exe','transform');assert analysis['optimized']=='none'
    oracle=compile_oracle(source,'transform',folder,'E:/mingw64/bin/gcc.exe')
    report['sources'].append({'label':label,'analysis':analysis,'fresh_source':True,'fresh_shape':True,'cached_actual_C':False,'source':str(source),'metadata':str(metadata),'source_sha256':sha(source),'metadata_sha256':sha(metadata),'oracle_binary_sha256':sha(oracle),'harness_sha256':sha(folder/'oracle.c')})
    for family in ['dense','signed-zero','subnormal','large','near-rank-one']:
        ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin')
        if family=='dense':make_input(ip,report['fresh_shapes'])
        else:stress_input(ip,report['fresh_shapes'],family)
        subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
        family_run(label,family,source,metadata,ip,ref)
    failure_input=p/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin';report['failure_input_sha256']=sha(failure_input)
    for failure in proof['failures']:
        label=failure['source'];folder=root/('failure-'+label);folder.mkdir();metadata=folder/'program.meta';shutil.copyfile(p/'artifacts/stage2-prepared-vm-phase2/correctness'/('failure-'+label)/'program.meta',metadata);results=[]
        for backend,exe in backend_exes.items():
            output=folder/(backend+'.bin');mode='decoded'if backend=='phase1-decoded'else'decoded-threaded'if backend=='portable-threaded'else backend
            command=[str(exe),'--metadata',str(metadata),'--input',str(failure_input),'--output',str(output),'--engine','auto']
            if backend!='new-default':command+=['--vm-backend',mode]
            r=subprocess.run(command,capture_output=True,text=True);assert r.returncode==1 and r.stderr==failure['results'][0]['stderr'] and not output.exists()and not Path(str(output)+'.partial').exists()
            results.append({'backend':backend,'code':r.returncode,'stderr':r.stderr})
        report['failures'].append({'source':label,'results':results,'metadata':str(metadata),'metadata_sha256':sha(metadata)});save()
    assert all(sha(p/name)==digest for name,digest in small['source_sha256'].items())
    assert sha(p/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    report.update(passed=True,status='complete',comparisons=len(report['runs']));save();print(json.dumps({'passed':True,'comparisons':len(report['runs']),'sources':len(report['sources']),'elapsed_seconds':report['elapsed_seconds']}),flush=True)
if __name__=='__main__':main()
