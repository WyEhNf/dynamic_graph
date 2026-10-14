"""Compile/capture the isolated proof component using only project F temp."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-vm-proved-budget';out=root/'component-acceptance';out.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
temp=root/'compiler-temp';temp.mkdir(exist_ok=True);env=dict(os.environ);env.update({key:str(temp)for key in ['TEMP','TMP','TMPDIR']})
compiler=Path('E:/mingw64/bin/g++.exe');core=p/'build-stage2-vm-default/libcholesky_core.a';exe=out/'vm-bound-tests.exe'
command=[str(compiler),'-std=c++20','-O2','-g','-Wall','-Wextra','-Wpedantic','-fno-fast-math','-ffp-contract=off','-I',str(p/'include'),str(p/'src/vm_step_bound.cpp'),str(p/'tests/vm_step_bound_tests.cpp'),str(core),'-o',str(exe)]
free=shutil.disk_usage(root).free;assert free>=256*1024*1024
start=time.perf_counter();proc=subprocess.run(command,capture_output=True,text=True,env=env)
(out/'compile.stdout').write_text(proc.stdout,encoding='utf-8');(out/'compile.stderr').write_text(proc.stderr,encoding='utf-8');assert proc.returncode==0
build_seconds=time.perf_counter()-start
start=time.perf_counter();test=subprocess.run([str(exe)],capture_output=True,text=True,env=env)
(out/'test.stdout').write_text(test.stdout,encoding='utf-8');(out/'test.stderr').write_text(test.stderr,encoding='utf-8');assert test.returncode==0
result=json.loads(test.stdout);assert result['passed']and result['adversarial_program_mutations']==6358 and result['actual_mutation_VM_executions']==2*result['proved_mutations']
test_seconds=time.perf_counter()-start
files=[p/'src/vm_step_bound.cpp',p/'include/cholesky/vm_step_bound.hpp',p/'tests/vm_step_bound_tests.cpp',p/'docs/stage2-vm-proved-budget-plan.md',Path(__file__),p/'build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make']
hashes={}
for x in files:
    name=x.relative_to(p);dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,dest);hashes[name.as_posix()]=sha(dest)
ordinary='99a87d135378406a15efd930d58941291683ca799f91bd5dcc0ca77ceadef448';assert sha(p/'build/cholesky_runtime.exe')==ordinary
original=json.loads((root/'initial-plan.json').read_text(encoding='utf-8'))
for name,digest in original['source_sha256'].items():assert sha(p/name)==digest,name
attempt={x.name:sha(x)for x in sorted((root/'initial-attempt').iterdir())if x.is_file()}
manifest={'passed':True,'phase':'component only; no Runtime/Options/CMake integration','actual_compile_exit_code':proc.returncode,'actual_test_exit_code':test.returncode,'compile_seconds':build_seconds,'test_seconds':test_seconds,'compile_command':command,'process_compile_env':{k:env[k]for k in ['TEMP','TMP','TMPDIR']},'free_disk_before_bytes':free,'compiler_version':subprocess.check_output([str(compiler),'--version'],text=True),'proof_test_TU_flags':'O2,g,strictFP; no performance claim','existing_frozen_core_library':{'path':str(core),'sha256':sha(core),'flags_sha256':sha(p/'build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make')},'source_sha256':hashes,'test_exe_sha256':sha(exe),'result':result,'ordinary_runtime_sha256':ordinary,'ordinary_source_unchanged':True,'Metadata_unchanged':True,'Runtime_budget_unchanged':True,'maximum_execution_started':False,'primary_refs':original['primary_references'],'initial_attempt_preserved_sha256':attempt,'initial_attempt_actual_exit_code':1,'initial_attempt_error':'unsound mutation accepted','initial_attempt_reason':'Test attempted a zero-progress mutation by modifying the ignored POP operand, instead of the induction CONST; corrected test locations; no earlier component runtime change','compile_stdout_sha256':sha(out/'compile.stdout'),'compile_stderr_sha256':sha(out/'compile.stderr'),'test_stdout_sha256':sha(out/'test.stdout'),'test_stderr_sha256':sha(out/'test.stderr')}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'result':result,'manifest_sha256':sha(out/'manifest.json'),'actual_compile_exit_code':proc.returncode,'actual_test_exit_code':test.returncode,'ordinary_runtime_unchanged':True,'maximum_execution_started':False},indent=2),flush=True)
