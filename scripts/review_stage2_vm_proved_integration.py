"""Root audit actual opt-in policy outputs, frozen ABI/builds and errors."""
import json
import struct
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from review_stage2_vm_measurements import compare_files, sha

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/19-dynamic-graph'
D=P/'artifacts/stage2-vm-proved-budget/runtime-integration'
F=D/'acceptance'


def header(path):
    with path.open('rb') as stream:
        raw=stream.read(4);assert len(raw)==4
        count=struct.unpack('<I',raw)[0];assert 1<=count<=10000
        shapes=[]
        for _ in range(count):
            raw=stream.read(4);assert len(raw)==4
            n=struct.unpack('<I',raw)[0];assert 3<=n<=10000
            shapes.append(n);stream.seek(8*n*n,1)
        assert stream.tell()==path.stat().st_size
    return shapes


def main():
    evidence={}
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        return json.loads(path.read_text(encoding='utf-8'))
    manifest=read(F/'manifest.json')
    assert manifest['passed'] and len(manifest['source_sha256'])==139
    for name,digest in manifest['source_sha256'].items():assert sha(F/'source'/name)==digest,name
    for family,binaries in manifest['binaries'].items():
        for name,row in binaries.items():assert sha(F/family/name)==row['sha256'],name
    for family,records in manifest['build_provenance_sha256'].items():
        for name,digest in records.items():assert sha(F/family/'build-provenance'/name)==digest,name
        flags=(F/family/'build-provenance/CMakeFiles/cholesky_core.dir/flags.make').read_text()
        assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags
        cache=(F/family/'build-provenance/CMakeCache.txt').read_text()
        assert 'CHOL_PROVED_VM_BUDGET:BOOL='+('OFF' if family=='disabled' else 'ON') in cache
    for name,digest in manifest['evidence_sha256'].items():
        assert sha(F/'evidence'/name)==digest,name
    cp=P/'artifacts/stage2-vm-proved-budget/component-acceptance/manifest.json'
    component=read(cp)
    assert sha(cp)==manifest['component_manifest_sha256']
    for name in ('src/vm_step_bound.cpp','include/cholesky/vm_step_bound.hpp','tests/vm_step_bound_tests.cpp'):
        assert manifest['source_sha256'][name]==component['source_sha256'][name]
    assert sha(P/'build/cholesky_runtime.exe')==manifest['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==manifest['memory_sha256']
    assert sha(P/'build-stage2-vm-default/libcholesky_core.a')==manifest['historical_core_unchanged_sha256']
    assert set(manifest['source_deltas_from_initial_plan'])=={'CMakeLists.txt','src/main.cpp','src/runtime.cpp','include/cholesky/runtime.hpp'}
    for name,digest in manifest['frontend_unchanged_sha256'].items():assert manifest['source_sha256'][name]==digest
    report=read(D/'correctness/report.json')
    assert sha(D/'correctness/report.json')==manifest['full_C_report_sha256']
    assert report['passed'] and len(report['sources'])==15 and len(report['runs'])==469
    for row in report['sources']:
        folder=Path(row['folder']);fresh=row.get('fresh_source',False)
        source=folder/'source.c' if fresh else Path(row['source'])
        assert sha(source)==row['source_sha256']
        metadata=folder/'program.meta' if fresh else Path(row['metadata'])
        assert sha(metadata)==row['metadata_sha256']
        oracle=folder if fresh else Path(row.get('cached_original_directory',str(source.parent)))
        assert sha(oracle/'oracle.c')==row['harness_sha256']
        assert sha(oracle/'oracle.exe')==row['oracle_binary_sha256']
    groups=defaultdict(list);proven,unknown=0,0
    for row in report['runs']:
        inp,ref,out=map(Path,(row['input'],row['reference'],row['output']))
        size,digests=compare_files([ref,out])
        assert size==row['bytes'] and digests[0]==digests[1]==row['sha256']==row['reference_sha256']
        assert sha(inp)==row['input_sha256'] and sha(Path(row['metadata']))==row['metadata_sha256']
        assert header(inp)==header(ref)==header(out) and row['matrices']==len(header(inp))
        stdout=out.with_suffix('.stdout');stderr=out.with_suffix('.stderr')
        actual=json.loads(stdout.read_text());assert stderr.read_bytes()==b'' and row['exit_code']==0
        for key,value in actual.items():assert row[key]==value,(row['mode'],key)
        assert row['selected_engine']=='vm' and row['vm_effective_step_limit_max']==1000000000
        if row['mode']=='fixed-auto':
            assert row['vm_budget_proof_ms']==row['vm_budget_work']==row['vm_budget_bound_peak']==0
        elif row['mode']=='proved-auto':
            proven+=row['vm_budget_proved_matrices'];unknown+=row['vm_budget_unknown_matrices']
            assert row['vm_budget_proved_matrices']+row['vm_budget_unknown_matrices']==row['matrices']
        groups[row['source'],row['family']].append(row)
    assert len(groups)==67
    modes={'fixed-auto','proved-auto','proved-legacy','proved-decoded','proved-tos2','proved-threaded','portable-proved'}
    for rows in groups.values():
        assert {r['mode'] for r in rows}==modes and len(rows)==7
        assert len({r['vm_steps'] for r in rows})==1
        assert rows[0]['vm_backend']=='decoded-threaded'
        assert next(r for r in rows if r['mode']=='portable-proved')['vm_backend']=='decoded-fallback'
    old=read(P/'artifacts/stage2-vm-default-integration/correctness/report.json')
    errors={r['source']:r['results'][0]['stderr'] for r in old['failures']}
    assert len(report['failures'])==7
    for group in report['failures']:
        assert sha(Path(group['metadata']))==group['metadata_sha256']
        assert len(group['results'])==7
        for row in group['results']:
            assert row['exit_code']==1 and row['stdout']=='' and row['stderr']==errors[group['source']]
            output=Path(row['command'][row['command'].index('--output')+1])
            assert not output.exists()
    assert len(report['cli'])==9
    for row in report['cli']:
        family='disabled' if 'disabled' in row['exe'] else ('portable' if 'portable' in row['exe'] else 'gnu')
        actual=subprocess.run([str(F/family/'cholesky_runtime.exe'),*row['flags']],capture_output=True,text=True,timeout=15)
        assert (actual.returncode,actual.stdout,actual.stderr)==(row['exit_code'],row['stdout'],row['stderr'])
        if row['flags']==['--help']:
            assert row['exit_code']==0 and row['stderr']==''
            assert ('[--vm-budget fixed|proved]' in row['stdout'])==(family!='disabled')
        else:
            assert row['exit_code']==1 and row['stdout']=='' and row['stderr'].startswith('error: ')
    for directory,counts in [('contracts-evidence-v2',(11,11,9)),('ctest-evidence',(15,))]:
        test=read(D/directory/'report.json');assert test['passed']
        assert len(test['runs'])==len(counts)
        for row,count in zip(test['runs'],counts):
            assert row['exit_code']==0
            path=D/directory/(row['label']+'.stdout')
            assert sha(path)==row['stdout_sha256']
            assert f'100% tests passed, 0 tests failed out of {count}' in path.read_text()
    ubsan=read(D/'ubsan/report.json');assert ubsan['passed'] and ubsan['exit_code']==0
    contracts=[]
    rootfolder=ROOT/'outputs/stage2-root-vm-proved-integration';rootfolder.mkdir(exist_ok=True)
    names=['vm_step_bound_tests.exe','vm_proved_budget_tests.exe','threaded_vm_proved_tests.exe']
    for family in ('gnu','portable'):
        for name in names:
            exe=F/family/name;run=subprocess.run([str(exe)],capture_output=True,timeout=60)
            for label,raw in [('stdout',run.stdout),('stderr',run.stderr)]:
                path=rootfolder/(family+'-'+name+'-'+label+'.txt');path.write_bytes(raw)
                evidence[path.relative_to(ROOT).as_posix()]=sha(path)
            assert run.returncode==0 and run.stderr==b''
            contracts.append(dict(family=family,name=name,exe_sha256=sha(exe),actual_exit_code=run.returncode,stdout=run.stdout.decode().strip()))
    assert (proven,unknown)==(306,260)
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(F/'manifest.json'),
        frozen_sources=139,actual_whole_C_outputs=469,source_count=15,input_families=67,
        GNU_full_ctest=15,portable_small_ctest=11,disabled_small_ctest=9,
        original_C_error_comparisons=49,CLI_contracts=9,root_actual_contract_executions=contracts,
        proved_auto_matrices=proven,unknown_auto_matrices=unknown,actual_raised_budget_cases=0,
        candidate_sha256=manifest['binaries']['gnu']['cholesky_runtime.exe']['sha256'],
        portable_sha256=manifest['binaries']['portable']['cholesky_runtime.exe']['sha256'],
        ordinary_runtime_sha256=manifest['ordinary_sha256'],evidence=evidence,
        scope='469 complete originalC outputs/inputs/metadata/source/harness/exe SHA independently compared;67x7 full groups retain exactly originalVM steps,49 originalerrors and9CLI contracts. Six actual frozen proof/policy/derived contract executables rerun under GNU+portable;15/11/9CTest and UBSan evidence frozen. Allsmall effectivebudgets remain1e9;306proved/260unknown respect scoped fallback. Ordinary99a fixeddefault unchanged. Actual N10000 raisedbudget and broader arbitraryC not proven.')
    (ROOT/'outputs/stage2-root-vm-proved-integration.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','root_actual_contract_executions')}))


if __name__=='__main__':main()
