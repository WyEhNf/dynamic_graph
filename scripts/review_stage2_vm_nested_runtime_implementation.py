"""Static mirror/ABI/dispatch/runner review before any new build."""
import difflib
import json
import time
from review_stage2_vm_nested_runtime_plan import ROOT,P,D,PLAN,sha,read

def main():
    r = D/'runtime-integration'; f = r/'implementation-freeze'; m = read(f/'manifest.json'); w = r/'workspace'
    assert sha(f/'manifest.json') == '43f1fe36fa2a0605e47a8de04035d3a2dfe6cc5a9020c52ab915fc94b365a399'
    assert m['initial_plan_sha256'] == sha(PLAN/'plan.json')
    assert m['static_contract_supplement_sha256'] == sha(r/'contract-supplement/plan.json')
    assert len(m['mirror_source_sha256']) == 178
    for name,digest in m['mirror_source_sha256'].items(): assert sha(w/name) == sha(f/'source'/name) == digest
    changed = set(m['four_modified_baseline_files'])
    assert changed == {'CMakeLists.txt','include/cholesky/runtime.hpp','src/main.cpp','src/runtime.cpp'}
    hunks = {}
    for name,digest in m['baseline_before_sha256'].items():
        assert sha(PLAN/'baseline-source'/name) == digest
        if name not in changed: assert sha(w/name) == digest
        else:
            assert sha(w/name) == m['modified_after_sha256'][name]
            before = (PLAN/'baseline-source'/name).read_text(); after = (w/name).read_text()
            diff = ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='baseline/'+name,tofile='isolated/'+name))
            saved = f/'diffs'/(name.replace('/','__')+'.diff')
            assert saved.read_text() == diff and sha(saved) == m['diff_sha256'][saved.name]
            hunks[name] = diff.count('\n@@')
    for name,digest in m['runner_source_sha256'].items(): assert sha(P/'tools'/name) == sha(f/'runner-source/tools'/name) == digest
    assert sha(w/'src/vm_nested_step_bound.cpp') == m['component_CPP_sha256'] == 'e4174798ec482c474c4bcf0ef3e602c02e339804c5413594cb5755fb68de7dea'
    assert sha(w/'src/vm_step_bound.cpp') == sha(P/'src/vm_step_bound.cpp') == m['working_original_proof_CPP_sha256']
    assert sha(w/'include/cholesky/runtime.hpp') == m['matching_new_ABI_header_sha256'] == '1955d364a3b097c05e3972ec29fb86c1e9fbed5622294e1b40bcba7894f3bf9d'
    source = (w/'src/runtime.cpp').read_text()
    assert 'const auto first=prove_vm_step_bound(metadata,input.n,options.block_size);' in source
    assert 'const auto remaining=work_limit-first.work;' in source and 'if(!remaining)nested_status="work-exhausted-skip";' in source
    assert 'nested=prove_vm_nested_step_bound(metadata,input.n,options.block_size,remaining);' in source
    assert source.index('return scalar_cholesky(input, options);') < source.index('const auto first=prove_vm_step_bound')
    assert 'first.bound==std::numeric_limits' not in source and 'nested.bound==std::numeric_limits' not in source
    assert not m['link_historical_library'] and m['all_four_builds_new_core_runtime_and_callers']
    assert m['expected_selection_observations'] == {'gnu-nested':60,'portable-nested':60,'proved-only-compat':60,'disabled':10,'total':190}
    assert m['all_primary_and_compat_denominator'] == dict(whole_C_files=624,exact_old_error_results=56,CLI_results=10,new_invalid_configuration_results=1)
    assert not any(m[k] for k in ('existing_VM_sources_changed','compile_or_VM_started','N10000_or_performance_or_default_changed'))
    assert sha(P/'build/cholesky_runtime.exe') == m['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe') == m['memory_sha256']
    result = dict(passed=True,reviewed_unix=time.time(),implementation_manifest_sha256=sha(f/'manifest.json'),
        mirror_files=178,changed_baseline_files=sorted(changed),diff_hunks=hunks,new_header_sha256=m['matching_new_ABI_header_sha256'],
        planned_selector_observations=190,planned_all_C=624,planned_all_errors=56,planned_all_CLI=10,
        authorization='Four isolated matching-ABI configure/builds then contracts phase only. Preserve actual failure/raw evidence before repairs. Root audit contracts before complete functional/CTest/UBSan phases.',
        scope='Root reviewed four diffs, stage dispatch/remaining250k/native bypass, twelve selector families/auxiliary boundaries and runner full-byte/C lineage. No build or candidate execution accepted yet. Current fixedMAX counter limitation is historical; components reject sentinelMAX internally. Ordinary/default/N10000/performance unchanged.')
    (ROOT/'outputs/stage2-root-vm-nested-runtime-implementation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
