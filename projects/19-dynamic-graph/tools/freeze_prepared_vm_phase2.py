"""Freeze the accepted TOS2 candidate and its true phase1 baseline."""
import hashlib,json,shutil
from pathlib import Path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-prepared-vm-phase2';report=json.loads((root/'correctness/report.json').read_text());assert report['passed'] and report['comparisons']==290 and len(report['sources'])==12 and len(report['failures'])==7
    assert report['native_contract']['phase1_cases']==404 and report['native_contract']['comparisons']==480 and report['native_contract']['raw_stack_operations']==100000
    for name,digest in report['source_sha256'].items():assert sha(p/name)==digest,name
    assert '100% tests passed, 0 tests failed out of 10' in (root/'ctest.log').read_text()
    assert sha(p/'build-stage2-vm-tos2/cholesky_runtime.exe')==report['runtime_sha256']
    oldsha='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c';memsha='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
    assert sha(p/'build/cholesky_runtime.exe')==oldsha and sha(p/'build-memory/cholesky_runtime.exe')==memsha
    assert sha(root/'phase1-baseline.exe')==report['phase1_sha256']
    snapshot=root/'candidate-source';snapshot.mkdir(exist_ok=False);hashes={}
    paths=[p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),*sorted((p/'tools').glob('*.py'))]
    paths += [p/'build-stage2-vm-tos2'/name for name in ['CMakeCache.txt','CTestTestfile.cmake','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt','CMakeFiles/prepared_vm_tos2_tests.dir/flags.make','CMakeFiles/prepared_vm_tos2_tests.dir/link.txt']]
    for path in paths:
        name=path.relative_to(p).as_posix();saved=snapshot/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,saved);hashes[name]=sha(saved)
    shutil.copyfile(p/'build-stage2-vm-tos2/cholesky_runtime.exe',root/'candidate.exe');shutil.copyfile(p/'build-stage2-vm-tos2/prepared_vm_tos2_tests.exe',root/'native-contract.exe')
    manifest={'passed':True,'phase':'two scalar FP64 stack top fields with cold vector; original switch/decoded plan/opcodes/step checks; no goto/fusion/plan cache','candidate_sha256':sha(root/'candidate.exe'),'native_contract_exe_sha256':sha(root/'native-contract.exe'),'phase1_baseline_sha256':report['phase1_sha256'],'ordinary_sha256':oldsha,'memory_sha256':memsha,'source_sha256':hashes,'proof_sha256':{name:sha(root/name)for name in ['initial-plan.json','correctness/report.json','ctest.log']},'correctness':{'actual_C_complete_files':290,'sources':12,'families':58,'fresh_sources':2,'fresh_shapes':[3,11,67,139,193,257],'error_CLI_contracts':7,'opcode_count':33,'original_phase1_cases':404,'triple_contract_cases':480,'raw_payload_operations':100000,'ctest':'10/10'},'preparation':'per-matrix decode included in compute; cache belongs only to this invocation; extra scalar fields not assumed to stay in hardware registers','default':'OFF; even enabled build defaults legacy; ordinary 4f73 frozen','N10000':'prior phase1 while-copy required explicit1e10 for1.7b steps; not default-budget or TOS2 maximum-shape pass','performance_started':False}
    (root/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'candidate_sha256':manifest['candidate_sha256'],'source_files':len(hashes),'manifest':str(root/'candidate-manifest.json')}))
if __name__=='__main__':main()
