"""Sequential isolated builds/CTest/CLI gates; file stdio, no automatic retry."""
import argparse,ctypes,hashlib,json,os,re,shutil,struct,sys,time,traceback
from pathlib import Path
from windows_file_resource_probe_stage2 import HostMemory,monitored_run

P=Path(__file__).resolve().parents[1]
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
ONE=1073741824
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def resources():
    memory=HostMemory();memory.dwLength=ctypes.sizeof(memory)
    if not ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx(ctypes.byref(memory)):raise ctypes.WinError(ctypes.get_last_error())
    return {'available_ram_bytes':memory.ullAvailPhys,'G_free_bytes':shutil.disk_usage(R).free,'required_each_bytes':ONE}
def prepare():
    destination=R/'build-gate-plan';assert not destination.exists();destination.mkdir()
    shutil.copyfile(Path(__file__),destination/'runner.py')
    helper=Path(__file__).with_name('windows_file_resource_probe_stage2.py')
    shutil.copyfile(helper,destination/helper.name)
    meta=P/'artifacts/stage2-vm-nested-budget/execution-static-design-v2/programs/unused-double/program.meta'
    shutil.copyfile(meta,destination/'cli.meta')
    (destination/'cli.input').write_bytes(struct.pack('<II9d',1,3,4,0,0,0,9,0,0,0,16))
    commands=read(R/'review-supplement/review.json')['future_commands']
    for label,command in commands.items():
        command['configure']+=['-DPython3_EXECUTABLE=F:/Hackathon/projects/19-dynamic-graph/.venv/Scripts/python.exe',
                               '-DCHOL_CLANG_EXECUTABLE=C:/Program Files/LLVM/bin/clang.exe']
        command['ctest']=['C:/Program Files (x86)/CMake/bin/ctest.exe','--test-dir',str(R/('build-'+label)),'-V','--output-on-failure','--parallel','1']
    plan={'schema':'isolated-load-pair-build-contract-plan-v1','source_manifest_sha256':sha(R/'manifest.json'),
          'review_manifest_sha256':sha(R/'review-supplement/manifest.json'),'commands':commands,
          'order':['gnu','portable','disabled'],'RAM_and_G_fresh_gate_bytes':ONE,
          'environment':{**{x:str(R/'compiler-temp')for x in ['TEMP','TMP','TMPDIR']},'PATH_prefix':'E:/mingw64/bin'},
          'contract_expectation':{'enabled_original_comparisons':934,'enabled_new_groups':15,'enabled_new_prefix':8369,
                                  'enabled_new_extras':80,'enabled_new_comparisons':8464,'enabled_CTest_count':15,'disabled_CTest_count':14},
          'cli_checks':['GNU explicit fused','portable explicit fused reports decoded-fallback/portable-fallback',
                        'GNU/portable explicit legacy complete bytes equality','disabled explicit backend rejects before output',
                        'GNU/portable default auto unchanged/no fusion'],
          'forbidden':['fullC beyond existing CTest','perf','maximum shape','default promotion','retry','old baseline library link'],
          'source_files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size}for p in destination.iterdir()if p.is_file()},
          'resource_at_prepare':resources()}
    write(destination/'plan.json',plan)
    print(json.dumps({'prepared':True,'plan':str(destination/'plan.json'),'sha256':sha(destination/'plan.json')}),flush=True)
