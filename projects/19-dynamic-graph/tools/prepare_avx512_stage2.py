"""Freeze feature detection, actual AVX2 assembly and ISA sources before coding."""
import hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-avx512';target=root/'initial-plan.json'
    if target.exists():raise SystemExit('Refusing to overwrite AVX512 plan')
    cpu=json.loads((root/'cpu-features.json').read_text());assert cpu['usable_avx512f'] and cpu['gcc_builtin_avx512f'] and cpu['xcr0']&0xe6==0xe6
    assert sha(project/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    files=['CMakeLists.txt','CMakePresets.json','include/cholesky/runtime.hpp','tools/cpu_features_probe.cpp','tools/prepare_avx512_stage2.py']+[str(p.relative_to(project)).replace('\\','/')for p in sorted((project/'src').glob('*.cpp'))]
    hashes={}
    for name in files:
        out=root/'baseline-source'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,out);hashes[name]=sha(out)
    shutil.copyfile(project/'build/cholesky_runtime.exe',root/'ordinary-baseline.exe')
    plan={'prepared_at_utc':datetime.now(timezone.utc).isoformat(),'cpu_features':cpu,'cpu_probe_source_sha256':sha(project/'tools/cpu_features_probe.cpp'),'cpu_probe_exe_sha256':sha(root/'cpu_features_probe.exe'),'cpuid_method':'CPUID leaf1 XSAVE/OSXSAVE/AVX/FMA; leaf7 F/DQ/BW/VL; gated XGETBV0; xcr0 mask0xe6; no AVX launch code','baseline_runtime_sha256':sha(root/'ordinary-baseline.exe'),'baseline_source_sha256':hashes,'baseline_avx2_object_sha256':sha(project/'build/CMakeFiles/cholesky_core.dir/src/simd_kernel.cpp.obj'),'assembly_sha256':sha(root/'baseline-avx2.asm'),
    'primary_refs':[{'url':'https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html','application':'AVX512F packed double mul/add/load, explicit fmadd; default MXCSR, no embedded rounding or SAE'}, {'url':'https://www.intel.com/content/dam/develop/external/us/en/documents/cpp_compiler_classic.pdf','application':'Official packed-double arithmetic/FMA intrinsic semantics'}, {'url':'https://cdrdv2-public.intel.com/843827/253665-sdm-vol-1-dec-24.pdf','application':'CPUID features and XSAVE/OSXSAVE/XCR0 bits1,2,5,6,7 required'}, {'url':'https://docs.amd.com/api/khub/documents/Fk9hEabDNdOiD4PcQu7EYw/content','application':'EPYC041 Zen4 uses two sequential256-bit internal paths; no assumption of2x throughput'}, {'url':'https://docs.amd.com/api/khub/documents/f5vEE9HFY50eZwgTAuMMmA/content','application':'AMD58020 optimization guide isolated-mavx512f toolchain support; avoid global ISA flags'}, {'url':'https://gpuopen.com/gdc-presentations/2024/GDC2024_AMD_Ryzen_Processor_Software_Optimization.pdf','application':'Official Ryzen optimization methods; 57647 listed but old57647 directURL redirects, not used as read source'}],
    'assembly_observation':'ordinary AVX2 four-row/eight-column loop0x938..0x9b5:8 YMMacc,4broadcast,2factorloads,8mul+8add per32outputs; no vector spill to stack in this k-loop. ABI prologue saves are not inner-loop spills.',
    'candidate':'AVX512F four rows by16columns,8ZMMacc, unchanged ascending k per cell and operands; scalar tail, diagonal bounded8-lane loads. Only explicitSIMDmode. No repeated8-rowAVX2 experiment.',
    'strict_arithmetic':'Plain source separate mul then add accumulation before separate A-sum subtraction in factor/solve; no implicit FMA/reassociation. Actualfma source uses512fmadd and std::fma tails.',
    'build':'New build-stage2-avx512; CHOL_BUILD_AVX512_KERNEL defaultOFF; standalone TU -mavx512f -mfma only, generic detector/entry baselineISA, FP64 flags unchanged, packedOFF/autoAVX2 unchanged/ordinary release frozen',
    'correctness_first':'Independent native bitgoldens, signedzero/subnormal/boundary operands/odd tails/guardpages; actual C plain and explicitfma full binary files across shapes and workers; forced modes and auto fallback verified. No candidate/Python numerical oracle.',
    'performance_not_started':True,'performance_gate':'After correct byte tests and frozen binary/metadata/inputs/C hashes, request root exclusive window. Predeclare fixed geometries B96/B128 AVX2 vsAVX512 on dense6145/8193/10000 actual frozen originalC. Every trial+cost+negative retained; no AUTO promotion or fitted threshold.'}
    target.write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'usable_avx512f':True,'plan':str(target)}))
if __name__=='__main__':main()
