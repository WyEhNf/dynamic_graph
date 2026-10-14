import hashlib,json,shutil,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-prepared-vm-phase3'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
snap=root/'candidate-source';snap.mkdir(exist_ok=False);hashes={}
paths=[p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),*sorted((p/'tools').glob('*.py')),p/'tools/build_threaded_vm_ubsan.cmd']
for build in ['build-stage2-vm-threaded','build-stage2-vm-threaded-portable']:
    paths += [p/build/x for x in ['CMakeCache.txt','CTestTestfile.cmake','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_core.dir/link.txt','CMakeFiles/cholesky_runtime.dir/link.txt','CMakeFiles/threaded_vm_tests.dir/flags.make','CMakeFiles/threaded_vm_tests.dir/link.txt']]
for x in paths:
    name=x.relative_to(p).as_posix();dest=snap/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,dest);hashes[name]=sha(dest)
executables={'candidate.exe':p/'build-stage2-vm-threaded/cholesky_runtime.exe','portable-candidate.exe':p/'build-stage2-vm-threaded-portable/cholesky_runtime.exe','native-contract.exe':p/'build-stage2-vm-threaded/threaded_vm_tests.exe','portable-contract.exe':p/'build-stage2-vm-threaded-portable/threaded_vm_tests.exe','old404-contract.exe':p/'build-stage2-vm-threaded/prepared_vm_tests.exe','old480-contract.exe':p/'build-stage2-vm-threaded/prepared_vm_tos2_tests.exe','ubsan-contract.exe':root/'threaded-contract-ubsan.exe'}
for name,x in executables.items():shutil.copyfile(x,root/name)
runs=[]
for name in ['native-contract.exe','portable-contract.exe','old404-contract.exe','old480-contract.exe','ubsan-contract.exe']:
    start=time.perf_counter();r=subprocess.run([str(root/name)],capture_output=True,text=True);assert r.returncode==0,(name,r.stderr)
    (root/(name+'.stdout.log')).write_text(r.stdout,encoding='utf-8');(root/(name+'.stderr.log')).write_text(r.stderr,encoding='utf-8')
    runs.append({'name':name,'exit_code':r.returncode,'wall_ms':(time.perf_counter()-start)*1000,'result':json.loads(r.stdout),'stderr':r.stderr,'exe_sha256':sha(root/name)})
manifest={'status':'small functional contracts passed; full C pending; no performance','default':'OFF; enabled still legacy; ordinary4f73 untouched','source_sha256':hashes,'executable_sha256':{name:sha(root/name)for name in executables},'contracts':runs,'actual_indirect_sites':['0x140018297 initial','0x14001830e common normal NEXT','0x140018793 jump NEXT'],'machine_code_sha256':sha(root/'threaded-initial.asm'),'machine_code_observation':'GNU15.2 tailmerged to3 dispatch sites; removed inner binary table; compiler auto-inlined unchanged source poplambda; about24KiB function vs5.6KiB decoded; not isolated branch-only effect','ubsan':'Clang21 native MSVC headers/ABI standalone UBSan all934; separate portable native dependencies, -fno-fast-math -ffp-contract=off; explicit native compile macros16/0/0','failed_attempts':[{'session':90668,'exit_code':1,'diagnostic':'CHOL_AVX_ROW_GROUP undefined in tiled_runtime standalone direct build; corrected by explicit native CMake macros, successful50935 exit0'},{'diagnostic':'first GNU-target Clang compile missing stdlib.h search path; later instrumented object built with E:/mingw64/include, never linked/used as proof; switched actual full native sanitizer to established MSVC environment'}]}
(root/'small-contract-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'sources':len(hashes),'runs':len(runs),'candidate_sha256':manifest['executable_sha256']['candidate.exe']}))