def run():
    directory=R/'build-gate-evidence';assert not directory.exists();directory.mkdir()
    plan=read(R/'build-gate-plan/plan.json')
    assert sha(R/'manifest.json')==plan['source_manifest_sha256']
    for path,entry in read(R/'manifest.json')['frozen_files'].items():assert sha(R/path)==entry['sha256'],path
    for path,entry in plan['source_files'].items():assert sha(R/'build-gate-plan'/path)==entry['sha256'],path
    (R/'compiler-temp').mkdir(exist_ok=True)
    for key,value in plan['environment'].items():
        if key!='PATH_prefix':os.environ[key]=value
    os.environ['PATH']=plan['environment']['PATH_prefix']+os.pathsep+os.environ.get('PATH','')
    report={'schema':'isolated-load-pair-build-contract-actual-v1','passed':False,'owner_PID':os.getpid(),
            'plan_sha256':sha(R/'build-gate-plan/plan.json'),'environment':plan['environment'],'records':[],'builds':{},'cli':[]}
    write(directory/'report.json',report)
    print(json.dumps({'actual_owner_PID':os.getpid(),'evidence':str(directory),'run_started':True}),flush=True)
    def launch(label,command,expected=0):
        resource=resources();row={'label':label,'command':command,'before':resource,'expected_exitcode':expected}
        report['records'].append(row);write(directory/'report.json',report)
        if min(resource['available_ram_bytes'],resource['G_free_bytes'])<ONE:
            row['resource_gate_passed']=False;write(directory/'report.json',report);raise SystemExit(75)
        row['resource_gate_passed']=True
        stdout=directory/(label+'.stdout');stderr=directory/(label+'.stderr')
        row.update({'raw_stdout':str(stdout),'raw_stderr':str(stderr)})
        print(json.dumps({'launch':label,'command':command,'fresh':resource}),flush=True)
        start=time.perf_counter();completed,metric=monitored_run(command,stdout,stderr,check=False)
        row.update({'actual_exitcode':completed.returncode,'wall_ms':(time.perf_counter()-start)*1000,'resource':metric,
                    'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)})
        write(directory/'report.json',report)
        print(json.dumps({'terminal':label,'exitcode':completed.returncode,'wall_ms':row['wall_ms']}),flush=True)
        assert completed.returncode==expected,(label,completed.returncode,completed.stderr[-1000:])
        return completed
    try:
        for label in plan['order']:
            commands=plan['commands'][label]
            assert not (R/('build-'+label)).exists(),'new build must be fresh'
            launch(label+'-configure',commands['configure']);launch(label+'-build',commands['build'])
            build=R/('build-'+label)
            files={p.relative_to(build).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
                   for p in build.rglob('*')if p.is_file()and(p.suffix in ['.exe','.a','.make','.rsp']or p.name in ['CMakeCache.txt','link.txt','CTestTestfile.cmake'])}
            report['builds'][label]={'artifacts':files,'new_header_sha256':sha(R/'workspace/include/cholesky/runtime.hpp')}
            completed=launch(label+'-ctest',commands['ctest'])
            count=15 if label!='disabled'else 14
            assert re.search(r'100% tests passed, 0 tests failed out of '+str(count)+r'\b',completed.stdout),(label,'CTest denominator')
            if label!='disabled':
                assert re.search(r'"original_groups":15,"prefix_cases":8369,"extra_cases":80,"comparisons":8464',completed.stdout),(label,'new denominator')
            assert '"comparisons":934' in completed.stdout,(label,'old934 denominator')
            exe=build/'cholesky_runtime.exe';base=[str(exe),'--metadata',str(R/'build-gate-plan/cli.meta'),
                                               '--input',str(R/'build-gate-plan/cli.input'),'--engine','vm','--simd','portable']
            outputs={}
            for mode in (['legacy','auto','decoded-threaded-load-pair']if label!='disabled'else ['decoded-threaded-load-pair']):
                output=directory/(label+'-'+mode+'.bin');command=base+['--output',str(output),'--vm-backend',mode]
                item={'build':label,'backend':mode,'output':str(output)}
                report['cli'].append(item)
                if label=='disabled':
                    result=launch(label+'-cli-'+mode,command,1)
                    assert result.stderr=='error: unknown or disabled VM backend\n'and not output.exists(),result.stderr
                    item['expected_disabled_reject']=True
                else:
                    result=launch(label+'-cli-'+mode,command)
                    actual=json.loads(result.stdout);item['metric']=actual;item['sha256']=sha(output);outputs[mode]=output.read_bytes()
                    assert actual['vm_budget_mode']=='fixed'and actual['vm_budget_work']==0
                    if mode=='decoded-threaded-load-pair':
                        expected='decoded-threaded-load-pair'if label=='gnu'else 'decoded-fallback'
                        assert actual['vm_backend']==expected,actual
                        if label=='portable':assert actual['vm_fusion_status_last']=='portable-fallback'and actual['vm_fusion_pairs_executed']==0
                        else:assert actual['vm_fusion_pairs_discovered']>0 and actual['vm_fusion_pairs_executed']>0
                    elif mode=='auto':
                        assert actual['vm_backend']==('decoded-threaded'if label=='gnu'else 'decoded-fallback')
                        assert actual['vm_fusion_pairs_executed']==0
                write(directory/'report.json',report)
            if outputs:assert len(set(outputs.values()))==1,'CLI full file bytes differ'
        report['passed']=True
    except BaseException as error:
        report['first_failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        write(directory/'report.json',report);raise
    write(directory/'report.json',report)
    print(json.dumps({'passed':True,'report':str(directory/'report.json'),'sha256':sha(directory/'report.json')}),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
    assert args.prepare!=args.run,'choose one action';prepare()if args.prepare else run()
