"""Verify actual full regression/sanitized commands and immutable acceptance files."""
import json,time
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,read,sha

def main():
    r=D/'runtime-integration'; a=r/'acceptance'; m=read(a/'manifest.json')
    assert sha(a/'manifest.json')=='205f434096f8b296f11716d2b9e312a5aabacb6b21432756000606d1e81cd8a3'
    assert m['passed']and m['mirror_source_count']==178 and not m['performance_or_maximum_or_ordinary_install_started']
    for name,row in m['frozen_files'].items():assert sha(a/name)==row['sha256'] and (a/name).stat().st_size==row['bytes'] and sha(row['origin'])==row['sha256']
    assert sha(a/'summary.json')==m['summary_sha256'] and sha(a/'output-index.json')==m['output_index_sha256']
    accepted=read(ROOT/'outputs/stage2-root-vm-nested-runtime-functional.json');assert accepted['passed']and accepted['whole_C_outputs']==624
    f=read(r/'implementation-freeze/manifest.json')
    c=read(r/'ctest-evidence/report.json');u=read(r/'ubsan-evidence/report.json')
    assert sha(r/'ctest-evidence/report.json')=='9460abb8d513d373755e25419a71cb5d00197a14e94b954cdb360e17bda0c626'
    assert sha(r/'ubsan-evidence/report.json')=='4e633d0df563da394153c56092bd5f969a20e208df81b62b5b6a17655dd8acc7'
    for phase,report in [('ctest',c),('ubsan',u)]:
        assert report['passed']and report['implementation_manifest_sha256']==sha(r/'implementation-freeze/manifest.json')
        for row in report['runs']:
            assert row['exit_code']==0
            for stream in ['stdout','stderr']:assert sha(r/(phase+'-evidence')/(row['label']+'.'+stream))==row[stream+'_sha256']
    counts=[17,13,12,10];assert len(c['runs'])==4
    for row,count in zip(c['runs'],counts):
        stdout=(r/'ctest-evidence'/(row['label']+'.stdout')).read_text();assert f'100% tests passed, 0 tests failed out of {count}'in stdout
    assert len(u['compile_commands'])==12
    for cmd in u['compile_commands']:
        for flag in ['-fsanitize=undefined','-fno-sanitize-recover=undefined','-fno-fast-math','-ffp-contract=off','-DCHOL_NESTED_VM_BUDGET=1']:assert flag in cmd
        assert not any('stage2-vm-proved-budget' in x or x.endswith('.a')for x in cmd)
    log=(r/'ubsan-evidence/UBSan-build-and-contracts.stdout').read_text();err=(r/'ubsan-evidence/UBSan-build-and-contracts.stderr').read_text()
    assert 'runtime error:'not in log+err
    jsonrows=[json.loads(x)for x in log.splitlines()if x.startswith('{')];summaries=[x for x in jsonrows if x.get('passed')]
    assert len(summaries)==4 and summaries[0]['comparisons']==summaries[1]['comparisons']==934
    assert summaries[2]['original_VM_executions']==4995 and summaries[2]['single_position_mutations']==16320
    assert summaries[3]['selection_observations']==60 and summaries[3]['residual_work_auxiliary_checks']==5 and summaries[3]['fixed_boundary_executions']==15
    pipeline=r/'workspace/artifacts';reports=list(pipeline.rglob('*report.json'));assert len(reports)==4
    def walk(x):
        if isinstance(x,dict):
            if 'byte_identical'in x:assert x['byte_identical']
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    for path in reports:
        report=read(path);assert report['passed'];walk(report)
        if 'runtime_sha256'in report:assert report['runtime_sha256']==sha(r/'build-gnu-nested/cholesky_runtime.exe')
    assert sha(P/'build/cholesky_runtime.exe')==m['ordinary_sha256']and sha(P/'build-memory/cholesky_runtime.exe')==m['memory_sha256']
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(a/'manifest.json'),frozen_files=len(m['frozen_files']),source_files=178,whole_C_outputs=624,errors=56,CLI=10,full_CTest=counts,UBSan_contract_executables=4,UBSan_original_comparisons=934,UBSan_nested_VM_executions=4995,UBSan_selector_observations=60,original_first_functional_exit=1,ordinary_unchanged=True,scope='All acceptance source/build/raw evidence copies checked against origins, actual fullCTest17/13/12/10 and four source-pipeline reports accepted; full8core+4matchingABI UBSan compile commands and actual4contract summaries checked. Root624wholeC already independently byte-verified. Optional integration accepted within21C-source/24shape coverage; no arbitraryC/maxnested/performance/default claim. First runner-only failure retained.')
    (ROOT/'outputs/stage2-root-vm-nested-runtime-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
