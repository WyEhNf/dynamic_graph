"""Isolated policy: all frozen C groups and fresh actual-C holdouts, no perf."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,exact_compare,make_input

P=Path(__file__).resolve().parents[1]
OUT=P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness'
ORDINARY='99a87d135378406a15efd930d58941291683ca799f91bd5dcc0ca77ceadef448'
MEMORY='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=False)
    temp=P/'artifacts/stage2-vm-proved-budget/compiler-temp';temp.mkdir(exist_ok=True)
    os.environ.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
    assert shutil.disk_usage(P).free>=256*1024*1024
    gnu=P/'build-stage2-vm-proved-budget/cholesky_runtime.exe'
    portable=P/'build-stage2-vm-proved-budget-portable/cholesky_runtime.exe'
    disabled=P/'build-stage2-vm-proved-budget-disabled/cholesky_runtime.exe'
    binaries={'gnu':gnu,'portable':portable,'disabled':disabled}
    exe_hashes={k:sha(v)for k,v in binaries.items()}
    prior=P/'artifacts/stage2-prepared-vm-phase3/correctness'
    corpus=json.loads((prior/'report.json').read_text(encoding='utf-8'));assert corpus['passed']
    modes={'fixed-auto':(gnu,['--vm-budget','fixed']),
           'proved-auto':(gnu,['--vm-budget','proved']),
           'proved-legacy':(gnu,['--vm-budget','proved','--vm-backend','legacy']),
           'proved-decoded':(gnu,['--vm-budget','proved','--vm-backend','decoded']),
           'proved-tos2':(gnu,['--vm-budget','proved','--vm-backend','decoded-tos2']),
           'proved-threaded':(gnu,['--vm-budget','proved','--vm-backend','decoded-threaded']),
           'portable-proved':(portable,['--vm-budget','proved'])}
    report={'passed':False,'status':'running','functional_only':True,'maximum_execution_started':False,
            'corpus_sha256':sha(prior/'report.json'),'binaries':{k:{'path':str(v),'sha256':exe_hashes[k]}for k,v in binaries.items()},
            'process_env':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']},'runs':[],'sources':[],'failures':[],'cli':[]}
    started=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-started;(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def runtimes(label,family,metadata,ip,ref,expected_steps=None,block=32):
        mh,ih,rh=sha(metadata),sha(ip),sha(ref)
        for mode,(exe,flags)in modes.items():
            target=OUT/label/(family+'-'+mode+'.bin');target.parent.mkdir(exist_ok=True)
            command=[str(exe),'--metadata',str(metadata),'--input',str(ip),'--output',str(target),'--engine','auto','--threads','4','--block-size',str(block),*flags]
            began=time.perf_counter();proc=subprocess.run(command,capture_output=True,text=True)
            (target.with_suffix('.stdout')).write_text(proc.stdout,encoding='utf-8');(target.with_suffix('.stderr')).write_text(proc.stderr,encoding='utf-8')
            assert proc.returncode==0,(label,family,mode,proc.stderr)
            metrics=json.loads(proc.stdout);assert metrics['selected_engine']=='vm'
            if expected_steps is not None:assert metrics['vm_steps']==expected_steps
            assert metrics['vm_budget_mode']==('fixed'if mode=='fixed-auto'else'proved')
            assert metrics['vm_effective_step_limit_max']>=1000000000
            if mode=='fixed-auto':assert metrics['vm_budget_work']==0 and metrics['vm_budget_proof_ms']==0
            else:assert metrics['vm_budget_proved_matrices']+metrics['vm_budget_unknown_matrices']==metrics['matrices']
            if mode=='portable-proved':assert metrics['vm_backend']=='decoded-fallback'
            row={'source':label,'family':family,'mode':mode,'output':str(target),'metadata':str(metadata),'input':str(ip),'reference':str(ref),'metadata_sha256':mh,'input_sha256':ih,'reference_sha256':rh,'command':command,'exit_code':proc.returncode,'wall_ms':(time.perf_counter()-began)*1000,**metrics,**exact_compare(ref,target)}
            report['runs'].append(row);save()
        assert sha(metadata)==mh and sha(ip)==ih and sha(ref)==rh
        print(json.dumps({'source':label,'family':family,'modes':len(modes),'full_bytes':True}),flush=True)
    save()
    for source in corpus['sources']:
        label=source['label'];folder=OUT/label;folder.mkdir();old=prior/label
        for name,digest in [('source.c',source['source_sha256']),('program.meta',source['metadata_sha256']),('oracle.c',source['harness_sha256']),('oracle.exe',source['oracle_binary_sha256'])]:
            assert sha(old/name)==digest;shutil.copyfile(old/name,folder/name)
        report['sources'].append({**source,'fresh_source':False,'folder':str(folder)})
        for reference in[r for r in corpus['runs']if r['source']==label and r['backend']=='decoded']:
            assert sha(reference['input'])==reference['input_sha256']and sha(reference['reference'])==reference['reference_sha256']
            runtimes(label,reference['family'],folder/'program.meta',Path(reference['input']),Path(reference['reference']),reference['vm_steps'])
    fresh={
      'heldout-stride2':'''#include <math.h>
static double twist(double x){return x<0?-x:x*0.5-0.0;}
int finite_stride(double* a,double* l,int n){int nn=n*n;for(int k=1;k<nn;k+=2)l[k]=twist(a[k]);return 0;}
''',
      'heldout-disjoint':'''#include <math.h>
int finite_disjoint(double* a,double* l,int n){int nn=n*n;for(int k=0;k<nn;k+=3)l[k]=a[k]*0.75;for(int j=2;j<nn;j+=3)l[j]=fma(a[j],0.5,-0.0);return 0;}
'''}
    for label,text in fresh.items():
        folder=OUT/label;folder.mkdir();source=folder/'source.c';source.write_text(text,encoding='utf-8');metadata=folder/'program.meta'
        function='finite_stride'if label=='heldout-stride2'else'finite_disjoint'
        analysis=analyze(source,metadata,'C:/Program Files/LLVM/bin/clang.exe',function);assert analysis['optimized']=='none'
        oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe')
        report['sources'].append({'label':label,'fresh_source':True,'function':function,'source_sha256':sha(source),'metadata_sha256':sha(metadata),'harness_sha256':sha(folder/'oracle.c'),'oracle_binary_sha256':sha(oracle),'sizes':[7,13,29,53],'folder':str(folder)})
        for family,diagonal,signed in [('dense',False,False),('signedzero',True,True)]:
            ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin');make_input(ip,[7,13,29,53],diagonal=diagonal,signed_zero=signed)
            proc=subprocess.run([str(oracle),str(ip),str(ref),'32'],capture_output=True,text=True);assert proc.returncode==0
            runtimes(label,family,metadata,ip,ref)
    failure_input=P/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin'
    for failure in corpus['failures']:
        label=failure['source'];folder=OUT/('failure-'+label);folder.mkdir();metadata=folder/'program.meta';shutil.copyfile(failure['metadata'],metadata);assert sha(metadata)==failure['metadata_sha256']
        results=[]
        for mode,(exe,flags)in modes.items():
            target=folder/(mode+'.bin');command=[str(exe),'--metadata',str(metadata),'--input',str(failure_input),'--output',str(target),*flags]
            proc=subprocess.run(command,capture_output=True,text=True)
            assert proc.returncode==1 and proc.stderr==failure['results'][0]['stderr']and not target.exists()and not Path(str(target)+'.partial').exists()
            results.append({'mode':mode,'command':command,'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
        report['failures'].append({'source':label,'metadata':str(metadata),'metadata_sha256':sha(metadata),'input_sha256':sha(failure_input),'results':results});save()
    for flags,error in[
        (['--vm-budget','proved','--vm-step-limit','1000000000'],'proved VM budget cannot combine with an explicit VM step limit'),
        (['--vm-step-limit','1000000000','--vm-budget','proved'],'proved VM budget cannot combine with an explicit VM step limit'),
        (['--vm-budget','proved','--vm-step-limit','10000000000'],'proved VM budget cannot combine with an explicit VM step limit'),
        (['--vm-budget','bad'],'VM budget mode must be fixed or proved'),
        (['--vm-budget','fixed','--vm-step-limit','1000000000'],'input, output and metadata are required')]:
        proc=subprocess.run([str(gnu),*flags],capture_output=True,text=True);assert proc.returncode==1 and proc.stderr=='error: '+error+'\n';report['cli'].append({'exe':str(gnu),'flags':flags,'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
    proc=subprocess.run([str(disabled),'--vm-budget','proved'],capture_output=True,text=True);assert proc.returncode==1 and proc.stderr=='error: proved VM budget is disabled in this build\n';report['cli'].append({'exe':str(disabled),'flags':['--vm-budget','proved'],'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
    for name,exe in binaries.items():
        proc=subprocess.run([str(exe),'--help'],capture_output=True,text=True);assert proc.returncode==0 and (('fixed|proved'in proc.stdout)==(name!='disabled'));report['cli'].append({'exe':str(exe),'flags':['--help'],'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
    assert all(sha(v)==exe_hashes[k]for k,v in binaries.items())and sha(P/'build/cholesky_runtime.exe')==ORDINARY and sha(P/'build-memory/cholesky_runtime.exe')==MEMORY
    report.update(passed=True,status='complete',whole_c_comparisons=len(report['runs']),ordinary_runtime_unchanged=True,memory_runtime_unchanged=True)
    save();print(json.dumps({'passed':True,'whole_C':len(report['runs']),'sources':len(report['sources']),'report_sha256':sha(OUT/'report.json'),'maximum_execution_started':False}),flush=True)
if __name__=='__main__':main()
