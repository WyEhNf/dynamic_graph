"""Archive historical ordinary EXE and current phase3 sources before defaults change."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-vm-default-integration';root.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
ordinary=p/'build/cholesky_runtime.exe';old=p/'artifacts/stage2-prepared-vm-phase1/ordinary-baseline.exe'
digest='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
assert sha(ordinary)==sha(old)==digest
shutil.copyfile(ordinary,root/'ordinary4f73.exe')
snap=root/'source-before';snap.mkdir();hashes={}
for path in [p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp'))]:
    name=path.relative_to(p).as_posix();dest=snap/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);hashes[name]=sha(dest)
manifest={'status':'historical archive before integration edits; no compile/test started','ordinary_sha256':digest,'ordinary_old_source_manifest':'artifacts/stage2-runtime-release/release-manifest.json (historical release provenance, not current phase3 source)','phase3_source_before_sha256':hashes,'phase3_exe_sha256':sha(p/'artifacts/stage2-prepared-vm-phase3/candidate.exe'),'native_defaults':'AUTO tile/nativeFP/Metadata behavior untouched; memory EXE not installed/rebuilt','budget_default':1000000000}
(root/'archive-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'archive':str(root),'sha256':digest,'source_files':len(hashes)}))
