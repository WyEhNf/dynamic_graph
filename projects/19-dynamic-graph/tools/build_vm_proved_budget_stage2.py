"""Isolated enabled/portable/disabled builds; explicit phases and frozen logs."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-vm-proved-budget/runtime-integration'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['build','contracts','ctest','policy-rebuild'],required=True);parser.add_argument('--label',default='');parser.add_argument('--only',choices=['gnu','portable','disabled']);args=parser.parse_args()
    assert not args.label or args.label.replace('-','').replace('_','').isalnum()
    env=dict(os.environ);temp=p/'artifacts/stage2-vm-proved-budget/compiler-temp';temp.mkdir(exist_ok=True);env.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
    builders=[('gnu','build-stage2-vm-proved-budget',True,False),('portable','build-stage2-vm-proved-budget-portable',True,True),('disabled','build-stage2-vm-proved-budget-disabled',False,False)]
    if args.only:builders=[entry for entry in builders if entry[0]==args.only]
    evidence=root/(('build-evidence'if args.phase=='build'else args.phase+'-evidence')+('-'+args.label if args.label else''));evidence.mkdir(parents=True,exist_ok=False)
    ordinary=p/'build/cholesky_runtime.exe';memory=p/'build-memory/cholesky_runtime.exe'
    preserved={str(ordinary):'99a87d135378406a15efd930d58941291683ca799f91bd5dcc0ca77ceadef448',str(memory):'7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'}
    assert all(sha(k)==v for k,v in preserved.items())
    report={'passed':False,'phase':args.phase,'only':args.only,'process_env':{k:env[k]for k in ['TEMP','TMP','TMPDIR']},'preserved_binaries':preserved,'runs':[],'source_sha256':{}}
    started=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-started;(evidence/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def call(label,command):
        free=shutil.disk_usage(p).free;assert free>=256*1024*1024
        print(json.dumps({'starting':label,'command':command,'free_F_bytes':free}),flush=True)
        began=time.perf_counter();proc=subprocess.run(command,cwd=p,env=env,capture_output=True,text=True)
        (evidence/(label+'.stdout')).write_text(proc.stdout,encoding='utf-8');(evidence/(label+'.stderr')).write_text(proc.stderr,encoding='utf-8')
        report['runs'].append({'label':label,'command':command,'exit_code':proc.returncode,'elapsed_seconds':time.perf_counter()-began,'free_F_before_bytes':free,'stdout_sha256':sha(evidence/(label+'.stdout')),'stderr_sha256':sha(evidence/(label+'.stderr'))});save()
        print(json.dumps({'terminal':label,'exit_code':proc.returncode,'elapsed_seconds':report['runs'][-1]['elapsed_seconds']}),flush=True)
        if proc.returncode:raise RuntimeError(label+' failed; preserve logs, no automatic restart')
    if args.phase=='build':
        files=[p/'CMakeLists.txt',p/'CMakePresets.json',*sorted((p/'src').glob('*.cpp')),*sorted((p/'include').rglob('*.hpp')),*sorted((p/'tests').glob('*.cpp')),*sorted((p/'tools').glob('*.py')),p/'docs/stage2-vm-proved-budget-integration.md']
        for x in files:
            relative=x.relative_to(p);target=evidence/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);report['source_sha256'][relative.as_posix()]=sha(target)
        save()
        for name,build,proved,portable in builders:
            assert not(p/build).exists()
            configure=['cmake','--preset','local-mingw','-B',str(p/build),'-DCHOL_PROVED_VM_BUDGET='+('ON'if proved else'OFF'),'-DCHOL_THREADED_VM_FORCE_PORTABLE='+('ON'if portable else'OFF'),'-DCHOL_TEST_ARTIFACT_LABEL=stage2-vm-proved-budget-'+name]
            call(name+'-configure',configure);call(name+'-build',['cmake','--build',str(p/build),'--parallel','2'])
    elif args.phase=='policy-rebuild':
        for relative in ['tests/vm_proved_budget_tests.cpp','tools/build_vm_proved_budget_stage2.py']:
            target=evidence/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/relative,target);report['source_sha256'][relative]=sha(target)
        report['test_only_correction']='Native structure auto legitimately reports diagonal, not stage. Test now checks both original auto diagonal and explicit dense stage bypass. No runtime/component source or runtime EXE changes.'
        for name,build,proved,portable in builders:call(name+'-policy-rebuild',['cmake','--build',str(p/build),'--target','vm_proved_budget_tests','--parallel','2'])
    elif args.phase=='contracts':
        for name,build,proved,portable in builders:
            call(name+'-contracts',['ctest','--test-dir',str(p/build),'-R','metadata_wire_protocol|input_buffer_ownership|runtime_correctness|threaded_vm_contract|prepared_vm_contract|prepared_vm_tos2_contract|vm_default_selection|vector_scan_boundaries|finite_program_step_bound|proved_vm_budget_contract|threaded_vm_proved_contract','--output-on-failure','-j','1'])
    else:
        for name,build,proved,portable in builders:
            call(name+'-ctest',['ctest','--test-dir',str(p/build),'--output-on-failure','-j','1'])
    assert all(sha(k)==v for k,v in preserved.items())
    if args.phase=='build':assert all(sha(p/name)==digest for name,digest in report['source_sha256'].items())
    report.update(passed=True,preserved_binaries_unchanged=True,maximum_execution_started=False);save();print(json.dumps({'passed':True,'phase':args.phase,'report_sha256':sha(evidence/'report.json')}),flush=True)
if __name__=='__main__':main()
