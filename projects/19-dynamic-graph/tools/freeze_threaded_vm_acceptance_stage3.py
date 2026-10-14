"""Freeze completed functional acceptance; performance remains a separate stage."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-prepared-vm-phase3'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
small=json.loads((root/'small-contract-manifest.json').read_text());proof=json.loads((root/'correctness/report.json').read_text());plan=root/'performance/run-plan.json'
assert proof['passed'] and proof['comparisons']==378 and len(proof['sources'])==13 and len(proof['failures'])==7
assert '100% tests passed, 0 tests failed out of 11' in (root/'ctest.log').read_text()
assert all(sha(p/name)==digest and sha(root/'candidate-source'/name)==digest for name,digest in small['source_sha256'].items())
assert sha(p/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
assert sha(p/'build-memory/cholesky_runtime.exe')=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
assert sha(p/'build-stage2-vm-threaded/cholesky_runtime.exe')==small['executable_sha256']['candidate.exe']
assert sha(plan)=='3dc6440370ee8ed18f4bd8c68690e71f5a25e0ff01718c125904da2dea3d2ec6'and not(root/'performance/report.json').exists()
snap=root/'acceptance-source';snap.mkdir(exist_ok=False);hashes={}
for name in ['tools/test_threaded_vm_stage3.py','tools/prepare_threaded_benchmark_script_stage3.py','tools/benchmark_threaded_vm_stage3.py','tools/freeze_threaded_vm_acceptance_stage3.py','docs/stage2-prepared-vm-phase3.md','README.md']:
    target=snap/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/name,target);hashes[name]=sha(target)
manifest={'status':'functional acceptance complete; performance prepared/not started','candidate_sha256':small['executable_sha256']['candidate.exe'],'portable_sha256':small['executable_sha256']['portable-candidate.exe'],'source_sha256':small['source_sha256'],'acceptance_sources_sha256':hashes,'evidence_sha256':{name:sha(root/name)for name in ['small-contract-manifest.json','correctness/report.json','ctest.log','threaded-initial.asm','performance/run-plan.json']},'native_contracts':'GNU934/fallback934/UBSan934; old404/480+100000payload; source snapshot126files','actual_C_files':378,'C_sources':13,'families':63,'CLI_failures':7,'ctest':'11/11 actual73743 exit0 113.02s','performance_plan':{'records':130,'pairs':65,'cases':13,'rounds':5,'source_freshness':'12prior performance sources, one fresh source+shape; all optimizednone','started':False},'default':'CHOL_THREADED_VM OFF; enabled defaultlegacy; ordinary4f73 andmemory7da06 frozen; AUTO/nativeFP/Metadata untouched','scope':'computedgoto direct33 handlers only, vectorstack. GCC also auto-inlines unchanged pop and tailmerges to3sites; no pure branch attribution.'}
(root/'acceptance-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'candidate_sha256':manifest['candidate_sha256'],'sources':len(manifest['source_sha256'])+len(hashes),'performance_started':False}))
