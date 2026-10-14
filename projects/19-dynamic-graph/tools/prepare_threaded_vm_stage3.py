"""One-time source preparation and historical snapshot; never a runtime generator."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1]
root=p/'artifacts/stage2-prepared-vm-phase3'
root.mkdir(exist_ok=False)
snap=root/'source-original';snap.mkdir()
hashes={}
for path in [p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp'))]:
    name=path.relative_to(p).as_posix();saved=snap/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,saved);hashes[name]=hashlib.sha256(saved.read_bytes()).hexdigest()
for phase,name in [('phase1','phase1-baseline.exe'),('phase2','phase2-baseline.exe')]:shutil.copyfile(p/f'artifacts/stage2-prepared-vm-{phase}/candidate.exe',root/name)
machine=p/'artifacts/stage2-vm-threaded-plan/machine-code'
report={'status':'machine diagnosis, before implementation/testing','original_sources':hashes,'machine_code_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in machine.glob('*.asm')},'phase1_dispatch':['0x140007b13','0x140007b80'],'phase2_decoded_dispatch':['0x140007bc3','0x140007c30'],'actual_pop_calls':'phase1 0x140001f00, phase2 same address; checks vector.empty then reads back and decrements end','pc_steps':'original steps+budget before fetch; PC old+1; decoded 32-byte record indexing','decision':'one independent33-label computedgoto backend using phase1 vector stack; no TOS2/fusion/cache/default promotion','performance_authorized':False}
(root/'initial-machine-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'snapshot_sources':len(hashes),'root':str(root)}))
