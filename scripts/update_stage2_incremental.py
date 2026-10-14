"""Append independently reviewed milestones without touching paused project11."""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'outputs/stage2-progress.json'
    state = json.loads(path.read_text(encoding='utf-8'))
    paused = dict(state['project11'])
    assert paused['status'] == 'paused_by_user'

    def evidence(relative):
        p = ROOT/relative
        return json.loads(p.read_text(encoding='utf-8')), dict(path=relative, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

    vm, vm_ref = evidence('outputs/stage2-root-prepared-vm-phase2.json')
    cost, cost_ref = evidence('outputs/stage2-root-vm-tos2-measurements.json')
    acceptance, acceptance_ref = evidence('outputs/stage2-root-acceptance-r45.json')
    assert vm['passed'] and vm['actual_output_files'] == 290
    assert cost['passed'] and cost['performance_records'] == 120 and cost['negative_pairs'] == 60
    assert acceptance['passed'] and acceptance['same_regression_records'] == 1099 and acceptance['numeric_controls'] == 523
    for record in (cost, acceptance):
        for relative, expected in record['evidence'].items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected
    for relative, expected in vm['evidence'].items():
        assert hashlib.sha256((ROOT/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase2'/relative).read_bytes()).hexdigest() == expected
    state['project19']['prepared_vm_phase2'] = dict(
        status='correct_but_performance_negative_not_promoted',
        candidate_exe_sha256=vm['candidate_exe_sha256'], actual_C_outputs=290,
        sources=12, source_files=111, ctest=10, original_error_contracts=7,
        native_contract=vm['root_rerun_native_contract'],
        performance=dict(records=120,pairs=60,negative_pairs=60,summaries=cost['summaries'],
                         host_busy_percent_range=cost['host_busy_percent_range']),
        evidence=[vm_ref,cost_ref], scope=cost['scope'],
        limitation='All12 source medians11.89–26.29percent slower than decoded in same candidate. TOS2 remains isolated defaultOFF; phase1bf54 and ordinary4f73 preserved. N10000 TOS2 acceptance not claimed.')
    state['project19']['next_work'] = 'Static design for independent dispatch optimization, preserving original per-opcode steps/error timing/FP bits and default portability; no new measured benefit claimed.'
    state['project27']['ancestor_projection_candidate'].update(
        status='accepted_functional_numeric_candidate_cost_measurement_underway',
        full_acceptance_root_review=acceptance_ref, normal_records=979,
        additional_structure_records=120, numeric_controls=523, ctest=12,
        release_candidate_sha256=acceptance['measured_release_sha256'],
        pending='Complete isolated predeclared full202+fresh48 three alternating pairs, all failure costs included. DefaultR44 remains141/202 until measured cost reviewed. R45 candidate143/202 has59 unresolved; fresh48 remains42/48.')
    state['project18']['next_work'] = 'Static R124 COPY-gap analysis prioritizes cross_group original-root lifetimes; all336/72 input statuses and272/62 legal incumbents retained. R123 lowerbound subsets do not prove official Levels; new age candidate not tested yet.'
    paired, paired_ref = evidence('outputs/stage2-root-resource-pairs-r45.json')
    spine, spine_ref = evidence('outputs/stage2-root-spine-age-r125.json')
    assert paired['passed'] and spine['passed'] and spine['independent_actual_outputs'] == 14
    for record in (paired,spine):
        for relative, expected in record['evidence'].items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected
    state['project27']['ancestor_projection_candidate'].update(
        status='functional_numeric_cost_verified_default_promotion_underway',
        paired_resource_cost=paired['groups'], paired_cost_root_review=paired_ref,
        pending='Promotion authorized after verified2 recoveries/no commonT/peak regressions and explicit+10.41percent hard/+8.72percent fresh48 CPU cost. Actual defaultR44 remains until build/12CTest/default checkpoint inspected; R48 independent future work.')
    state['project18']['spine_age_r125'] = dict(
        status='isolated_small_quality_gain_not_default',input_count=16,actual_selected_outputs=14,
        before_copies=9755,after_copies=9739,improved=6,recovered=0,
        unchanged_statuses=dict(verified=14,budget_exhausted=1,proven_infeasible_under_model=1),
        root_review=spine_ref,scope=spine['scope'])
    state['project18']['next_work'] = 'R125 actual original-prefix age beam saves16COPY on6 of16cross inputs,0recoveries; largest gap unchanged. Preserve full336/72 statuses and existing incumbents; investigate root-use segment transitions without changing original per-node arithmetic.'
    default45, default45_ref = evidence('outputs/stage2-root-default-r45.json')
    final45, final45_ref = evidence('projects/27-aicore-streams/reports/final-checkpoint-batch45.json')
    assert default45['passed'] and default45['ctest'] == 12 and default45['independent_heap_replays'] == 5
    for relative, expected in default45['evidence'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((ROOT/'projects/27-aicore-streams/research/batch45/rollback/inputs/solution/solution.cpp').read_bytes()).hexdigest() == default45['source_sha256']
    assert hashlib.sha256((ROOT/'projects/27-aicore-streams/research/batch45/default-aicore_bench.exe').read_bytes()).hexdigest() == default45['default_exe_sha256']
    state['project27']['historical_r44'] = dict(source_sha256=final45['old_default_R44_source_sha'],
        binary_sha256=final45['old_default_R44_exe_sha'],freeze=final45['old_R44_freeze'],
        hard_legal=141,hard_unresolved=61,rollback_preserved=True)
    state['project27'].update(
        current='R45 is actual default: failed-only input ancestor/workspace closure projection recovers2 hard records,141 to143/202, with59 known feasible unresolved. Fresh48 remains42/48 and6 unresolved. Root1099 normal/structure records,523 numeric controls,185 candidate plans and actual default8 representative cases checked;12/12 default CTest. Cost is explicit+10.41percent hardCPU/+8.72percent fresh48CPU, not speed improvement.',
        source_sha256=default45['source_sha256'],binary_sha256=default45['default_exe_sha256'],
        measured_release_sha256=default45['measured_exe_sha256'],hard202=dict(legal=143,unresolved=59),
        fresh48=dict(legal=42,unresolved=6,recovered=0),
        paired_resource_cost=dict(groups=paired['groups'],root_review=paired_ref,scope=paired['interpretation']),
        limitation='59 old and6 new known witness-feasible records remain unresolved; no universal feasibility/optimality or official/NPU result. Per-trial host load not measured, background apps active. Measured3e827 candidate and actual5acc default are distinct executables with same source/Release flags. R44 rollback and old open TeX preserved.')
    state['project27']['ancestor_projection_candidate'].update(status='validated_actual_default_r45',
        actual_default_root_review=default45_ref,pending='Continue new independentgroup-move R48 research; no R48 quality/performance result yet.')
    for key, refs in [('project19',[vm_ref,cost_ref]),('project27',[acceptance_ref,paired_ref,default45_ref,final45_ref]),('project18',[spine_ref])]:
        existing = {r.get('path') if isinstance(r,dict) else r for r in state[key]['evidence']}
        state[key]['evidence'] += [r for r in refs if r['path'] not in existing]
    state['updated_unix'] = time.time()
    state['completion'] = 'Not achieved.11 explicitly paused;18 official Level1–3 unproved, R125 isolated16COPY improvement only;19 TOS2 rejected by all60 performance pairs and independent dispatch work pending;27 actual defaultR45 still59 old and6 new known feasible hard cases unresolved. Continue18/19/27.'
    assert state['project11'] == paused
    path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(updated=path.as_posix(),project11_status=paused['status'],status=state['status']),ensure_ascii=False))
    import update_stage2_current
    update_stage2_current.main()


if __name__ == '__main__':
    main()
