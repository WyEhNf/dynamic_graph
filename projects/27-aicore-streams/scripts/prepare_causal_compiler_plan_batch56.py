"""Static file/manifest preparation ONLY: no compiler/reference/candidate process."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
P=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
assert sha(P/'solution.cpp')==source
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
assert sha('reports/project27-research.tex')=='e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
for name in ('source-before-gold-freeze.json','reference-completion-freeze-revision1.json'):
    old=json.loads((P/name).read_text())
    for f in old['files']:assert sha(f['path'])==f['sha256'],f['path']
dest=P/'selected12-driver.cpp';assert not dest.exists();dest.write_bytes(Path('research/batch55/selected12-driver.cpp').read_bytes())
owned='G:/Hackathon-project27-owned/batch56-3a4f184d';assert not Path(owned).exists()
gcc='E:/mingw64/bin/g++.exe';clang='C:/Program Files/LLVM/bin/clang++.exe'
vs='C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat'
assert all(Path(f).is_file() for f in (gcc,clang,vs))
commands=[dict(label='gcc-version',argv=[gcc,'--version']),dict(label='clang-version',argv=[clang,'--version'])]
for label,driver in (('gold','gold-driver.cpp'),('caller','caller-controls-driver.cpp'),('selected12','selected12-driver.cpp')):
    commands.append(dict(label='build-gcc-'+label,argv=[gcc,'-O2','-std=c++17','-Iinclude',str(P/driver),'src/simulator.cpp','-o',owned+'/bin/'+label+'-gcc.exe']))
commands.append(dict(label='build-gcc-standalone',argv=[gcc,'-O2','-std=c++17','-Iinclude','-c',str(P/'solution.cpp'),'-o',owned+'/bin/standalone.o']))
for label,driver in (('gold','gold-driver.cpp'),('caller','caller-controls-driver.cpp')):
    cmd=P/('build-ubsan-'+label+'.cmd');assert not cmd.exists()
    executable=owned+'/bin/'+label+'-ubsan.exe';pdb=owned+'/bin/'+label+'-ubsan.pdb';ilk=owned+'/bin/'+label+'-ubsan.ilk'
    cmd.write_text('@echo off\ncall "'+vs+'" -arch=x64 -host_arch=x64 >nul\nif errorlevel 1 exit /b 1\n"'+clang+'" -std=c++17 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Iinclude '+str(P/driver)+' src/simulator.cpp -Xlinker "/PDB:'+pdb+'" -Xlinker "/ILK:'+ilk+'" -o "'+executable+'"\nif errorlevel 1 exit /b 1\nexit /b 0\n',encoding='utf-8')
    commands.append(dict(label='build-ubsan-'+label,argv=['cmd.exe','/c',str(cmd)]))
for compiler in ('gcc','ubsan'):
    commands.append(dict(label='run-'+compiler+'-gold',argv=[owned+'/bin/gold-'+compiler+'.exe',str(P/'gold-driver-input.json'),owned+'/outputs/gold-'+compiler+'.json']))
    commands.append(dict(label='run-'+compiler+'-caller',argv=[owned+'/bin/caller-'+compiler+'.exe',str(P/'caller-guard-controls16.json'),owned+'/outputs/caller-'+compiler+'.json']))
commands.append(dict(label='verify-frozen-gold',argv=[sys.executable,'scripts/verify_causal_gold_batch56.py']))
plan=dict(status='STATIC_PREPARED_NOT_EXECUTED_ROOT_REVIEW_REQUIRED',project_root=str(Path.cwd().resolve()),owned_root=owned,process_environment_overrides={k:owned+'/compiler-temp' for k in ('TEMP','TMP','TMPDIR')},minimum_G_free_bytes=1<<30,observed_G_free_bytes=shutil.disk_usage('G:/').free,observed_F_free_bytes=shutil.disk_usage('F:/').free,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands,scope='GCC160 detector+16directcaller/guard+160fixedphys and ClangUBSan same; compile-only original12 driver/stdlib singlefile; no12solver/63/67/full/perf/default/TeX',coverage=dict(normal_per_compiler=160,direct_extra_per_compiler=16,fixed_physics_per_compiler=160,extra_fixed_physics_per_compiler=16,source_per_operation_runtime_fee_trace=False,original12_execution=False,artificial_whole_success_not_guaranteed=True),budgets_unchanged=dict(cut=2000000,projection_shared=16000000,closure=128,top_held=24,restart_count=1),preserve_first_failure=True,automatic_retry=False,no_user_cleanup=True,no_system_environment_mutation=True)
plan_path=P/'compiler-resource-plan.json';assert not plan_path.exists();plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
paths={str(f).replace('\\','/') for f in P.iterdir() if f.is_file()}
paths.update(str(f).replace('\\','/') for f in Path('include').glob('*.h'))
paths.update(('src/benchmark.cpp','src/simulator.cpp','solution/solution.cpp','build/aicore_bench.exe','reports/project27-research.tex','reports/project27-research-resumed.tex','research/batch52/observer-selected12-input-only.json','reports/observer-baseline-batch52.json','scripts/prepare_causal_compiler_plan_batch56.py','scripts/run_causal_controls_batch56.py','scripts/verify_causal_gold_batch56.py'))
doc=dict(status='PRE_COMPILE_PLAN_AND_ALL_GOLD_FROZEN_NO_CANDIDATE_EXECUTED',source_sha256=source,original160_preserved=True,extra16_hand_fees=dict(guard=69,restart=207,sharedwork7_restart=214,external_guardprobe=67),root_reference_audit='F:/Hackathon/outputs/stage2-root-causal-reference-gold-r56.json',no_live_handles=[],actual_generator_executions_prior=1,candidate_executions=0,compiled=False,default_changed=False,old_open_tex_changed=False,files=[dict(path=f,sha256=sha(f),bytes=Path(f).stat().st_size) for f in sorted(paths)])
target=P/'compiler-controls-plan-freeze.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(target),sha256=sha(target),files=len(paths),extra16_sha256=sha(P/'caller-guard-controls16.json'),handfees_sha256=sha(P/'caller-guard-hand-fees.json'),runner_sha256=sha('scripts/run_causal_controls_batch56.py'),verifier_sha256=sha('scripts/verify_causal_gold_batch56.py'),plan_sha256=sha(plan_path),owned_root=owned,compiled=False,candidate_executed=False),indent=2))
