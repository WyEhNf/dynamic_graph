"""Audit four real ABI builds and independently repeat their selector contracts."""
import json, subprocess, time
from review_stage2_vm_nested_runtime_plan import ROOT, P, D, sha, read

def main():
    r=D/'runtime-integration'; f=read(r/'implementation-freeze/manifest.json')
    b=read(r/'build-evidence/report.json'); c=read(r/'contracts-evidence/report.json')
    assert sha(r/'build-evidence/report.json')=='077653d6e851a5a93861aead2df5b3f3fce00dc3a4f2c940e7c10d7546cec4d7'
    assert sha(r/'contracts-evidence/report.json')=='cae99b9e1b0de385c14822a4252b5003e3ec68cf6b22fc72c66e8a652b6bd076'
    assert b['passed'] and c['passed'] and not c['performance_or_maximum_started']
    for phase,report in [('build',b),('contracts',c)]:
        assert report['implementation_manifest_sha256']==sha(r/'implementation-freeze/manifest.json')
        for row in report['runs']:
            assert row['exit_code']==(1 if row['label']=='nestedON-provedOFF-configure' else 0)
            for stream in ['stdout','stderr']:
                assert sha(r/(phase+'-evidence')/(row['label']+'.'+stream))==row[stream+'_sha256']
    for name,digest in f['mirror_source_sha256'].items(): assert sha(r/'workspace'/name)==digest
    out=ROOT/'outputs/stage2-root-vm-nested-runtime-contract-logs';out.mkdir(exist_ok=True)
    repeated=[]; totals=[0,0,0]
    for config in f['builds']:
        label=config['label']; build=r/config['build']; inventory=b['build_inventory'][label]
        assert inventory['matching_runtime_header_sha256']==f['matching_new_ABI_header_sha256']
        for name,artifact in inventory['artifacts'].items():
            assert sha(build/name)==artifact['sha256'] and (build/name).stat().st_size==artifact['bytes']
        flags=(build/'CMakeFiles/cholesky_core.dir/flags.make').read_text()
        assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags
        for macro,key in [('CHOL_PROVED_VM_BUDGET','CHOL_PROVED_VM_BUDGET'),('CHOL_NESTED_VM_BUDGET','CHOL_NESTED_VM_BUDGET')]:
            assert (('-D'+macro+'=1') in flags)==config[key]
        link=(build/'CMakeFiles/cholesky_runtime.dir/linkLibs.rsp').read_text()
        assert 'cholesky_core' in link and 'stage2-vm-proved-budget' not in link
        count={'gnu-nested':13,'portable-nested':13,'proved-only-compat':12,'disabled':10}[label]
        log=(r/'contracts-evidence'/(label+'-contracts.stdout')).read_text()
        assert f'100% tests passed, 0 tests failed out of {count}' in log
        exe=build/'vm_nested_budget_selection_tests.exe'
        with (out/(label+'.stdout')).open('wb') as stdout,(out/(label+'.stderr')).open('wb') as stderr:
            proc=subprocess.run([str(exe)],stdout=stdout,stderr=stderr,cwd=build,check=False)
        assert proc.returncode==0
        rows=[json.loads(line) for line in (out/(label+'.stdout')).read_text().splitlines()]
        saved=next(s for s in c['selection'] if s['build']==label)
        assert rows[-1]==saved['summary'] and rows[:-1]==saved['observations']
        s=rows[-1]; assert s['passed'] and s['selection_observations']==len(rows)-1
        for row in rows[:-1]:
            assert row['total_work']==row['first_work']+row['nested_work']<=250000
            if row['selected_stage']=='nested': assert row['first_status']=='unknown' and row['nested_status']=='proved' and row['cap']==max(1000000000,row['bound'])
            if row['first_status']=='proved': assert row['nested_status']=='first-proved-skip' and row['nested_work']==0
            if row['first_work']==250000: assert row['nested_work']==0
        for i,key in enumerate(['selection_observations','residual_work_auxiliary_checks','fixed_boundary_executions']): totals[i]+=s[key]
        repeated.append(dict(build=label,exit_code=0,CTest=count,exe_sha256=sha(exe),stdout_sha256=sha(out/(label+'.stdout')),summary=s))
    assert totals==[190,15,60]
    assert sha(P/'build/cholesky_runtime.exe')==f['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==f['memory_sha256']
    result=dict(passed=True,reviewed_unix=time.time(),build_report_sha256=sha(r/'build-evidence/report.json'),contracts_report_sha256=sha(r/'contracts-evidence/report.json'),independent_repeats=repeated,selector_observations=190,residual_work_checks=15,fixed_boundary_executions=60,authorization='Complete624 whole-C comparisons/56 errors/10 CLI, fullGNU CTest and separate UBSan on the same frozen mirror; preserve first actual failures. No maximum-size/performance/default promotion.',scope='All four actual core/caller inventories and strictFP flags, actual configure/build terminal logs and smallCTest counts verified; four selector executables independently rerun with exact observations. This does not yet prove C frontend integration or full regression.')
    (ROOT/'outputs/stage2-root-vm-nested-runtime-contracts.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
