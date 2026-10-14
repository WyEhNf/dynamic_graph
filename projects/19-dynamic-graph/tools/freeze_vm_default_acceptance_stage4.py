"""Freeze actual Stage4 functional gates and rollback; no large matrix hashes."""
import hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path

p=Path(__file__).resolve().parents[1]
root=p/'artifacts/stage2-vm-default-integration'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def read(x):return json.loads(Path(x).read_text(encoding='utf-8'))
def copy(x,dest):
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,dest)
    assert sha(x)==sha(dest)
    return sha(dest)
assert not(root/'acceptance-manifest.json').exists()
proof=read(root/'correctness/report.json')
assert proof['passed'] and proof['status']=='complete' and proof['comparisons']==378
assert len(proof['sources'])==13 and len(proof['runs'])==378 and len(proof['failures'])==7
assert len({(r['source'],r['family'])for r in proof['runs']})==63
for name,digest in proof['source_sha256'].items():assert sha(p/name)==digest,name
for f in proof['failures']:
    assert len(f['results'])==6 and all(r['exit_code']==1 for r in f['results'])
    assert len({r['stderr']for r in f['results']})==1

ctest={}
for label in ['gnu','portable']:
    log=root/(label+'-ctest.log');text=log.read_text(encoding='utf-8')
    assert '100% tests passed, 0 tests failed out of 12'in text
    assert len(re.findall(r'\d+/12 Test.*Passed',text))==12
    ctest[label]={'passed':12,'seconds':float(re.search(r'Total Test time \(real\) = ([0-9.]+)',text)[1]),'path':str(log),'sha256':sha(log),'actual_exit_code':0}
ubsan=root/'ubsan-build.log';u=ubsan.read_text(encoding='utf-8')
assert '"comparisons":934'in u and '"default":"decoded-threaded"'in u
assert 'runtime error:'not in u

ordinary='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
memory='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
assert sha(p/'build/cholesky_runtime.exe')==sha(root/'ordinary4f73.exe')==ordinary
assert sha(p/'build-memory/cholesky_runtime.exe')==memory

# Preserve real original4f73 provenance, not the later Phase3 source-before.
release=p/'artifacts/stage2-runtime-release';historic=read(release/'release-manifest.json')
rollback=root/'rollback4f73';rollback.mkdir(exist_ok=False)
for name,digest in historic['source_sha256'].items():
    assert sha(release/'released-source'/name)==digest,name
shutil.copytree(release/'released-source',rollback/'released-source')
shutil.copytree(release/'released-build',rollback/'released-build')
copy(release/'release-manifest.json',rollback/'release-manifest.json')
assert copy(release/'runtime.exe',rollback/'cholesky_runtime.exe')==ordinary
rollback_hashes={x.relative_to(rollback).as_posix():sha(x)for x in sorted(rollback.rglob('*'))if x.is_file()}
(rollback/'snapshot-manifest.json').write_text(json.dumps({'runtime_sha256':ordinary,'source_provenance':'original4f73 release; source-before belongs to Phase3','sha256':rollback_hashes,'binary_rollback':'exact executable copy','runtime_rebuild':'historical source; BUILD_TESTING=OFF; no fresh rebuild claimed'},indent=2),encoding='utf-8')

snap=root/'candidate-source';snap.mkdir(exist_ok=False)
files=[p/'CMakeLists.txt',p/'CMakePresets.json',p/'docs/stage2-vm-default-integration.md',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),*sorted((p/'tools').glob('*.py')),*sorted((p/'tools').glob('*.cmd'))]
for build in ['build-stage2-vm-default','build-stage2-vm-default-portable','build-stage2-vm-default-legacy']:
    files+=[p/build/'CMakeCache.txt',p/build/'CMakeFiles/cholesky_core.dir/flags.make',p/build/'CMakeFiles/cholesky_runtime.dir/link.txt']
hashes={x.relative_to(p).as_posix():copy(x,snap/x.relative_to(p))for x in files}
flags=(p/'build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make').read_text()
baseline=(p/'artifacts/stage2-prepared-vm-phase3/candidate-source/build-stage2-vm-threaded/CMakeFiles/cholesky_core.dir/flags.make').read_text()
assert flags==baseline,'accepted production compile options changed'
binaries={}
for build,label in [('build-stage2-vm-default','candidate.exe'),('build-stage2-vm-default-portable','portable-candidate.exe'),('build-stage2-vm-default-legacy','legacy-candidate.exe')]:
    binaries[label]={'path':str(root/label),'sha256':copy(p/build/'cholesky_runtime.exe',root/label)}
