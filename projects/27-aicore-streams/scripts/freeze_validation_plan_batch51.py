"""Static pending gate manifest; never marks prepared tests as executed."""
import hashlib,json
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()
p=Path('research/batch51')
assert sha(p/'solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
inputs=[str(x).replace('\\','/') for d in ('src','include') for x in sorted(Path(d).glob('*')) if x.suffix in ('.cpp','.h')]
inputs += [str(x).replace('\\','/') for x in sorted((p/'tests').glob('*.cpp'))]
inputs += [str(p/f).replace('\\','/') for f in ('solution.cpp','projection.cpp.inc','release-cut.cpp.inc','cmake/CMakeLists.txt','numeric_checks.cpp','test_projection.cpp','test_group_template.cpp','test_release_cut.cpp')]
scripts=[str(x).replace('\\','/') for x in sorted(Path('scripts').glob('*batch51.py'))]
scripts+=['scripts/make_first_pivot_gold_batch50.py','scripts/make_projection_gold_batch45.py','scripts/make_group_gold_batch48.py','scripts/regress_current.py','scripts/compare_research.py','scripts/audit_certificates.py']
raw=['reports/functional-summary-batch51.json','reports/hard-functional-batch51.json','reports/heldout-functional-batch51.json','reports/release-cut-actual-plan-bigint-batch51.json','reports/release-cut-fixed-result-batch51.json','research/batch51/functional-checkpoint.json']
m=dict(status='Prepared pending gate only;full202/48 functionality actualterminal;new Release/Clang/979 gates NOT RUN',source_sha=sha(p/'solution.cpp'),compile_inputs={f:sha(f) for f in inputs},generation_inputs={f:sha(f) for f in scripts},completed_reports={f:sha(f) for f in raw},completed_executables={str(p/f).replace('\\','/'):sha(p/f) for f in ('diagnostic.exe','test_release_cut.exe','aicore_bench.exe')},prepared_commands=['C:/Users/admin/miniconda3/python.exe scripts/run_validation_build_batch51.py','C:/Users/admin/miniconda3/python.exe scripts/verify_candidate_batch51.py','C:/Users/admin/miniconda3/python.exe scripts/verify_numeric_batch51.py'],release_flags='CMake Release, GCC15.2, expected-O3-DNDEBUG;actual flags must be frozen after build',gate_counts=dict(ctest=14,normal=979,structure=36,prior_heldout=72,resource_controls=12,existing_fixed_bigint=523,new_cut_complete_plans=102,new_cut_probes=102,ancestor_profiles=495,group_recognition=83,group_moves=210),default48_source_sha=sha('solution/solution.cpp'),default48_exe_sha=sha('research/batch48/default-aicore_bench.exe'),old_user_open_tex_sha=sha('reports/project27-research.tex'),performance='NOT authorized/run; shared functional records cannot establish cost improvement',launch='Hold execution until parent confirms19 performancewindow true-terminal; build sequential parallel1; no GPU')
(p/'validation-plan.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print('validation plan',sha(p/'validation-plan.json'),flush=True)
