"""Phase1 decoded operands: real VM-required C and unchanged original output."""
import json,shutil,subprocess,time,hashlib
from pathlib import Path
from analyze_source import analyze
from evaluate_source import compile_oracle,make_input,exact_compare
from benchmark_extended import stress_input
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-prepared-vm-phase1/correctness';root.mkdir(exist_ok=False)
    runtime=project/'build-stage2-vm-decode/cholesky_runtime.exe';old=project/'artifacts/stage2-prepared-vm-phase1/ordinary-baseline.exe'
    shutil.copyfile(runtime,root/'runtime.exe');runtime=root/'runtime.exe'
    assert sha(old)=='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c'
    start=time.perf_counter();hashes={}
    paths=[project/'CMakeLists.txt',project/'CMakePresets.json',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),project/'tests/prepared_vm_tests.cpp',Path(__file__).resolve(),project/'tools/analyze_source.py',project/'tools/c_frontend.py',project/'tools/semantic_cholesky.py',project/'tools/evaluate_source.py',project/'tools/benchmark_extended.py']
    for p in paths:
        target=root/'source'/p.relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);hashes[p.relative_to(project).as_posix()]=sha(target)
    native=subprocess.run([str(project/'build-stage2-vm-decode/prepared_vm_tests.exe')],capture_output=True,text=True,check=True);native=json.loads(native.stdout)
    report={'passed':False,'status':'running','phase':'decode only; original vector stack and switch; no TOS/goto/fusion/cache','runtime_sha256':sha(runtime),'ordinary_sha256':sha(old),'source_sha256':hashes,'native_contract':native,'sources':[],'runs':[],'failures':[],'performance_attribution':False}
    def save():report['seconds']=time.perf_counter()-start;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    pipeline=project/'artifacts/build-release-stage2-metadata-ctest-pipeline';helpers=project/'artifacts/build-release-stage2-metadata-ctest-helpers'
    sources=[('changed-arithmetic',pipeline/'changed-arithmetic.c','cholesky',False),('changed-SSA',pipeline/'changed-ssa-arithmetic.c','cholesky',False),('generic-if-while',pipeline/'generic.c','transform',False),('int-arithmetic',pipeline/'typed-integer-arithmetic.c','transform',False),('int-conversion',pipeline/'ssa-integer-conversion.c','transform',True),('deep-SSA40',helpers/'deep-ssa-40.c','transform',False),('nested-helpers',helpers/'nested-multiple-arguments.c','transform',False),('SSA-conditional',helpers/'ssa-branch-expression.c','transform',False),('unused-double',helpers/'unused-double-cholesky.c','cholesky',False)]
    for label,source,function,integer in sources:
        folder=root/label;folder.mkdir();target=folder/'source.c';shutil.copyfile(source,target);metadata=folder/'program.meta';analysis=analyze(target,metadata,'C:/Program Files/LLVM/bin/clang.exe',function)
        assert analysis['optimized']=='none'
        oracle=compile_oracle(target,function,folder,'E:/mingw64/bin/gcc.exe')
        report['sources'].append({'label':label,'actual_source':str(source),'source_sha256':sha(target),'metadata_sha256':sha(metadata),'oracle_binary_sha256':sha(oracle),'harness_sha256':sha(folder/'oracle.c'),'analysis':analysis})
        for family in (('dense','signed-zero','subnormal')if integer else ('dense','signed-zero','subnormal','large','near-rank-one')):
            ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin')
            sizes=[3,7,17,31,33,63,64,65,127,129]
            if family=='dense':make_input(ip,sizes)
            else:stress_input(ip,sizes,family)
            subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
            records=[]
            for backend in ('ordinary4f73','legacy','decoded','new-default'):
                output=folder/(family+'-'+backend+'.bin');exe=old if backend=='ordinary4f73'else runtime
                command=[str(exe), '--metadata',str(metadata),'--input',str(ip),'--output',str(output),'--engine','auto','--scheduler','parallel','--threads','4','--vm-step-limit','1000000000']
                if backend in ('legacy','decoded'):command+=['--vm-backend',backend]
                begin=time.perf_counter();result=subprocess.run(command,capture_output=True,text=True,check=True);metrics=json.loads(result.stdout)
                assert metrics['selected_engine']=='vm'
                if backend!='ordinary4f73':assert metrics['vm_backend']==('decoded'if backend=='decoded'else'legacy')
                row={'source':label,'family':family,'backend':backend,'input_sha256':sha(ip),'original_c_output_sha256':sha(ref),'process_wall_ms':(time.perf_counter()-begin)*1000,**metrics,**exact_compare(ref,output)}
                records.append(row);report['runs'].append(row);save()
            assert records[1]['vm_steps']==records[2]['vm_steps']==records[3]['vm_steps']
            print(json.dumps({'source':label,'family':family,'byte_comparisons':4,'steps':records[2]['vm_steps']}),flush=True)
    # Existing executed source faults: compare exact CLI text, status, outputs,
    # including auto fallback; no C oracle is executed for undefined behavior.
    valid=root/'failure-input.bin';make_input(valid,[3])
    bad_sources=['int-add-overflow','int-multiply-overflow','int-negate-minimum','int-divide-minimum','int-remainder-minimum','fp-to-int-range','integer-zero-divisor']
    for label in bad_sources:
        folder=root/('failure-'+label);folder.mkdir();target=folder/'source.c';shutil.copyfile(pipeline/(label+'.c'),target);metadata=folder/'program.meta';analyze(target,metadata,'C:/Program Files/LLVM/bin/clang.exe','transform');failures=[]
        for backend in ('ordinary4f73','legacy','decoded'):
            output=folder/(backend+'.bin');exe=old if backend=='ordinary4f73'else runtime
            command=[str(exe),'--metadata',str(metadata),'--input',str(valid),'--output',str(output),'--engine','auto']
            if backend!='ordinary4f73':command+=['--vm-backend',backend]
            r=subprocess.run(command,capture_output=True,text=True);assert r.returncode==1 and not output.exists() and not Path(str(output)+'.partial').exists();failures.append({'backend':backend,'returncode':r.returncode,'stderr':r.stderr})
        assert all(r['stderr']==failures[0]['stderr']for r in failures)
        report['failures'].append({'source':label,'source_sha256':sha(target),'metadata_sha256':sha(metadata),'results':failures});save()
    assert all(sha(project/name)==value for name,value in hashes.items())
    assert sha(project/'build/cholesky_runtime.exe')==sha(old)
    report.update(passed=True,status='complete',comparisons=len(report['runs']));save();print(json.dumps({'passed':True,'comparisons':report['comparisons'],'source_fault_contracts':len(report['failures']),'seconds':report['seconds']}),flush=True)
if __name__=='__main__':main()