assert binaries['candidate.exe']['sha256']==proof['backends']['new-default']['sha256']
assert binaries['portable-candidate.exe']['sha256']==proof['backends']['portable-default']['sha256']
contracts=[]
for build in ['build-stage2-vm-default','build-stage2-vm-default-portable','build-stage2-vm-default-legacy']:
    names=['vm_default_selection_tests'] if build.endswith('legacy')else ['vm_default_selection_tests','threaded_vm_tests','prepared_vm_tests','runtime_tests','prepared_vm_tos2_tests']
    for name in names:
        exe=p/build/(name+'.exe');proc=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
        label=build+'-'+name;out=root/'contracts'/(label+'.stdout');err=root/'contracts'/(label+'.stderr');out.parent.mkdir(exist_ok=True)
        out.write_text(proc.stdout,encoding='utf-8');err.write_text(proc.stderr,encoding='utf-8')
        frozen=root/'contracts'/(label+'.exe');copy(exe,frozen)
        contracts.append({'label':label,'actual_exit_code':proc.returncode,'exe':str(frozen),'exe_sha256':sha(frozen),'stdout':str(out),'stdout_sha256':sha(out),'stderr':str(err),'stderr_sha256':sha(err)})
for name in ['threaded-ubsan','default-ubsan']:
    exe=root/(name+'.exe');proc=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
    assert 'runtime error:'not in proc.stderr
    out=root/'contracts'/(name+'.stdout');err=root/'contracts'/(name+'.stderr')
    out.write_text(proc.stdout,encoding='utf-8');err.write_text(proc.stderr,encoding='utf-8')
    contracts.append({'label':name,'actual_exit_code':proc.returncode,'exe':str(exe),'exe_sha256':sha(exe),'stdout':str(out),'stdout_sha256':sha(out),'stderr':str(err),'stderr_sha256':sha(err)})
evidence={}
for build in ['build-stage2-vm-default','build-stage2-vm-default-portable']:
    for kind in ['pipeline','helpers','while','integer-selectors']:
        old=p/'artifacts'/(build+'-ctest-'+kind)
        for x in sorted(old.glob('*report.json')):
            name=x.relative_to(p).as_posix();evidence[name]=copy(x,root/'ctest-evidence'/build/kind/x.name)
    x=p/build/'Testing/Temporary/LastTest.log';evidence[x.relative_to(p).as_posix()]=copy(x,root/'ctest-evidence'/build/'LastTest.log')
archive=read(root/'archive-manifest.json')
for name,digest in archive['phase3_source_before_sha256'].items():assert sha(root/'source-before'/name)==digest
manifest={'passed':True,'status':'isolated functional acceptance; ordinary install and maximum shape pending','created_at_utc':datetime.now(timezone.utc).isoformat(),'binaries':binaries,'source_sha256':hashes,'source_count':len(hashes),'ctest':ctest,'contracts':contracts,'UBSan_compile_log_sha256':sha(ubsan),'correctness':{'report':str(root/'correctness/report.json'),'sha256':sha(root/'correctness/report.json'),'sources':13,'families':63,'whole_C_outputs':378,'failures':7,'backends':6,'elapsed_seconds':proof['elapsed_seconds']},'ctest_evidence_sha256':evidence,'GNU_core_flags_equal_accepted_phase3':True,'production_FP_flags':'-fno-fast-math -ffp-contract=off; SIMD TU -mavx2 -mfma unchanged','ordinary_installed_sha256':ordinary,'memory_installed_sha256':memory,'rollback4f73_manifest_sha256':sha(rollback/'snapshot-manifest.json'),'source_before_provenance':'later frozen Phase3; not4f73 original source','default_step_limit':1000000000,'native_AUTO_and_Metadata_unchanged':True,'maximum_shape_started':False,'performance_started':False,'plan_sha256':sha(root/'run-plan.json')}
(root/'acceptance-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'acceptance_sha256':sha(root/'acceptance-manifest.json'),'binaries':binaries,'source_count':len(hashes),'contracts':len(contracts),'whole_C_outputs':378,'GNU_ctest':12,'portable_ctest':12,'maximum_shape_started':False},indent=2))
