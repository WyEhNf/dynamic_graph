"""Explicit isolated nested integration phases. No ordinary install or perf."""
import argparse,ctypes,hashlib,json,os,shutil,time
from pathlib import Path
from windows_file_resource_probe_stage2 import HostMemory,monitored_run
P=Path(__file__).resolve().parents[1];R=P/'artifacts/stage2-vm-nested-budget/runtime-integration';W=R/'workspace';F=R/'implementation-freeze'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['build','contracts','ctest','functional','ubsan'],required=True);args=parser.parse_args()
    frozen=read(F/'manifest.json');assert frozen['compile_or_VM_started']==False
    assert sha(P/'build/cholesky_runtime.exe')==frozen['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==frozen['memory_sha256']
    for relative,digest in frozen['mirror_source_sha256'].items():assert sha(W/relative)==digest,relative
    assert sha(Path(__file__))==frozen['runner_sha256']
    out=R/(args.phase+'-evidence');out.mkdir(exist_ok=False);temp=P/'artifacts/stage2-vm-nested-budget/compiler-temp';temp.mkdir(exist_ok=True);os.environ.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']});os.chdir(W)
    report={'schema':'optional-nested-VM-runtime-'+args.phase+'-evidence-v1','passed':False,'phase':args.phase,'implementation_manifest_sha256':sha(F/'manifest.json'),'process_env':{k:os.environ[k]for k in ['TEMP','TMP','TMPDIR']},'runs':[],'functional':[],'sources':[],'errors':[],'cli':[],'ordinary_unchanged':True,'performance_or_maximum_started':False}
    started=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-started;(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def call(label,command,want=0):
        memory=HostMemory();memory.dwLength=ctypes.sizeof(memory);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory));free=shutil.disk_usage(P).free
        if memory.ullAvailPhys<256*1024*1024 or free<512*1024*1024:report.update(resource_gate_exit=75,pending_label=label);save();raise SystemExit(75)
        command=list(map(str,command));print(json.dumps({'starting':label,'command':command,'fresh_RAM_bytes':memory.ullAvailPhys,'F_free_bytes':free}),flush=True);began=time.perf_counter()
        proc,resource=monitored_run(command,out/(label+'.stdout'),out/(label+'.stderr'),check=False)
        row={'label':label,'command':command,'exit_code':proc.returncode,'wall_ms':(time.perf_counter()-began)*1000,'fresh_RAM_bytes':memory.ullAvailPhys,'F_free_bytes':free,'stdout_sha256':sha(out/(label+'.stdout')),'stderr_sha256':sha(out/(label+'.stderr')),**resource};report['runs'].append(row);save();print(json.dumps({'terminal':label,'exit_code':proc.returncode}),flush=True)
        assert proc.returncode==want,(label,proc.returncode,proc.stderr);return proc,row
    builds=frozen['builds'];cmake='C:/Program Files (x86)/CMake/bin/cmake.exe';ctest='C:/Program Files (x86)/CMake/bin/ctest.exe'
    if args.phase=='build':
        call('GNU-compiler-version',['E:/mingw64/bin/g++.exe','--version'])
        for b in builds:
            build=R/b['build'];assert not build.exists()
            command=[cmake,'--preset','local-mingw','-B',build,'-DPython3_EXECUTABLE='+str(P/'.venv/Scripts/python.exe'),'-DCHOL_PROVED_VM_BUDGET='+('ON'if b['CHOL_PROVED_VM_BUDGET']else'OFF'),'-DCHOL_NESTED_VM_BUDGET='+('ON'if b['CHOL_NESTED_VM_BUDGET']else'OFF'),'-DCHOL_THREADED_VM_FORCE_PORTABLE='+('ON'if b['CHOL_THREADED_VM_FORCE_PORTABLE']else'OFF'),'-DCHOL_TEST_ARTIFACT_LABEL=stage2-vm-nested-'+b['label']]
            call(b['label']+'-configure',command);call(b['label']+'-build',[cmake,'--build',build,'--parallel','2'])
            inventory={}
            for artifact in [*build.glob('*.exe'),*build.glob('*.a'),build/'CMakeCache.txt',*sorted((build/'CMakeFiles').glob('*.dir/flags.make')),*sorted((build/'CMakeFiles').glob('*.dir/build.make')),*sorted((build/'CMakeFiles').glob('*.dir/link.txt'))]:
                inventory[artifact.relative_to(build).as_posix()]={'path':str(artifact),'sha256':sha(artifact),'bytes':artifact.stat().st_size}
            report.setdefault('build_inventory',{})[b['label']]={'matching_runtime_header_sha256':sha(W/'include/cholesky/runtime.hpp'),'all_new_core_and_callers_recompiled':True,'artifacts':inventory};save()
        invalid=R/'build-invalid';proc,_=call('nestedON-provedOFF-configure',[cmake,'--preset','local-mingw','-B',invalid,'-DCHOL_PROVED_VM_BUDGET=OFF','-DCHOL_NESTED_VM_BUDGET=ON'],want=1);assert 'CHOL_NESTED_VM_BUDGET requires CHOL_PROVED_VM_BUDGET'in proc.stderr
    elif args.phase in ['contracts','ctest']:
        for b in builds:
            build=R/b['build'];command=[ctest,'--test-dir',build,'--output-on-failure','-j','1']
            if args.phase=='contracts' or b['label']!='gnu-nested':command+=['-E','source_pipeline|helper_source_pipeline|while_source_pipeline|integer_selector_pipeline']
            call(b['label']+'-'+args.phase,command)
            # Save actual individual test stdout independently from CTest display.
            if args.phase=='contracts':
                proc,_=call(b['label']+'-selection-raw',[build/'vm_nested_budget_selection_tests.exe']);rows=[json.loads(line)for line in proc.stdout.splitlines()];summary=rows[-1];assert summary['passed'];assert summary['selection_observations']==(10 if b['label']=='disabled'else 60);report.setdefault('selection',[]).append({'build':b['label'],'summary':summary,'observations':rows[:-1]});save()
    elif args.phase=='functional':
        from analyze_source import analyze
        from evaluate_source import make_input,compile_oracle,exact_compare
        import subprocess
        old=read(P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json');initial=read(R/'initial-plan/plan.json');assert old['passed'] and sha(P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json')==initial['old_report_sha256']
        binary={b['label']:R/b['build']/'cholesky_runtime.exe'for b in builds};report['binary_sha256']={k:sha(v)for k,v in binary.items()}
        modes={
          'fixed-auto':(binary['gnu-nested'],['--vm-budget','fixed']),
          'proved-auto':(binary['gnu-nested'],['--vm-budget','proved']),
          'proved-legacy':(binary['gnu-nested'],['--vm-budget','proved','--vm-backend','legacy']),
          'proved-decoded':(binary['gnu-nested'],['--vm-budget','proved','--vm-backend','decoded']),
          'proved-tos2':(binary['gnu-nested'],['--vm-budget','proved','--vm-backend','decoded-tos2']),
          'proved-threaded':(binary['gnu-nested'],['--vm-budget','proved','--vm-backend','decoded-threaded']),
          'portable-proved':(binary['portable-nested'],['--vm-budget','proved'])}
        report['sources']=[{**s,'inherited_actual_C':True}for s in old['sources']]
        def runtimes(label,family,metadata,ip,ref,selected_modes,expected=None,engine='auto',fresh_requirement=None,scope='main'):
            hashes={'metadata_sha256':sha(metadata),'input_sha256':sha(ip),'reference_sha256':sha(ref)}
            for mode,(exe,flags)in selected_modes.items():
                folder=out/label;folder.mkdir(exist_ok=True);target=folder/(family+'-'+mode+'.bin');rawlabel=label+'-'+family+'-'+mode;command=[exe,'--metadata',metadata,'--input',ip,'--output',target,'--engine',engine,'--threads','4','--block-size','32',*flags]
                proc,resources=call(rawlabel,command);metric=json.loads(proc.stdout)
                row={'source':label,'family':family,'mode':mode,'scope':scope,'metadata':str(metadata),'input':str(ip),'reference':str(ref),'output':str(target),**hashes,**metric,**exact_compare(ref,target)};report['functional'].append(row);save()
                if expected is not None:assert metric['vm_steps']==expected
                if mode!='fixed-auto'and metric['selected_engine']=='vm':
                    assert metric['vm_budget_first_proved_matrices']+metric['vm_budget_first_unknown_matrices']==metric['matrices']
                    assert metric['vm_budget_work']==metric['vm_budget_first_work']+metric['vm_budget_nested_work'] and metric['vm_budget_work']<=250000*metric['matrices']
                if mode=='fixed-auto' or metric['selected_engine']!='vm':assert metric['vm_budget_work']==0 and metric['vm_budget_proof_ms']==0 and metric['vm_budget_nested_attempted_matrices']==0
                if mode=='portable-proved'and metric['selected_engine']=='vm':assert metric['vm_backend']=='decoded-fallback'
                if mode=='proved-auto' and fresh_requirement:
                    if fresh_requirement=='nested':assert metric['selected_engine']=='vm'and metric['vm_budget_first_unknown_matrices']==5 and metric['vm_budget_nested_proved_matrices']==5 and metric['vm_budget_proved_matrices']==5,(label,family,metric)
                    if fresh_requirement=='unknown':assert metric['selected_engine']=='vm'and metric['vm_budget_unknown_matrices']==5 and metric['vm_effective_step_limit_max']==1000000000,(label,family,metric)
                    if fresh_requirement=='native':assert metric['selected_engine']!='vm'and metric['vm_budget_not_run_matrices']==5 and metric['vm_budget_first_work']==0
            assert all(sha(path)==hashes[key]for key,path in [('metadata_sha256',metadata),('input_sha256',ip),('reference_sha256',ref)])
        for group in initial['old_C_reference_groups']:
            old_source=next(s for s in old['sources']if s['label']==group['source']);metadata=Path(group['metadata']);ip=Path(group['input']);ref=Path(group['reference']);assert sha(metadata)==group['metadata_sha256']and sha(ip)==group['input_sha256']and sha(ref)==group['reference_sha256']
            runtimes(group['source'],group['family'],metadata,ip,ref,modes,group['vm_steps'])
            runtimes(group['source'],group['family'],metadata,ip,ref,{'proved-only-compat':(binary['proved-only-compat'],['--vm-budget','proved'])},group['vm_steps'],scope='separate-compat')
        for source in initial['fresh_C_sources']:
            label=source['label'];folder=out/label;folder.mkdir(exist_ok=True);cp=folder/'source.c';shutil.copyfile(source['path'],cp);assert sha(cp)==source['sha256'];metadata=folder/'program.meta';analysis=analyze(cp,metadata,'C:/Program Files/LLVM/bin/clang.exe',source['function']);assert analysis['optimized']==('scalar_cholesky_column_dag'if label=='strict-cholesky-control'else'none'),(label,analysis['optimized'])
            # Reuse exact frozen harness generator, intercept only its GCC call for file capture.
            saved_run=subprocess.run
            def captured_gcc(command,*a,**kw):
                assert command[0]=='E:/mingw64/bin/gcc.exe'and not a
                proc,_=call(label+'-oracle-compile',command);return proc
            subprocess.run=captured_gcc
            try:oracle=compile_oracle(cp,source['function'],folder,'E:/mingw64/bin/gcc.exe')
            finally:subprocess.run=saved_run
            report['sources'].append({**source,'actual_folder':str(folder),'metadata_sha256':sha(metadata),'analysis_sha256':sha(metadata.with_suffix('.analysis.json')),'harness_sha256':sha(folder/'oracle.c'),'oracle_EXE_sha256':sha(oracle),'analysis':analysis});save()
            requirement='native'if label=='strict-cholesky-control'else'unknown'if label.startswith('unknown-')else'nested'
            for family,diagonal,signed in [('dense',False,False),('signedzero',True,True)]:
                ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin');make_input(ip,source['sizes'],diagonal=diagonal,signed_zero=signed);call(label+'-'+family+'-trueC',[oracle,ip,ref,'32'])
                runtimes(label,family,metadata,ip,ref,modes,fresh_requirement=requirement)
                if label=='strict-cholesky-control':runtimes(label,family,metadata,ip,ref,{'forced-VM-fixed':modes['fixed-auto'],'forced-VM-proved':modes['proved-auto']},engine='vm',scope='main-forced')
        failure_input=P/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin'
        for failure in old['failures']:
            for mode,(exe,flags)in {**modes,'proved-only-compat':(binary['proved-only-compat'],['--vm-budget','proved'])}.items():
                target=out/('error-'+failure['source']+'-'+mode+'.bin');proc,_=call('error-'+failure['source']+'-'+mode,[exe,'--metadata',failure['metadata'],'--input',failure_input,'--output',target,*flags],want=1)
                report['errors'].append({'source':failure['source'],'mode':mode,'stderr':proc.stderr,'stdout':proc.stdout,'exit_code':proc.returncode});save();assert proc.stderr==failure['results'][0]['stderr']and not target.exists()and not Path(str(target)+'.partial').exists()
        for index,entry in enumerate(old['cli']):
            label='disabled'if 'disabled'in entry['exe']else'portable-nested'if 'portable'in entry['exe']else'gnu-nested';proc,_=call('CLI-'+str(index),[binary[label],*entry['flags']],want=entry['exit_code']);assert proc.stdout==entry['stdout']and proc.stderr==entry['stderr'];report['cli'].append({'build':label,**entry,'actual_exe':str(binary[label])});save()
        proc,_=call('CLI-proved-only-help',[binary['proved-only-compat'],'--help']);assert proc.stdout==next(c['stdout']for c in old['cli']if c['flags']==['--help']and 'disabled'not in c['exe']);report['cli'].append({'build':'proved-only-compat','flags':['--help'],'stdout':proc.stdout,'stderr':proc.stderr});save()
        assert len(report['functional'])==624 and len(report['errors'])==56 and len(report['cli'])==10
        mainrows=[r for r in report['functional']if r['scope']!='separate-compat'];assert len(mainrows)==557
        old_auto=[r for r in mainrows if r['mode']=='proved-auto'and r['source']not in [s['label']for s in initial['fresh_C_sources']]]
        assert sum(r['vm_budget_first_proved_matrices']for r in old_auto)==306 and sum(r['vm_budget_first_unknown_matrices']for r in old_auto)==260
        compatibility=[r for r in report['functional']if r['scope']=='separate-compat'];assert len(compatibility)==67 and sum(r['vm_budget_proved_matrices']for r in compatibility)==306 and sum(r['vm_budget_unknown_matrices']for r in compatibility)==260
        report.update(main_whole_C=557,separate_compat_whole_C=67,all_whole_C=624,main_errors=49,all_errors=56,main_CLI=9,all_CLI=10)
    else:
        # Separate Clang/UBSan full new ABI; no old core import or SIMD TU leakage.
        import subprocess
        compiler='C:/Program Files/LLVM/bin/clang++.exe';flags=['-std=c++20','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=undefined','-fno-fast-math','-ffp-contract=off','-DCHOL_UPDATE_WIDTH=16','-DCHOL_AVX_ROW_GROUP=0','-DCHOL_PACK_INITIALIZATION=0','-DCHOL_PREPARED_VM=1','-DCHOL_THREADED_VM=1','-DCHOL_HAVE_THREADED_DISPATCH=1','-DCHOL_PROVED_VM_BUDGET=1','-DCHOL_NESTED_VM_BUDGET=1','-I',str(W/'include')]
        sources=['runtime','tiled_runtime','banded_runtime','binary_io','prepared_vm','threaded_vm','vm_step_bound','vm_nested_step_bound'];tests=['threaded_vm_tests','threaded_vm_proved_tests','vm_nested_step_bound_tests','vm_nested_budget_selection_tests'];commands=[];objects=[]
        for source in sources:obj=out/(source+'.obj');objects.append(obj);commands.append([compiler,*flags,'-c',W/'src'/(source+'.cpp'),'-o',obj])
        for test in tests:commands.append([compiler,*flags,W/'tests'/(test+'.cpp'),*objects,'-o',out/(test+'.exe')])
        lines=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul']
        for command in commands:lines+=[subprocess.list2cmdline(list(map(str,command))),'if errorlevel 1 exit /b %errorlevel%']
        for test in tests:lines+=[subprocess.list2cmdline([str(out/(test+'.exe'))]),'if errorlevel 1 exit /b %errorlevel%']
        cmd=out/'build-and-run.cmd';cmd.write_text('\n'.join(lines)+'\n',encoding='utf-8');report['compile_commands']=[list(map(str,c))for c in commands];save();call('UBSan-build-and-contracts',['cmd.exe','/d','/c',cmd])
    assert sha(P/'build/cholesky_runtime.exe')==frozen['ordinary_sha256']and sha(P/'build-memory/cholesky_runtime.exe')==frozen['memory_sha256'];assert all(sha(W/k)==v for k,v in frozen['mirror_source_sha256'].items())
    report['passed']=True;save();print(json.dumps({'passed':True,'phase':args.phase,'report_sha256':sha(out/'report.json'),'no_ordinary_install':True}),flush=True)
if __name__=='__main__':main()
