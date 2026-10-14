"""Freeze the accepted decode-only candidate before subsequent VM experiments."""
import hashlib,json,shutil
from pathlib import Path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-prepared-vm-phase1'
    report=json.loads((root/'correctness/report.json').read_text())
    assert report['passed'] and report['comparisons']==172 and len(report['failures'])==7
    assert report['native_contract']['comparisons']==404
    for name,digest in report['source_sha256'].items():assert sha(project/name)==digest,name
    log=(root/'ctest.log').read_text();assert '100% tests passed, 0 tests failed out of 9' in log
    assert sha(project/'build/cholesky_runtime.exe')==report['ordinary_sha256']
    assert sha(project/'build-stage2-vm-decode/cholesky_runtime.exe')==report['runtime_sha256']
    target=root/'candidate-source';target.mkdir(exist_ok=False);hashes={}
    paths=[project/'CMakeLists.txt',project/'CMakePresets.json',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),*sorted((project/'tests').glob('*.cpp')),*sorted((project/'tools').glob('*.py'))]
    paths += [project/'build-stage2-vm-decode'/name for name in ['CMakeCache.txt','CTestTestfile.cmake','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt','CMakeFiles/prepared_vm_tests.dir/flags.make','CMakeFiles/prepared_vm_tests.dir/link.txt']]
    for path in paths:
        name=path.relative_to(project).as_posix();saved=target/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,saved);hashes[name]=sha(saved)
    shutil.copyfile(project/'build-stage2-vm-decode/cholesky_runtime.exe',root/'candidate.exe')
    shutil.copyfile(project/'build-stage2-vm-decode/prepared_vm_tests.exe',root/'native-contract.exe')
    memory=sha(project/'build-memory/cholesky_runtime.exe');assert memory=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
    manifest={'passed':True,'phase':'1 typed operands only; vector stack and switch unchanged; no TOS/goto/cache/fusion','default':'CHOL_PREPARED_VM OFF; backend legacy even in experimental build','ordinary_sha256':report['ordinary_sha256'],'memory_sha256':memory,'candidate_sha256':sha(root/'candidate.exe'),'native_contract_binary_sha256':sha(root/'native-contract.exe'),'source_sha256':hashes,'proof_sha256':{name:sha(root/name)for name in ['initial-plan.json','correctness/report.json','ctest.log']},'correctness':{'whole_file_actual_C':172,'actual_VM_required_sources':9,'families':43,'ordinary_error_contracts':7,'direct_API_opcode_comparisons':404,'ctest':'9/9; full native/frontend regression'},'preparation':'per matrix; timed inside compute; retained plan bytes recorded; original Metadata and PROGRAM intact','performance_attribution':False}
    (root/'phase1-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'candidate_sha256':manifest['candidate_sha256'],'source_files':len(hashes),'manifest':str(root/'phase1-manifest.json')}))
if __name__=='__main__':main()
