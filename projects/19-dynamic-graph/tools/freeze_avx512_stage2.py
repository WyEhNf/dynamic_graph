"""Freeze tested optional runtime; never replace ordinary or prior evidence."""
import json,shutil,subprocess,re
from pathlib import Path
from datetime import datetime,timezone
from benchmark_grain48_stage2 import sha

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-avx512';out=root/'candidate-manifest.json'
    if out.exists():raise SystemExit('Candidate already frozen')
    proof=json.loads((root/'correctness/report.json').read_text())
    binary=project/'build-stage2-avx512/cholesky_runtime.exe'
    assert proof['passed'] and proof['comparisons']==240 and sha(binary)==proof['runtime_sha256']
    assert all(sha(project/k)==v for k,v in proof['source_sha256'].items())
    log=(root/'ctest.log').read_text()
    assert '100% tests passed, 0 tests failed out of 9' in log
    native=subprocess.run([str(project/'build-stage2-avx512/avx512_kernel_tests.exe')],capture_output=True,text=True,check=True)
    native=json.loads(native.stdout);assert native=={'passed':True,'gate_rejections':11,'ieee754_goldens':16,'guard_page_cases':1400}
    native_path=root/'native-kernel-tests-final.json';native_path.write_text(json.dumps(native,indent=2),encoding='utf-8')
    startup={}
    for label,symbol in (('entry','main'),('detector','_ZN4chol24detect_simd_capabilitiesEv')):
        result=subprocess.run(['E:/mingw64/bin/objdump.exe','-d','--disassemble='+symbol,str(binary)],capture_output=True,text=True,check=True).stdout
        assert '<'+symbol+'>:' in result and not re.search(r'\b(?:zmm|ymm)\d+\b',result,re.I)
        path=root/('binary-'+label+'.asm');path.write_text(result,encoding='utf-8');startup[label]={'sha256':sha(path),'vector_register_matches':0}
    baseline=project/'build/cholesky_runtime.exe';memory=project/'build-memory/cholesky_runtime.exe'
    assert sha(baseline)=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    assert sha(memory)=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
    frozen=root/'candidate';frozen.mkdir();shutil.copyfile(binary,frozen/'runtime.exe');files={}
    paths=[project/'build-stage2-avx512/CMakeCache.txt',project/'build-stage2-avx512/CMakeFiles/cholesky_core.dir/flags.make',project/'build-stage2-avx512/CMakeFiles/cholesky_runtime.dir/flags.make',project/'build-stage2-avx512/CMakeFiles/cholesky_runtime.dir/link.txt',project/'build-stage2-avx512/CTestTestfile.cmake',project/'README.md',project/'docs/stage2-avx512.md',Path(__file__).resolve(),project/'tools/benchmark_avx512_stage2.py']
    for p in paths:
        target=frozen/p.relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);files[p.relative_to(project).as_posix()]=sha(target)
    plan=root/'performance/run-plan.json';performance=json.loads(plan.read_text());assert performance['runtime_sha256']==sha(binary) and performance['planned_records']==60
    manifest={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_sha256':sha(binary),'ordinary_sha256':sha(baseline),'memory_sha256':sha(memory),'source_sha256':proof['source_sha256'],'frozen_auxiliary_sha256':files,'startup_binary_disassembly':startup,'functional_report_sha256':sha(root/'correctness/report.json'),'native_final_sha256':sha(native_path),'ctest_log_sha256':sha(root/'ctest.log'),'ctest':{'passed':9,'total':9,'seconds':181.45},'performance_plan_sha256':sha(plan),'performance_started':False,'default_policy':'CHOL_BUILD_AVX512_KERNEL OFF; packed OFF; AUTO remains AVX2/portable and original tile geometry; ordinary4f73 and memory unchanged','candidate':'Opt-in AVX512F4x16 update only; original k order/strict arithmetic, AVX2 panel+scan; CPU+OS gate; no automatic promotion or score claim'}
    out.write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'frozen':True,'runtime_sha256':sha(binary),'startup_disassembly_no_ymm_zmm':True}),flush=True)
if __name__=='__main__':main()
