"""Actual C full binary oracle, same arithmetic for AVX2/AVX512 and fallback."""
import hashlib,json,shutil,subprocess,time
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,make_input,run_runtime,exact_compare
from benchmark_extended import stress_input
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-avx512/correctness';root.mkdir(exist_ok=False)
    runtime=project/'build-stage2-avx512/cholesky_runtime.exe';shutil.copyfile(runtime,root/'runtime.exe');frozen=root/'runtime.exe';started=time.perf_counter();hashes={}
    paths=[project/'CMakeLists.txt',project/'CMakePresets.json',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),project/'tests/avx512_kernel_tests.cpp',Path(__file__).resolve(),project/'tools/analyze_source.py',project/'tools/evaluate_source.py',project/'tools/benchmark_extended.py']
    for p in paths:
        path=root/'source'/p.relative_to(project);path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,path);hashes[p.relative_to(project).as_posix()]=sha(path)
    report={'passed':False,'status':'running','runtime_sha256':sha(frozen),'source_sha256':hashes,'contract':'independently compiled actual source C -O2 -fno-fast-math -ffp-contract=off; every input/output/header byte; no tolerance','scope':'four actual C functions, plain and explicit FMA; both SIMD at same tile/thread config, auto/portable fallback; correctness costs only, no performance attribution','sources':[],'runs':[]}
    def save():
        report['wall_seconds']=time.perf_counter()-started;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    sources=[('scalar',project/'fixtures/cholesky_reference.c','cholesky_reference'),('page',project/'fixtures/official_naive_transcribed.c','cholesky'),('blocked',project/'fixtures/cholesky_blocked.c','cholesky_blocked'),('fma',project/'artifacts/build-ctest-pipeline/explicit-fma.c','cholesky')]
    shapes=[3,7,17,31,33,65,127,129]
    dense_shapes=[3,7,15,16,17,31,32,33,63,64,65,95,96,97,127,128,129,191,193,257]
    for label,source,function in sources:
        folder=root/label;folder.mkdir();target=folder/'source.c';shutil.copyfile(source,target);metadata=folder/'program.meta'
        analysis=analyze(target,metadata,'C:/Program Files/LLVM/bin/clang.exe',function)
        assert analysis['optimized']!='none' and (analysis['optimized'].endswith('_fma')==(label=='fma'))
        oracle=compile_oracle(target,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked')
        record={'label':label,'source_sha256':sha(target),'metadata_sha256':sha(metadata),'oracle_sha256':sha(oracle),'harness_sha256':sha(folder/'oracle.c'),'analysis':analysis};report['sources'].append(record)
        for family in ('subnormal','large','near-rank-one','signed-zero','dense'):
            ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin')
            if family=='dense':make_input(ip,dense_shapes)
            else:stress_input(ip,shapes,family)
            subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            configs=[(mode,b,4)for b in (7,16,32,64,96)for mode in ('avx2','avx512')]+[('portable',32,1),('auto',32,4)]
            for mode,b,count in configs:
                output=folder/(family+'-'+mode+f'-B{b}-t{count}.bin');metrics=run_runtime(frozen,metadata,ip,output,engine='tiled',tile_size=b,threads=count,block=7,simd=mode,structure='dense')
                expected='portable_ordered_lanes' if mode=='portable' else ('avx512'if mode=='avx512'else'avx2')+('_explicit_fma'if label=='fma'else'_separate_mul_add')
                assert metrics['vector_kernel']==expected and metrics['effective_tile_size']==b
                assert metrics['input_validation_kernel']==('scalar_finite'if mode=='portable'else'avx2_exponent_bits')
                report['runs'].append({'source':label,'family':family,'mode':mode,'input_sha256':sha(ip),'oracle_output_sha256':sha(ref),'metadata_sha256':sha(metadata),**metrics,**exact_compare(ref,output)});save()
            print(json.dumps({'source':label,'family':family,'comparisons':len(configs)}),flush=True)
    assert all(sha(project/name)==value for name,value in hashes.items()) and sha(runtime)==sha(frozen)
    assert sha(project/'build/cholesky_runtime.exe')=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    report.update(passed=True,status='complete',comparisons=len(report['runs']));save();print(json.dumps({'passed':True,'comparisons':len(report['runs']),'seconds':report['wall_seconds']}),flush=True)
if __name__=='__main__':main()
