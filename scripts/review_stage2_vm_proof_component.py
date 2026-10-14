"""Rebuild the frozen proof component using its frozen historical ABI library."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/19-dynamic-graph'
A=P/'artifacts/stage2-vm-proved-budget/component-acceptance'
S=P/'artifacts/stage2-vm-proved-budget/component-dependency-supplement'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence={}
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        return json.loads(path.read_text(encoding='utf-8'))
    accepted=read(A/'manifest.json'); supplement=read(S/'manifest.json')
    assert accepted['passed'] and supplement['passed']
    assert supplement['supplements_manifest_sha256']==sha(A/'manifest.json')
    for name, record in supplement['files'].items():
        assert sha(S/name)==record['sha256']
        evidence[(S/name).relative_to(ROOT).as_posix()]=record['sha256']
    for name,digest in accepted['source_sha256'].items():
        assert sha(A/'source'/name)==digest
    assert sha(S/'libcholesky_core.a')==accepted['existing_frozen_core_library']['sha256']
    assert sha(S/'core-flags.make')==accepted['existing_frozen_core_library']['flags_sha256']
    for name in ('src/vm_step_bound.cpp','include/cholesky/vm_step_bound.hpp','tests/vm_step_bound_tests.cpp'):
        assert sha(S/'source'/name)==accepted['source_sha256'][name]
    installed=P/'build/cholesky_runtime.exe'
    ordinary_before=sha(installed)
    assert ordinary_before==accepted['ordinary_runtime_sha256']
    folder=ROOT/'outputs/stage2-root-vm-proof-component'
    folder.mkdir(exist_ok=True)
    temp=folder/'compiler-temp';temp.mkdir(exist_ok=True)
    env=os.environ.copy();env.update({k:str(temp) for k in ('TEMP','TMP','TMPDIR')})
    exe=folder/'vm-bound-tests.exe'
    command=[accepted['compile_command'][0],'-std=c++20','-O2','-g','-Wall','-Wextra','-Wpedantic','-fno-fast-math','-ffp-contract=off',
        '-I',str(S/'source/include'),str(S/'source/src/vm_step_bound.cpp'),str(S/'source/tests/vm_step_bound_tests.cpp'),str(S/'libcholesky_core.a'),'-o',str(exe)]
    executions=[]
    for label,args in [('compile',command),('test',[str(exe)])]:
        began=time.time();run=subprocess.run(args,env=env,capture_output=True,timeout=120)
        for stream,raw in [('stdout',run.stdout),('stderr',run.stderr)]:
            path=folder/(label+'-'+stream+'.txt');path.write_bytes(raw)
            evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        executions.append(dict(phase=label,command=args,actual_exit_code=run.returncode,wall_seconds=time.time()-began))
        assert run.returncode==0,(label,run.stderr.decode(errors='replace'))
        if label=='test':
            stats=json.loads(run.stdout)
    assert stats==accepted['result'],stats
    assert sha(installed)==ordinary_before
    result=dict(passed=True,reviewed_unix=time.time(),frozen_component_manifest_sha256=sha(A/'manifest.json'),
        abi_dependency_supplement_sha256=sha(S/'manifest.json'),frozen_dependency_files=len(supplement['files']),
        actual_root_executions=executions,root_test_exe_sha256=sha(exe),component_stats=stats,
        ordinary_runtime_sha256=ordinary_before,ordinary_runtime_unchanged=True,evidence=evidence,
        scope='Independent actual rebuild and execution of frozen historical-ABI component tests:517 goldens,1030 boundaries,119 unknowns,6358 one-position mutations,832 actual VM mutation runs. These finite tests plus structural review support scoped proof, not arbitraryPROGRAM correctness or N10000 execution. Original failed test fixture retained; runtime integration is a separate gate.')
    (ROOT/'outputs/stage2-root-vm-proof-component.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','actual_root_executions')}))


if __name__=='__main__':main()
