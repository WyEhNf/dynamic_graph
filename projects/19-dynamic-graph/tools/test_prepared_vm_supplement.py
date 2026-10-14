"""Independent FP C oracle and sequential maximum-shape VM resource contract."""
import argparse,hashlib,json,shutil,struct,subprocess,time
from array import array
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,exact_compare
from windows_resource_probe import monitored_run
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
FP='''#include <math.h>
int transform(double *a,double *l,int n) {
  for(int i=0;i<n*n;++i) {
    if(i%8==0) l[i]=fma(1.000000007450580596923828125,0.999999992549419403076171875,-1.0);
    else if(i%8==1) { double x=1.000000007450580596923828125*0.999999992549419403076171875; l[i]=x-1.0; }
    else if(i%8==2) l[i]=a[i]*1.0;
    else if(i%8==3) l[i]=2.2250738585072014e-308*0.5;
    else if(i%8==4) l[i]=fabs(a[i]);
    else if(i%8==5) l[i]=sqrt(4.0);
    else if(i%8==6) l[i]=fmin(a[i],0.0);
    else l[i]=fmax(a[i],0.0);
  }
  return 0;
}
'''
COPY='''int transform(double *a,double *l,int n) {
  int i=0;
  while(i<n*n) { l[i]=a[i]; ++i; }
  return 0;
}
'''
def free_kib():
    r=subprocess.run(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory'],capture_output=True,text=True,check=True)
    return int(r.stdout.strip())
def inputs(path,sizes):
    pattern=[-0.0,0.0,5e-324,-5e-324,2.2250738585072014e-308,-2.2250738585072014e-308,1.5,-3.0]
    with path.open('wb')as f:
        f.write(struct.pack('<I',len(sizes)))
        for n in sizes:
            f.write(struct.pack('<I',n));row=array('d',(pattern[j%8]for j in range(n)))
            for _ in range(n):f.write(row.tobytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--maximum',action='store_true');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--run-prepared',action='store_true');args=ap.parse_args()
    if args.run_prepared and (not args.maximum or args.prepare_only):ap.error('--run-prepared requires --maximum and cannot combine with --prepare-only')
    project=Path(__file__).resolve().parents[1];stage=project/'artifacts/stage2-prepared-vm-phase1'
    root=stage/('maximum-shape'if args.maximum else'fp-supplement')
    if args.run_prepared:
        assert root.is_dir() and not (root/'report.json').exists(),'no rerun of an existing execution report'
        assert sha(root/'test-script.py')==sha(Path(__file__)),'prepared script changed'
    else:
        root.mkdir(exist_ok=False);(root/'test-script.py').write_bytes(Path(__file__).read_bytes())
    runtime=stage/'candidate.exe';old=stage/'ordinary-baseline.exe'
    manifest=json.loads((stage/'phase1-manifest.json').read_text());assert sha(runtime)==manifest['candidate_sha256'] and sha(old)==manifest['ordinary_sha256']
    plan={'status':'predeclared','source':COPY if args.maximum else FP,'sizes':[10000]if args.maximum else[3,7,65,129],'budget':10000000000 if args.maximum else 1000000000,'backends':['ordinary4f73','legacy','decoded','new-default'],'execution':'strictly sequential C then each backend; no shared process matrices; one candidate output retained per backend','minimum_free_kib':2621440 if args.maximum else 0,'whole_file_contract':True,'functional_only':True,'candidate_sha256':sha(runtime),'ordinary_sha256':sha(old),'script_sha256':sha(root/'test-script.py')}
    if args.run_prepared:assert json.loads((root/'plan.json').read_text())==plan,'frozen plan changed'
    else:(root/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    if args.prepare_only:
        print(json.dumps({'predeclared':True,'plan':str(root/'plan.json'),'free_memory_kib':free_kib(),'performance_started':False}));return
    if args.maximum and free_kib()<plan['minimum_free_kib']:raise RuntimeError('insufficient free RAM for declared full N10000 run; plan preserved, no input/test started')
    source=root/'source.c';source.write_text(plan['source'],encoding='utf-8');metadata=root/'program.meta'
    analysis=analyze(source,metadata,'C:/Program Files/LLVM/bin/clang.exe','transform');assert analysis['optimized']=='none'
    oracle=compile_oracle(source,'transform',root,'E:/mingw64/bin/gcc.exe')
    ip=root/'input.bin';inputs(ip,plan['sizes']);ref=root/'oracle.bin'
    report={'passed':False,'status':'running','plan':plan,'analysis':analysis,'source_sha256':sha(source),'metadata_sha256':sha(metadata),'oracle_binary_sha256':sha(oracle),'oracle_harness_sha256':sha(root/'oracle.c'),'input_sha256':sha(ip),'runs':[]}
    def save():(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save();start=time.perf_counter();result,resources=monitored_run([str(oracle),str(ip),str(ref),'7']);report['oracle']={'wall_ms':(time.perf_counter()-start)*1000,**resources};report['oracle_output_sha256']=sha(ref);save()
    print(json.dumps({'original_C_complete':True,'resources':resources}),flush=True)
    if not args.maximum:
        # Independent source expression goldens, in addition to actual C oracle.
        with ref.open('rb')as f:f.read(8);head=struct.unpack('<8Q',f.read(64))
        assert head[0]==0xbc90000000000000 and head[1]==0 and head[3]==0x0008000000000000 and head[5]==0x4000000000000000
        report['independent_expression_bitgold']=[hex(x)for x in head]
    for backend in plan['backends']:
        available=free_kib()
        if args.maximum and available<plan['minimum_free_kib']:raise RuntimeError('free RAM below frozen minimum before '+backend)
        output=root/(backend+'.bin');exe=old if backend=='ordinary4f73'else runtime
        command=[str(exe),'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--vm-step-limit',str(plan['budget'])]
        if backend in('legacy','decoded'):command+=['--vm-backend',backend]
        start=time.perf_counter();run,resources=monitored_run(command);metrics=json.loads(run.stdout);assert metrics['selected_engine']=='vm'
        record={'backend':backend,'free_memory_before_kib':available,'wall_ms':(time.perf_counter()-start)*1000,**resources,**metrics,**exact_compare(ref,output)}
        if backend!='ordinary4f73':assert metrics['vm_backend']==('decoded'if backend=='decoded'else'legacy')
        report['runs'].append(record);save();print(json.dumps({'backend':backend,'byte_identical':True,'bytes':record['bytes'],'resources':resources}),flush=True)
    assert report['runs'][1]['vm_steps']==report['runs'][2]['vm_steps']==report['runs'][3]['vm_steps']
    assert sha(runtime)==manifest['candidate_sha256'] and sha(project/'build/cholesky_runtime.exe')==manifest['ordinary_sha256']
    report.update(passed=True,status='complete');save();print(json.dumps({'passed':True,'report':str(root/'report.json')}),flush=True)
if __name__=='__main__':main()
