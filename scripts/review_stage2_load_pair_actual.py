"""Verify actual isolated build records, complete raw gates and fallback CLI."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    source=read(ROOT/'outputs/stage2-root-load-pair-source.json');assert source['passed']
    original=read(R/'build-gate-evidence/report.json');actual=read(R/'build-gate-continuation-evidence/report.json')
    assert not original['passed'] and original['first_failure']['type']=='AssertionError'
    assert original['first_failure']['message']=="('gnu', 'CTest denominator')"
    assert sha(R/'build-gate-evidence/report.json')==actual['initial_report_sha256']
    assert sha(R/'build-gate-continuation-evidence/report.json')=='8896ca777a39057454a1973db95dbfebdf7947901624ebb3b791eb3bba3596f0'
    assert actual['passed'] and actual['reused_records']==original['records']
    plan=read(R/'build-gate-continuation-plan/plan.json');assert sha(R/'build-gate-continuation-plan/plan.json')==actual['plan_sha256']
    manifest=read(R/'manifest.json')
    for path,r in manifest['frozen_files'].items():assert sha(R/path)==r['sha256'] and (R/path).stat().st_size==r['bytes']
    records=original['records']+actual['records'];ctest={};fresh=[]
    for r in records:
        assert r['actual_exitcode']==r['expected_exitcode']
        for k in ('stdout','stderr'):assert sha(r['raw_'+k])==r[k+'_sha256']
        before=r['before'];assert r['resource_gate_passed'] and min(before['available_ram_bytes'],before['G_free_bytes'])>=1073741824
        fresh.append(before)
        if r['label'].endswith('-ctest'):ctest[r['label'].split('-')[0]]=Path(r['raw_stdout']).read_text()
    assert set(ctest)=={'gnu','portable','disabled'}
    for label,text in ctest.items():
        expected=13 if label=='disabled' else 14
        assert re.search(r'100% tests passed, 0 tests failed out of '+str(expected)+r'\b',text)
        lines=re.findall(r'^\d+: (\{"passed":true[^\n]+\})',text,re.M)
        docs=[json.loads(x) for x in lines]
        assert any(x.get('comparisons')==934 and x.get('opcode_coverage')==33 for x in docs)
        if label!='disabled':assert any(x==dict(passed=True,original_groups=15,prefix_cases=8369,extra_cases=80,comparisons=8464) for x in docs)
        else:assert not any(x.get('comparisons')==8464 for x in docs)
        build=R/('build-'+label)
        for p,r in actual['builds'][label]['artifacts'].items():assert sha(build/p)==r['sha256'] and (build/p).stat().st_size==r['bytes']
        flags=(build/'CMakeFiles/cholesky_core.dir/flags.make').read_text()
        assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags
        assert actual['builds'][label]['new_header_sha256']==sha(R/'workspace/include/cholesky/runtime.hpp')
        cache=(build/'CMakeCache.txt').read_text()
        assert 'CHOL_PROVED_VM_BUDGET:BOOL=OFF' in cache and 'CHOL_NESTED_VM_BUDGET:BOOL=OFF' in cache
        assert 'CHOL_VECTOR_SCANS:BOOL=OFF' in cache and 'CHOL_VECTOR_PANEL:BOOL=OFF' in cache
    assert len(actual['cli'])==7;files=[]
    for c in actual['cli']:
        p=Path(c['output'])
        if c['build']=='disabled':assert c['expected_disabled_reject'] and not p.exists();continue
        assert p.stat().st_size==80 and sha(p)==c['sha256'];files.append(p.read_bytes());m=c['metric']
        assert m['vm_budget_mode']=='fixed' and m['vm_budget_work']==0
        if c['backend']=='decoded-threaded-load-pair':
            if c['build']=='gnu':assert m['vm_fusion_pairs_discovered']>0 and m['vm_fusion_pairs_executed']>0
            else:assert m['vm_backend']=='decoded-fallback' and m['vm_fusion_status_last']=='portable-fallback' and m['vm_fusion_pairs_executed']==0
        if c['backend']=='auto':assert m['vm_fusion_pairs_executed']==0
    assert len(set(files))==1
    acceptance=read(R/'build-gate-acceptance/manifest.json')
    assert acceptance['passed'] and acceptance['failure_preserved']
    assert sha(R/'build-gate-acceptance/manifest.json')=='5a6a47332f520a375a2037e3c86be0ecabedd4df4d6b6f8b9747d816e0d0cf9e'
    archive_bytes=0
    for name,entry in acceptance['files'].items():
        archived=R/'build-gate-acceptance'/name;origin=Path(entry['origin'])
        assert sha(archived)==sha(origin)==entry['sha256']
        assert archived.stat().st_size==origin.stat().st_size==entry['bytes'];archive_bytes+=entry['bytes']
    assert len(acceptance['files'])==3482 and archive_bytes==329642347
    result=dict(passed=True,actual_continuation_exit_code=0,original_runner_exit_code=1,original_failure_preserved=True,source_frozen_files=len(manifest['frozen_files']),acceptance_frozen_files=3482,acceptance_bytes=archive_bytes,acceptance_manifest_sha256=sha(R/'build-gate-acceptance/manifest.json'),build_CTest_counts=dict(gnu=14,portable=14,disabled=13),new_comparisons_per_enabled=8464,old_comparisons_per_build=934,cli_checks=7,CLI_full_bytes_compared=480,strict_FP_builds=3,fresh_resource_records=len(fresh),report_sha256=sha(R/'build-gate-continuation-evidence/report.json'),source_review_sha256=sha(ROOT/'outputs/stage2-root-load-pair-source.json'),GNU_exe_sha256=sha(R/'build-gnu/cholesky_runtime.exe'),scope='Actual source-preserving LOAD+LOAD/fallback/disabled functional gates; finite-C historical pipelines retained under auto, explicit fused realC only the N3 CLI. No measured speed gain or arbitrary-C/official grade/default promotion claim.')
    (ROOT/'outputs/stage2-root-load-pair-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
