"""Freeze source,160 pre-execution gold and compiler plan. Never compiles."""
from pathlib import Path
import datetime,hashlib,json,shutil
P=Path('research/batch55');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
assert sha('reports/project27-research.tex')=='e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
old=json.loads((P/'static-plan-freeze.json').read_text())
for f in old['files']:assert sha(f['path'])==f['sha256'],f['path']
gold=json.loads((P/'gold160.json').read_text());assert gold['count']==160
assert all(c['qualifier']['prefix_is_original_ideal'] and c['qualifier']['prefix_physical_valid'] for c in gold['cases'])
assert sum(c['qualifier']['eligible'] for c in gold['cases'])==158
assert all(c['qualifier']['eligible'] and not c['qualifier']['within128'] and c['whole_physics']['valid'] for c in gold['cases'] if c['family']=='D' and len(c['qualifier']['closure_original_ids'])>128)
paths=set(f['path'] for f in old['files'])
paths.update(str(p).replace('\\','/') for p in P.iterdir() if p.is_file() and p.name!='pre-execution-freeze.json')
paths.update('scripts/'+s for s in ('prepare_cut_repair_batch55.py','make_cut_repair_gold_batch55.py','freeze_cut_repair_pre_execution_batch55.py'))
paths.update(('src/benchmark.cpp','src/simulator.cpp','include/local_json.h','include/simulator.h','include/solver_metrics.h','reports/observer-baseline-batch52.json'))
space=shutil.disk_usage(Path.cwd().anchor)
plan=dict(scope='AUTHORIZATION_REQUIRED_BEFORE_COMPILE; then160controls and sameR52twelve only; no63/67/full/perf/default',process_environment_overrides={k:str((P/'compiler-temp').resolve()) for k in ('TEMP','TMP','TMPDIR')},minimum_F_free_bytes=1024**3,observed_F_free_bytes=space.free,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=[['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude',str(P/'gold-driver.cpp'),'src/simulator.cpp','-o',str(P/'gold-gcc.exe')],['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude',str(P/'selected12-driver.cpp'),'src/simulator.cpp','-o',str(P/'selected12-gcc.exe')],['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude','-c',str(P/'solution.cpp'),'-o',str(P/'standalone.o')],['cmd.exe','/c',str(P/'build-ubsan.cmd')]],future_actual_calls=dict(normal_probe_per_compiler=160,direct_routine_per_compiler=16,independent_fixed_physics_per_compiler=160,compilers=['GCC15.2-O2','Clang21.1-O1-UBSan'],same12_whole_and_helper_GCC=12),execution_started=False,logs='All commands capture separate stdout/stderr/actualexit; no run inferred from file existence; shared functional timing only')
(P/'compiler-resource-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8');paths.add(str(P/'compiler-resource-plan.json').replace('\\','/'))
doc=dict(status='SOURCE_AND160_PREEXECUTION_GOLD_FROZEN_NO_COMPILER_OR_CANDIDATE_EXECUTED',candidate_source_sha256=sha(P/'solution.cpp'),fragment_sha256=sha(P/'repair.cpp.inc'),gold_sha256=sha(P/'gold160.json'),driver_input_sha256=sha(P/'gold-driver-input.json'),literal_charge_sha256=sha(P/'literal-charge-gold.json'),source_base='R51-8b7c',default_changed=False,old_open_tex_changed=False,live_handles=[],candidate_executed=False,gold_expected_not_actual_candidate_results=True,controls=160,eligible=158,deliberate_zero_output_ineligible=2,cap129_130_controls=8,direct_routine_only_same_mask_controls=16,literal_boundaries=dict(setup=80,first_physical_child=112,helper_complete=178,returned_complete=180),files=[dict(path=f,bytes=Path(f).stat().st_size,sha256=sha(f)) for f in sorted(paths)])
out=P/'pre-execution-freeze.json';out.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(out),sha256=sha(out),frozen_files=len(paths),source_sha256=doc['candidate_source_sha256'],gold_sha256=doc['gold_sha256'],F_free_bytes=space.free,status=doc['status']),indent=2))
