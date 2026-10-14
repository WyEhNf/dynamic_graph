"""Sequential Clang UBSan diagnostic builds with project-only compiler temp."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parents[1];out=p/'artifacts/stage2-vm-proved-budget/runtime-integration/ubsan';out.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
temp=p/'artifacts/stage2-vm-proved-budget/compiler-temp';temp.mkdir(exist_ok=True);env=dict(os.environ);env.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
assert shutil.disk_usage(p).free>=256*1024*1024
compiler='C:/Program Files/LLVM/bin/clang++.exe'
flags=['-std=c++20','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=undefined','-fno-fast-math','-ffp-contract=off','-DCHOL_UPDATE_WIDTH=16','-DCHOL_AVX_ROW_GROUP=0','-DCHOL_PACK_INITIALIZATION=0','-DCHOL_PREPARED_VM=1','-DCHOL_THREADED_VM=1','-DCHOL_HAVE_THREADED_DISPATCH=1','-DCHOL_PROVED_VM_BUDGET=1','-I',str(p/'include')]
sources=['src/runtime.cpp','src/tiled_runtime.cpp','src/banded_runtime.cpp','src/binary_io.cpp','src/prepared_vm.cpp','src/threaded_vm.cpp','src/vm_step_bound.cpp']
tests=['threaded_vm_tests','threaded_vm_proved_tests','vm_step_bound_tests','vm_proved_budget_tests']
cmd=out/'build-and-run.cmd';lines=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul']
commands=[];objects=[]
for source in sources:
    obj=out/(Path(source).stem+'.obj');objects.append(str(obj));commands.append([compiler,*flags,'-c',str(p/source),'-o',str(obj)])
for test in tests:commands.append([compiler,*flags,str(p/'tests'/(test+'.cpp')),*objects,'-o',str(out/(test+'.exe'))])
for command in commands:lines.extend([subprocess.list2cmdline(command),'if errorlevel 1 exit /b %errorlevel%'])
for test in tests:lines.extend([subprocess.list2cmdline([str(out/(test+'.exe'))]),'if errorlevel 1 exit /b %errorlevel%'])
cmd.write_text('\n'.join(lines)+'\n',encoding='utf-8')
start=time.perf_counter();proc=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=p,env=env,capture_output=True,text=True)
(out/'stdout.log').write_text(proc.stdout,encoding='utf-8');(out/'stderr.log').write_text(proc.stderr,encoding='utf-8')
report={'passed':proc.returncode==0,'exit_code':proc.returncode,'commands':commands,'process_env':{k:env[k]for k in ['TEMP','TMP','TMPDIR']},'elapsed_seconds':time.perf_counter()-start,'source_sha256':{name:sha(p/name)for name in sources+[str(Path('tests')/(t+'.cpp'))for t in tests]},'compiler_version':subprocess.check_output([compiler,'--version'],text=True),'stdout_sha256':sha(out/'stdout.log'),'stderr_sha256':sha(out/'stderr.log'),'exe_sha256':{test:sha(out/(test+'.exe'))for test in tests if(out/(test+'.exe')).exists()},'maximum_execution_started':False,'performance_claim':False}
(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'passed':report['passed'],'exit_code':proc.returncode,'elapsed_seconds':report['elapsed_seconds'],'report_sha256':sha(out/'report.json')}),flush=True)
if proc.returncode:raise SystemExit(proc.returncode)
