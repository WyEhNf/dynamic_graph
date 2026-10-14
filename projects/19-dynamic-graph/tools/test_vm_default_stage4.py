"""Default integration: unchanged frozen C corpus, six real executable modes."""
import hashlib,json,shutil,subprocess,time
from pathlib import Path
from evaluate_source import exact_compare
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def main():
    p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-default-integration';root=stage/'correctness';root.mkdir(exist_ok=False)
    prior=p/'artifacts/stage2-prepared-vm-phase3';proof=json.loads((prior/'correctness/report.json').read_text());assert proof['passed']
    snapshot=root/'source';hashes={}
    for x in [p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),Path(__file__),p/'tools/evaluate_source.py']:
        name=x.relative_to(p).as_posix();target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);hashes[name]=sha(target)
    for build,name in [('build-stage2-vm-default','runtime.exe'),('build-stage2-vm-default-portable','portable.exe')]:shutil.copyfile(p/build/'cholesky_runtime.exe',root/name)
    backends={'ordinary4f73':stage/'ordinary4f73.exe','new-default':root/'runtime.exe','decoded-threaded':root/'runtime.exe','decoded':root/'runtime.exe','legacy':root/'runtime.exe','portable-default':root/'portable.exe'}
    report={'passed':False,'status':'running','functional_only':True,'phase3_corpus_sha256':sha(prior/'correctness/report.json'),'source_sha256':hashes,'backends':{k:{'exe':str(v),'sha256':sha(v)}for k,v in backends.items()},'sources':[],'runs':[],'failures':[]};start=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-start;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    for source in proof['sources']:
        label=source['label'];folder=root/label;folder.mkdir();old=prior/'correctness'/label
        for name,digest in [('source.c',source['source_sha256']),('program.meta',source['metadata_sha256']),('oracle.c',source['harness_sha256']),('oracle.exe',source['oracle_binary_sha256'])]:
            assert sha(old/name)==digest;shutil.copyfile(old/name,folder/name)
        entry=dict(source);entry.update(source=str(folder/'source.c'),metadata=str(folder/'program.meta'));report['sources'].append(entry)
        for reference in [r for r in proof['runs']if r['source']==label and r['backend']=='decoded']:
            ip=Path(reference['input']);ref=Path(reference['reference']);metadata=folder/'program.meta';rows=[]
            for backend,exe in backends.items():
                assert sha(ip)==reference['input_sha256']and sha(ref)==reference['reference_sha256']and sha(metadata)==source['metadata_sha256']and sha(exe)==report['backends'][backend]['sha256']
                output=folder/(reference['family']+'-'+backend+'.bin');command=[str(exe),'--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--threads','4']
                if backend in ['decoded-threaded','decoded','legacy']:command+=['--vm-backend',backend]
                began=time.perf_counter();proc=subprocess.run(command,capture_output=True,text=True,check=True);metrics=json.loads(proc.stdout)
                assert metrics['selected_engine']=='vm'
                if backend=='ordinary4f73':assert 'vm_backend'not in metrics
                else:assert metrics['vm_backend']==('decoded-fallback'if backend=='portable-default'else'decoded-threaded'if backend=='new-default'else backend)and metrics['vm_steps']==reference['vm_steps']
                row={'source':label,'family':reference['family'],'backend':backend,'output':str(output),'metadata':str(metadata),'input':str(ip),'reference':str(ref),'source_sha256':source['source_sha256'],'metadata_sha256':source['metadata_sha256'],'input_sha256':reference['input_sha256'],'reference_sha256':reference['reference_sha256'],'wall_ms':(time.perf_counter()-began)*1000,**metrics,**exact_compare(ref,output)};report['runs'].append(row);rows.append(row);save()
            print(json.dumps({'source':label,'family':reference['family'],'comparisons':len(rows),'default':'decoded-threaded','portable_default':'decoded-fallback'}),flush=True)
    failure_input=p/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin';report['failure_input_sha256']=sha(failure_input)
    for failure in proof['failures']:
        label=failure['source'];folder=root/('failure-'+label);folder.mkdir();metadata=folder/'program.meta';shutil.copyfile(Path(failure['metadata']),metadata);results=[]
        assert sha(metadata)==failure['metadata_sha256']
        for backend,exe in backends.items():
            output=folder/(backend+'.bin');command=[str(exe),'--metadata',str(metadata),'--input',str(failure_input),'--output',str(output),'--engine','auto']
            if backend in ['decoded-threaded','decoded','legacy']:command+=['--vm-backend',backend]
            proc=subprocess.run(command,capture_output=True,text=True);assert proc.returncode==1 and proc.stderr==failure['results'][0]['stderr']and not output.exists()and not Path(str(output)+'.partial').exists()
            results.append({'backend':backend,'exit_code':proc.returncode,'stderr':proc.stderr})
        report['failures'].append({'source':label,'results':results,'metadata':str(metadata),'metadata_sha256':sha(metadata)});save()
    assert all(sha(p/name)==digest for name,digest in hashes.items())
    assert sha(p/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    report.update(passed=True,status='complete',comparisons=len(report['runs']));save();print(json.dumps({'passed':True,'comparisons':len(report['runs']),'sources':len(report['sources']),'elapsed_seconds':report['elapsed_seconds']}),flush=True)
if __name__=='__main__':main()
