"""Append immutable historical dependencies; never rewrite component07481."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-proved-budget';old=stage/'component-acceptance';out=stage/'component-dependency-supplement';out.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
manifest=json.loads((old/'manifest.json').read_text(encoding='utf-8'))
original=json.loads((stage/'initial-plan.json').read_text(encoding='utf-8'))
historical=p/'artifacts/stage2-vm-default-integration/ordinary-install/released-source'
files={}
for x in sorted((historical/'include').rglob('*.hpp')):
    relative=x.relative_to(historical)
    if relative.as_posix()in original['source_sha256']:assert sha(x)==original['source_sha256'][relative.as_posix()]
    target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);files['source/'+relative.as_posix()]={'sha256':sha(target),'origin':str(x)}
for relative in ['src/vm_step_bound.cpp','include/cholesky/vm_step_bound.hpp','tests/vm_step_bound_tests.cpp']:
    x=old/'source'/relative;assert sha(x)==manifest['source_sha256'][relative]
    target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);files['source/'+relative]={'sha256':sha(target),'origin':str(x)}
assert sha(out/'source/include/cholesky/runtime.hpp')=='f1b56b5526e65df389036c579300a9c8a9f01d99e24899493e3369a51b75bd0e'
for source,relative,expected in [
    (Path(manifest['existing_frozen_core_library']['path']),'libcholesky_core.a',manifest['existing_frozen_core_library']['sha256']),
    (p/'build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make','core-flags.make',manifest['existing_frozen_core_library']['flags_sha256'])]:
    assert sha(source)==expected;target=out/relative;shutil.copyfile(source,target);files[relative]={'sha256':sha(target),'origin':str(source)}
target=out/'source/tools'/Path(__file__).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,target);files['source/tools/'+target.name]={'sha256':sha(target),'origin':str(Path(__file__))}
data={'passed':True,'supplements_manifest_sha256':sha(old/'manifest.json'),'historical_runtime_header_matches_initial_plan':True,'core_library_matches_original_component':True,'files':files,'restore_compile_recipe':manifest['compile_command'],'recipe_note':'Replace -I with this supplement/source/include, proof/test paths with supplement/source counterparts, and core library with supplement/libcholesky_core.a; do not use current Options header with old ABI library. Use F-drive process TEMP/TMP/TMPDIR. Original manifest remains immutable.','initial_attempt_clarification':'Ignored POP-operand mutation was corrected. Final component also added full work charges for CFG/vector/State copies before07481 acceptance. VM/native execution code and old core library remained unchanged.'}
(out/'manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'manifest':str(out/'manifest.json'),'manifest_sha256':sha(out/'manifest.json'),'files':len(files)}),flush=True)
