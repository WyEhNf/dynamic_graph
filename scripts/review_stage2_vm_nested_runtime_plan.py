"""Independently audit static Runtime plan, original C lineage and ABI scope."""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'projects/19-dynamic-graph'
D = P / 'artifacts/stage2-vm-nested-budget'
PLAN = D / 'runtime-integration/initial-plan'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    p = read(PLAN / 'plan.json')
    assert sha(PLAN / 'plan.json') == '32aafc022a3fe8ad375c36bdbccf66823048847c88bc45a3cd18b20abc867253'
    for name, row in p['frozen_files'].items():
        assert sha(PLAN / name) == sha(row['origin']) == row['sha256'], name
    assert len(p['frozen_files']) == 148
    acceptance = P / 'artifacts/stage2-vm-proved-budget/runtime-integration/acceptance'
    accepted = read(acceptance / 'manifest.json')
    assert accepted['passed'] and sha(acceptance / 'manifest.json') == p['baseline_acceptance_sha256']
    component = D / 'component-acceptance'
    assert read(component / 'manifest.json')['passed']
    assert sha(component / 'manifest.json') == p['component_manifest_sha256']
    assert sha(ROOT / 'outputs/stage2-root-vm-nested-component.json') == p['root_component_audit_sha256']
    for name in ['src/vm_nested_step_bound.cpp', 'include/cholesky/vm_nested_step_bound.hpp', 'tests/vm_nested_step_bound_tests.cpp']:
        assert sha(PLAN / 'nested-source' / name) == sha(component / 'source' / name)
    assert sha(PLAN / 'nested-source/src/vm_nested_step_bound.cpp') == 'e4174798ec482c474c4bcf0ef3e602c02e339804c5413594cb5755fb68de7dea'
    assert sha(P / 'build/cholesky_runtime.exe') == p['ordinary_sha256']
    assert sha(P / 'build-memory/cholesky_runtime.exe') == p['memory_sha256']
    assert sha(P / 'src/vm_step_bound.cpp') == p['source_scope']['original_vm_step_bound_cpp_SHA_unchanged']

    old_path = P / 'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json'
    old = read(old_path)
    assert sha(old_path) == p['old_report_sha256'] and old['passed']
    assert len(old['runs']) == 469 and len(old['failures']) == 7 and len(old['cli']) == 9
    assert len(p['old_actual_C_source_lineage']) == len(old['sources']) == 15
    for lineage, original in zip(p['old_actual_C_source_lineage'], old['sources']):
        assert lineage['source'] == original['label'] and lineage['folder'] == original['folder']
        keys = dict(zip(['source.c', 'program.meta', 'oracle.c', 'oracle.exe'],
                        ['source_sha256', 'metadata_sha256', 'harness_sha256', 'oracle_binary_sha256']))
        for name, key in keys.items():
            assert sha(Path(lineage['folder']) / name) == lineage['files_sha256'][name] == original[key]
    old_fixed = [r for r in old['runs'] if r['mode'] == 'fixed-auto']
    assert len(old_fixed) == len(p['old_C_reference_groups']) == 67
    assert sum(r['matrices'] for r in old_fixed) == 566
    for r, original in zip(p['old_C_reference_groups'], old_fixed):
        assert all(v == original[k] for k, v in r.items())
        for key in ('metadata', 'input', 'reference'):
            assert sha(r[key]) == r[key + '_sha256']
        assert Path(r['reference']).stat().st_size == r['bytes']
        assert r['reference_sha256'] == r['sha256']
    proved = [r for r in old['runs'] if r['mode'] == 'proved-auto']
    assert len(proved) == 67
    assert sum(r['vm_budget_proved_matrices'] for r in proved) == 306
    assert sum(r['vm_budget_unknown_matrices'] for r in proved) == 260

    fresh = p['fresh_C_sources']
    assert len(fresh) == 6 and len({r['sha256'] for r in fresh}) == 6
    for r in fresh:
        assert sha(r['path']) == r['sha256'] and r['sizes'] == [3, 7, 13, 29, 53]
        assert r['families'] == ['dense-SPD', 'diagonal-signedzero-SPD']
        assert r['whole_C_output_comparisons'] == 14 and not r['AST_IR_or_C_compiled']
        source = Path(r['path']).read_text(encoding='utf-8')
        assert r['function'] + '(' in source and 'return 0;' in source
    # The six C bodies were also read by root: positive strides, finite bounded
    # int indexes (N<=53), independent input/output arrays, source-order FP64.
    denom = p['denominators']
    assert denom['total_whole_C_comparisons'] == 67 * 7 + 6 * 2 * 7 + 4 == 557
    assert denom['all_actual_C_sources'] == 21
    assert denom['old_exact_error_checks'] == 7 * 7 == 49 and denom['old_CLI_cases'] == 9
    assert denom['fresh_required_generic_nested_proved_auto_matrices'] == 30
    assert denom['fresh_required_unknown_auto_matrices'] == 20
    assert denom['fresh_required_native_no_proof_auto_matrices'] == 10
    contract = p['integration_contract']
    assert contract['total_analysis_work_cap'] == 250000
    assert contract['nested_work_limit'] == '250000-first.work, checked; if zero skip with work-limit reason'
    assert p['new_CMake_flag']['default'] is False and p['new_CMake_flag']['no_new_cli_budget_mode']
    builds = p['builds']
    assert len(builds) == 4
    assert [(b['CHOL_PROVED_VM_BUDGET'], b['CHOL_NESTED_VM_BUDGET'], b['CHOL_THREADED_VM_FORCE_PORTABLE']) for b in builds] == [(True, True, False), (True, True, True), (True, False, False), (False, False, False)]
    assert not any(p[k] for k in ('source_oracle_execution_started', 'runtime_build_started', 'large_shape_or_performance_started', 'default_promoted'))
    assert not (D / 'runtime-integration/workspace').exists()
    supplement_path = D / 'runtime-integration/contract-supplement/plan.json'
    supplement = read(supplement_path)
    assert sha(supplement_path) == '7aa25cc3a060cffc700aee41799877346d74dc0999a61d33e78b6a172735b5a3'
    assert supplement['initial_plan_sha256'] == sha(PLAN / 'plan.json')
    for row in supplement['anticipated_mirror_file_changes']:
        assert sha(PLAN / 'baseline-source' / row['path_in_future_mirror']) == row['before_sha256']
        assert row['proposed_after_sha256'] is None
    assert supplement['build_contract']['builds'] == builds
    assert supplement['ABI_contract']['all_four_builds_recompile_core_runtime_tests_together']
    assert supplement['ABI_contract']['no_link_new_metrics_header_or_new_Runtime_objects_to_old57205_library']
    totals = supplement['denominator_contract']['all_primary_and_compat_totals']
    assert totals == dict(whole_C_files=624, exact_old_error_results=56, CLI_results=10, new_invalid_configuration_results=1)
    selection = supplement['new_selection_contract']
    assert len(selection['caseIDs']) == 12 and selection['all_four_builds_observations'] == 60*3+10 == 190
    assert not supplement['build_or_run_started'] and not supplement['implementation_written']
    result = dict(passed=True, reviewed_unix=time.time(), plan_sha256=sha(PLAN / 'plan.json'),
        frozen_files=len(p['frozen_files']), original_C_sources=15, original_C_groups=67,
        original_matrices=566, first_proved=306, first_unknown=260, fresh_C_sources=6,
        planned_whole_C_comparisons=557, planned_errors=49, planned_CLI=9, planned_builds=4,
        contract_supplement_sha256=sha(supplement_path), planned_compat_C_comparisons=67,
        planned_all_primary_compat_C=624, planned_all_primary_compat_errors=56,
        planned_all_primary_compat_CLI=10, planned_selector_observations=190,
        ABI_requirement='Any added RunMetrics fields require rebuilding each entire cholesky_core and all matching callers from the same mirror/header. Never link new header to old57205 library.',
        authorization='Source mirror implementation and contract/runner freeze only. Root review implementation before isolated configure/build/gates.',
        scope='Static plan and immutable actual-C source/input/reference lineage verified. Shared250k/native bypass/fixed and explicit limits/full-byte comparison are acceptance requirements, not yet execution results. No default, N10000 or performance promotion.')
    (ROOT / 'outputs/stage2-root-vm-nested-runtime-plan.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
