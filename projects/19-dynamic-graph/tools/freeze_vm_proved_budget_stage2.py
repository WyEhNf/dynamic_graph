"""Freeze accepted isolated policy; no ordinary installation or large run."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-proved-budget';root=stage/'runtime-integration';out=root/'acceptance';out.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def read(x):return json.loads(Path(x).read_text(encoding='utf-8'))
component=read(stage/'component-acceptance/manifest.json');initial=read(stage/'initial-plan.json')
proof=read(root/'correctness/report.json');contracts=read(root/'contracts-evidence-v2/report.json');ctest=read(root/'ctest-evidence/report.json');ubsan=read(root/'ubsan/report.json');build=read(root/'build-evidence/report.json');rebuild=read(root/'policy-rebuild-evidence/report.json')
assert all(r['passed']for r in [component,proof,contracts,ctest,ubsan,build,rebuild])
assert len(proof['runs'])==469 and len(proof['sources'])==15 and len(proof['failures'])==7 and len(proof['cli'])==9
assert all(r['byte_identical']for r in proof['runs'])and all(r['exit_code']==0 for r in build['runs']+contracts['runs']+ctest['runs']+rebuild['runs'])
ordinary=p/'build/cholesky_runtime.exe';memory=p/'build-memory/cholesky_runtime.exe';core=Path(component['existing_frozen_core_library']['path']);oldflags=p/'build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make'
assert sha(ordinary)==initial['ordinary_sha256']and sha(memory)=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
assert sha(core)==component['existing_frozen_core_library']['sha256']and sha(oldflags)==component['existing_frozen_core_library']['flags_sha256']
allowed={'CMakeLists.txt','include/cholesky/runtime.hpp','src/runtime.cpp','src/main.cpp'}
source_deltas={}
for relative,oldhash in initial['source_sha256'].items():
    newhash=sha(p/relative)
    if newhash!=oldhash:assert relative in allowed;source_deltas[relative]={'before_sha256':oldhash,'after_sha256':newhash}
assert set(source_deltas)==allowed
for relative in ['src/vm_step_bound.cpp','include/cholesky/vm_step_bound.hpp','tests/vm_step_bound_tests.cpp']:assert sha(p/relative)==component['source_sha256'][relative]
for relative in ['CMakeLists.txt','include/cholesky/runtime.hpp','src/runtime.cpp','src/main.cpp']:assert sha(p/relative)==build['source_sha256'][relative]
files=[p/'CMakeLists.txt',p/'CMakePresets.json',p/'README.md',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),*sorted((p/'tools').glob('*.py')),p/'docs/stage2-vm-proved-budget-integration.md',p/'docs/stage2-vm-proved-budget-plan.md']
hashes={}
for x in files:
    relative=x.relative_to(p);target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);hashes[relative.as_posix()]=sha(target)
# Exact untouched compiler-facing frontend matches the ordinary release.
released=p/'artifacts/stage2-vm-default-integration/ordinary-install/released-source'
frontend={}
for relative in ['tools/analyze_source.py','tools/symbolic_metadata.py']:
    assert sha(p/relative)==sha(released/relative);frontend[relative]=sha(p/relative)
binaries={};settings={}
for label,builddir in [('gnu','build-stage2-vm-proved-budget'),('portable','build-stage2-vm-proved-budget-portable'),('disabled','build-stage2-vm-proved-budget-disabled')]:
    folder=p/builddir;dest=out/label;dest.mkdir()
    binaries[label]={}
    for x in sorted(folder.glob('*.exe')):
        shutil.copyfile(x,dest/x.name);binaries[label][x.name]={'sha256':sha(dest/x.name),'origin':str(x)}
    assert binaries[label]['cholesky_runtime.exe']['sha256']==proof['binaries'][label]['sha256']
    library=folder/'libcholesky_core.a';shutil.copyfile(library,dest/library.name);binaries[label][library.name]={'sha256':sha(dest/library.name),'origin':str(library)}
    paths=[folder/'CMakeCache.txt',folder/'CTestTestfile.cmake',*sorted((folder/'CMakeFiles').rglob('flags.make')),*sorted((folder/'CMakeFiles').rglob('link.txt')),*sorted((folder/'CMakeFiles').rglob('includes_CXX.rsp'))]
    settings[label]={}
    for x in paths:
        relative=x.relative_to(folder);target=dest/'build-provenance'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);settings[label][relative.as_posix()]=sha(target)
for test,digest in ubsan['exe_sha256'].items():
    x=root/'ubsan'/(test+'.exe');assert sha(x)==digest;target=out/'ubsan'/x.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(x,target)
evidence={}
for name in ['build-evidence','policy-rebuild-evidence','contracts-evidence','contracts-evidence-v2','ctest-evidence','ubsan']:
    folder=root/name
    for x in sorted(folder.iterdir()):
        if x.is_file()and x.suffix in ['.json','.stdout','.stderr','.log','.cmd']:
            relative=x.relative_to(root);target=out/'evidence'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);evidence[relative.as_posix()]=sha(target)
for label in ['proved','unknown']:
    pass
auto=[r for r in proof['runs']if r['mode']=='proved-auto']
summary=[{'source':s['label'],'fresh_source':s['fresh_source'],'proved_matrices':sum(r['vm_budget_proved_matrices']for r in auto if r['source']==s['label']),'unknown_matrices':sum(r['vm_budget_unknown_matrices']for r in auto if r['source']==s['label'])}for s in proof['sources']]
manifest={'passed':True,'scope':'isolated first opt-in policy; no ordinary installation/performance/maximum execution','source_sha256':hashes,'source_deltas_from_initial_plan':source_deltas,'component_unchanged':True,'component_manifest_sha256':sha(stage/'component-acceptance/manifest.json'),'historical_dependency_supplement_sha256':sha(stage/'component-dependency-supplement/manifest.json'),'binaries':binaries,'build_provenance_sha256':settings,'evidence_sha256':evidence,'full_C_report_sha256':sha(root/'correctness/report.json'),'whole_C_comparisons':469,'actual_C_sources':15,'original_error_contract_groups':7,'error_modes_per_group':7,'cli_contracts':9,'GNU_full_CTest':15,'portable_small_CTest':11,'disabled_small_CTest':9,'UBSan_actual_exit_code':ubsan['exit_code'],'UBSan_exe_sha256':ubsan['exe_sha256'],'proof_status_by_source':summary,'proof_bound_peak':max(r['vm_budget_bound_peak']for r in auto),'effective_budget_max_in_this_small_gate':max(r['vm_effective_step_limit_max']for r in auto),'small_gate_does_not_test_raised_budget':True,'derived_contract_note':'Original934 fixed policy unchanged. Derived934 switches only runs whose nonboundary test limit is100000 to proved with default1e9; explicit original per-op boundary limits remain fixed. No claim934 all-proved boundaries.','native_FP_and_AUTO_sources_unchanged':True,'frontend_unchanged_sha256':frontend,'ordinary_sha256':sha(ordinary),'memory_sha256':sha(memory),'historical_core_unchanged_sha256':sha(core),'default_proof_CMake':False,'default_runtime_policy':'fixed','default_runtime_limit':1000000000,'maximum_execution_started':False,'performance_claim':False,'failed_initial_policy_test_retained':'contracts-evidence GNU10/11, native fixture incorrectly expected stage instead of original auto diagonal; fixed test only; unchanged runtime binaries','compiler_temp_note':'Each compile and C-oracle child inherits project F TEMP/TMP/TMPDIR; no system environment change; actual env/space in logs.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'manifest':str(out/'manifest.json'),'manifest_sha256':sha(out/'manifest.json'),'source_files':len(hashes),'runtime_sha256':{k:v['cholesky_runtime.exe']['sha256']for k,v in binaries.items()},'whole_C':469,'maximum_execution_started':False}),flush=True)
