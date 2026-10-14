"""Root isolated rebuild with observation-only gold records and integer oracle."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from review_stage2_vm_nested_component_plan import ROOT,P,D,read,sha

def counted(specs,depth=0,parent=0,conservative=False):
    s=specs[depth];start,end,step,parent_bound,shape=s
    limit=parent if parent_bound else 3 if shape else end
    values=list(range(start,limit,step)) if start<limit else []
    if not conservative:
        bodies=sum(counted(specs,depth+1,value) if depth+1<len(specs) else 2 for value in values)
    else:
        bodies=len(values)*(counted(specs,depth+1,values[-1],True) if depth+1<len(specs) and values else 2)
    return 3+4*(len(values)+1)+6*len(values)+bodies

def main():
    acceptance=D/'component-acceptance';manifest=read(acceptance/'manifest.json')
    for name,row in manifest['files'].items():assert sha(acceptance/name)==row['sha256']
    for name,digest in manifest['dependencies_sha256'].items():
        path=Path(name)
        if not path.is_absolute():path=D/'initial-freeze'/name
        assert sha(path)==digest
    assert manifest['compile_attempts']==2 and manifest['actual_contract_batches']==1
    gate=D/'component-gate-capture';report=read(gate/'report.json')
    assert sha(gate/'report.json')==manifest['passed_execution_report_sha256']
    assert report['passed'] and len(report['runs'])==2 and all(r['actual_exit_code']==0 for r in report['runs'])
    for r in report['runs']:
        assert sha(gate/(r['phase']+'.stdout'))==r['stdout_sha256'] and sha(gate/(r['phase']+'.stderr'))==r['stderr_sha256']
    folder=ROOT/'outputs/stage2-root-vm-nested-component';folder.mkdir(exist_ok=True)
    source=(D/'accounting-supplement/candidate-source/tests/vm_nested_step_bound_tests.cpp').read_text()
    anchor='boundaries+=2;'
    observe=r'''boundaries+=2;
  std::cout<<"{\"kind\":\"root_gold\",\"bound\":"<<proof.bound<<",\"actual_steps\":"<<got.steps<<",\"specs\":[";
  for(std::size_t k=0;k<specs.size();++k){auto s=specs[k];if(k)std::cout<<',';std::cout<<'['<<s.start<<','<<s.end<<','<<s.increment<<','<<(s.parent_bound?"true":"false")<<','<<(s.shape_bound?"true":"false")<<']';}
  std::cout<<"]}\n";'''
    assert source.count(anchor)==1
    observed=source.replace(anchor,observe);assert observed.replace(observe,anchor)==source
    test=folder/'observed-tests.cpp';test.write_text(observed)
    command=list(manifest['compile_command']);command[-1]=str(folder/'vm-nested-root.exe')
    original_test=str(D/'accounting-supplement/candidate-source/tests/vm_nested_step_bound_tests.cpp')
    command[command.index(original_test)]=str(test)
    temp=folder/'compiler-temp';temp.mkdir(exist_ok=True);env=os.environ.copy();env.update({k:str(temp) for k in ('TEMP','TMP','TMPDIR')});env['PATH']='E:/mingw64/bin'+os.pathsep+env['PATH']
    import sys
    sys.path.insert(0,str(P/'tools'));from windows_file_resource_probe_stage2 import HostMemory,monitored_run
    import ctypes
    def resource_gate():
        memory=HostMemory();memory.dwLength=ctypes.sizeof(memory);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
        free=shutil.disk_usage(ROOT).free;assert memory.ullAvailPhys>=268435456 and free>=268435456
        return dict(available_RAM_bytes=memory.ullAvailPhys,F_free_bytes=free)
    freeze=dict(observation_only=True,test_sha256=sha(test),candidate_sha256=sha(Path(command[-5])),command=command,resource_gate=resource_gate(),environment={k:env[k] for k in ('TEMP','TMP','TMPDIR')})
    (folder/'precompile.json').write_text(json.dumps(freeze,indent=2)+'\n')
    oldenv=dict(os.environ);os.environ.update(env)
    try:
        proc,resources=monitored_run(command,folder/'compile.stdout',folder/'compile.stderr',check=False)
        assert proc.returncode==0
        before=resource_gate();executed,vmresources=monitored_run([command[-1]],folder/'contracts.stdout',folder/'contracts.stderr',check=False)
        assert executed.returncode==0
    finally:os.environ.clear();os.environ.update(oldenv)
    rows=[json.loads(line) for line in (folder/'contracts.stdout').read_text().splitlines()];stats=rows[-1];golds=rows[:-1]
    assert stats==manifest['stats'] and len(golds)==1081
    for r in golds:
        assert r['kind']=='root_gold';specs=r['specs']
        assert r['actual_steps']==counted(specs)+2<=r['bound']==counted(specs,conservative=True)+2
    assert stats['original_VM_executions']==4995 and stats['single_position_mutations']==16320 and stats['proved_mutations']==872
    assert sha(P/'build/cholesky_runtime.exe')==manifest['ordinary_sha256']
    assert sha(P/'src/vm_step_bound.cpp')=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(acceptance/'manifest.json'),root_test_exe_sha256=sha(Path(command[-1])),root_observation_test_sha256=sha(test),
        independent_integer_gold_cases=1081,root_contract_stats=stats,root_compile_exit=proc.returncode,root_contract_exit=executed.returncode,
        root_compile_resources=resources,root_contract_resources=vmresources,
        scope='Frozen sources/dependencies/new da955/57205 ABI and both compile attempts audited; root rebuilt candidate with observation-only tests, independently enumerated1081 integer loop counts/conservative parent maxima from printed specs and matched all actual legacy steps/bounds. Root2162 boundaries/16320mutants/220unknown/4error and4995VM executed. First PIPE failure retained. Component-only, no arbitraryC/universal proof/new Runtime/largeN/default/performance claim.')
    (ROOT/'outputs/stage2-root-vm-nested-component.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if 'resources' not in k}))

if __name__=='__main__':main()
