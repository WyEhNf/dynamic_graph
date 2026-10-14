"""Record verified resumed-stage evidence without changing paused project 11."""
import hashlib
import json
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root/'outputs/stage2-progress.json'
state = json.loads(path.read_text(encoding='utf-8'))
assert state['project11']['status'] == 'paused_by_user'
paused = dict(state['project11'])

def evidence(relative):
    p = root/relative
    data = json.loads(p.read_text(encoding='utf-8'))
    return data, dict(path=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

comb, comb_ref = evidence('projects/18-isa-scheduler/experiments/r90-comb-early-holdout/report.json')
assert comb['summary']['research_portfolio']['verified'] == 48
assert comb['summary']['research_portfolio']['total_inserted_copies_successes'] == 0
milestone, milestone_ref = evidence('projects/18-isa-scheduler/experiments/milestone-level-r91-336/report.json')
successes = [r for r in milestone['records'] if r['variant']=='research_portfolio' and r['status']=='verified']
assert len(successes) == 272
mean_ratio = sum(r['inserted_copies']/r['output_count'] for r in successes)/len(successes)
serialized, serialized_ref = evidence('projects/18-isa-scheduler/experiments/milestone-level-r91-336/serialized-replay.json')
identity, identity_ref = evidence('projects/18-isa-scheduler/experiments/milestone-level-r91-336/identity-replay.json')
assert serialized['verified'] == 272
wire, wire_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-metadata-wire/report.json')
assert wire['passed'] and wire['runtime_comparisons'] == 60
minimum, minimum_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-smallest-metadata/report.json')
assert minimum['passed'] and minimum['runtime_comparisons'] == 24
assert all(r['ast_compilations']==r['llvm_ir_compilations']==1 for r in minimum['sources'])
suite19, suite19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-metadata-wire/full-suite-summary.json')
assert suite19['passed'] and suite19['ctest_passed']==8 and suite19['comparisons']==405 and suite19['rejections']==53
default19, default19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-default-metadata-audit/report.json')
assert default19['passed']
hard, hard_ref = evidence('projects/27-aicore-streams/reports/paired-hard-batch36-summary.json')
for run in hard['runs']:
    assert run['comparison']['before']['passed'] == 133
    assert run['comparison']['after']['passed'] == 137
    assert not run['comparison']['lost'] and run['comparison']['model_disagreements'] == 0
overlap, overlap_ref = evidence('outputs/stage2-memory-structure/report.json')
assert overlap['passed'] and overlap['excluded'] == 0
structure, structure_ref = evidence('outputs/stage2-memory-structure/sp-classification.json')
research27, research27_ref = evidence('projects/27-aicore-streams/reports/hard-functional-batch38.json')
assert research27['summary']['passed'] == 139 and research27['summary']['failed'] == 63
final27, final27_ref = evidence('projects/27-aicore-streams/reports/final-hard-batch39.json')
paired27, paired27_ref = evidence('projects/27-aicore-streams/reports/paired-hard-batch39-summary.json')
forkjoin27, forkjoin27_ref = evidence('projects/27-aicore-streams/reports/paired-forkjoin-batch39-summary.json')
assert final27['status'] == 'validated_default_milestone'
assert final27['strict_records'] == 979 and final27['optimum_audit_checked'] == 144
assert final27['hard_legal'] == 139 and final27['hard_unresolved'] == 63
assert final27['serial_checks'] == 1120 and final27['certificates'] == 33
for report, before, after in ((paired27, 137, 139), (forkjoin27, 14, 36)):
    assert len(report['runs']) == 3
    assert report['current_solution_sha256'] == final27['source_sha256']
    assert report['current_exe_sha256'] == final27['default_exe_sha256']
    for run in report['runs']:
        comparison = run['comparison']
        assert comparison['before']['passed'] == before
        assert comparison['after']['passed'] == after
        assert not comparison['lost'] and comparison['model_disagreements'] == 0
        assert comparison['regressed_T'] == comparison['regressed_peak_at_equal_T'] == 0
for relative, expected in (
    ('projects/27-aicore-streams/research/batch39/solution.cpp', final27['source_sha256']),
    ('projects/27-aicore-streams/research/batch39/default-aicore_bench.exe', final27['default_exe_sha256']),
):
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
grain19, grain19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain48/run-plan-v2.json')
grain_result19, grain_result19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain48/performance.json')
grain_summary19, grain_summary19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain48/comparison-summary.json')
assert grain_result19['passed'] and grain_result19['status'] == 'complete'
assert len(grain_result19['records']) == grain_summary19['records'] == 45
assert all(r['byte_identical'] for r in grain_result19['records'])
assert grain_result19['plan_sha256'] == grain19_ref['sha256']
oracle18, oracle18_ref = evidence('projects/18-isa-scheduler/experiments/r94-raw-cut-oracle/report.json')
assert oracle18['count'] == 1200 and not oracle18['violations']
assert oracle18['statuses'] == dict(optimal=1057,unknown_budget=140,proven_infeasible_identity_model=3)
root_review, root_review_ref = evidence('outputs/stage2-root-review.json')
opportunity18, opportunity18_ref = evidence('outputs/stage2-copy-opportunity.json')
assert opportunity18['verified'] == 272 and sum(opportunity18['statuses'].values()) == 336
holdout19, holdout19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain128-holdout/run-plan-v2.json')
assert holdout19['new_reference_shapes'] == [6145,8193]
assert len(holdout19['schedule']) == holdout19['planned_records'] == 30
references19, references19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain128-holdout/reference-preparation-v2.json')
holdout_result19, holdout_result19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-grain128-holdout/performance.json')
assert references19['passed'] and references19['status'] == 'complete_performance_not_started'
assert holdout_result19['passed'] and holdout_result19['status'] == 'complete'
assert len(holdout_result19['records']) == 30
assert all(r['byte_identical'] and r['effective_tile_size']==r['expected_tile'] for r in holdout_result19['records'])
assert holdout_result19['plan_sha256'] == holdout19_ref['sha256']
extreme27, extreme27_ref = evidence('outputs/stage2-memory-structure/extreme-memory-r39-result.json')
assert extreme27['summary'] == dict(total=1,passed=0,failed=1)
assert extreme27['cases'][0]['valid'] and extreme27['cases'][0]['models_equal']
assert extreme27['cases'][0]['peak_memory'] == 0

bound_review18, bound_review18_ref = evidence('outputs/stage2-root-review-r99.json')
assert bound_review18['passed'] and bound_review18['independent_new_certificates'] == 138
assert bound_review18['positive_reduction_certificates'] == 2
assert bound_review18['successful_subset']['count'] == 272
assert bound_review18['successful_subset']['mean_lower_copy_output'] > .10
bound99, bound99_ref = evidence('projects/18-isa-scheduler/experiments/r99-reduction-global-audit/report.json')
assert bound99['all_inputs']['count'] == 336 and bound99['previous_successes_only']['count'] == 272
phase100, phase100_ref = evidence('projects/18-isa-scheduler/experiments/r100-phases-336/report.json')
phase101, phase101_ref = evidence('projects/18-isa-scheduler/experiments/r101-root-phase-heldout/report.json')
phase_summaries = []
for report, count, legal, expected_delta in ((phase100,336,272,-73),(phase101,64,60,-268)):
    assert report['case_count'] == count
    before, after = report['paired_variants']['before'], report['paired_variants']['after']
    assert report['summary'][before]['verified'] == report['summary'][after]['verified'] == legal
    assert report['summary'][before]['statuses'] == report['summary'][after]['statuses']
    pairs = report['paired']
    assert len(pairs) == count and all(p['before_status'] == p['after_status'] for p in pairs)
    common = [p for p in pairs if p['before_status'] == p['after_status'] == 'verified']
    assert len(common) == legal and sum(p['copy_delta'] for p in common) == expected_delta
    assert all(p['copy_delta'] <= 0 for p in common)
    records = [r for r in report['records'] if r['variant'] == after and r['status'] == 'verified']
    phase_summaries.append(dict(attempted=count,legal=legal,improved=sum(p['copy_delta']<0 for p in common),
                                equal=sum(p['copy_delta']==0 for p in common),regressed=0,
                                copy_delta=expected_delta,
                                successful_subset_mean_copy_output=sum(r['inserted_copies']/r['output_count'] for r in records)/legal))
phase_replay_refs = []
for name, count in (('r100-phases-336',272),('r101-root-phase-heldout',60)):
    for file, key in (('serialized-replay.json','verified'),('identity-replay.json','verified_identity_outputs')):
        replay, ref = evidence(f'projects/18-isa-scheduler/experiments/{name}/{file}')
        assert replay[key] == replay['attempted'] == count
        phase_replay_refs.append(ref)
release19, release19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-runtime-release/release-manifest.json')
assert release19['status'] == 'verified_current_ordinary_runtime'
assert release19['ctest']['passed'] == 8 and release19['ctest']['original_c_comparisons'] == 405
assert release19['ctest']['rejections'] == 53 and release19['wire']['comparisons'] == 60 and release19['smallest']['comparisons'] == 24
assert release19['packed_ready_keys'] == 'OFF' and release19['frontend_default_schema'] == 2
for p in (release19['installed_runtime'],release19['frozen_runtime']):
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == release19['runtime_sha256']
for section in ('wire','smallest'):
    item = release19[section]
    report = json.loads(Path(item['report']).read_text(encoding='utf-8'))
    assert hashlib.sha256(Path(item['report']).read_bytes()).hexdigest() == item['sha256']
    assert report['passed'] and report['runtime_comparisons'] == item['comparisons']
for row in release19['ctest']['rows']:
    assert hashlib.sha256(Path(row['frozen_report']).read_bytes()).hexdigest() == row['sha256']
repaired_extreme27, repaired_extreme27_ref = evidence('outputs/stage2-memory-structure/extreme-memory-r42-root-result.json')
assert repaired_extreme27['summary'] == dict(total=1,passed=1,failed=0)
assert not repaired_extreme27['cases'][0]['valid'] and repaired_extreme27['cases'][0]['models_equal']
release_review, release_review_ref = evidence('outputs/stage2-root-release-review.json')
assert release_review['passed']
assert release_review['project19']['official_vendor_archive_files_checked'] == 255
assert release_review['project19']['full_native_containers_decoded_by_python'] == 42
assert release_review['project27']['direct_frozen_r39_to_r42_normal_records'] == 979
numeric42, numeric42_ref = evidence('projects/27-aicore-streams/reports/final-checkpoint-batch42.json')
direct42, direct42_ref = evidence('projects/27-aicore-streams/reports/direct-normal-r39-batch42.json')
assert numeric42['status'] == 'validated_correctness_default_milestone'
assert numeric42['numeric_fixed_plan_gold'] == 523 and numeric42['priority_arbitrary_precision_gold'] == 20180
assert numeric42['hard_legal'] == 139 and numeric42['known_witness_unresolved'] == 63
assert direct42['all_same'] and direct42['records'] == 979
for relative, expected in (
    ('projects/27-aicore-streams/research/batch42/solution.cpp',numeric42['source_sha256']),
    ('projects/27-aicore-streams/src/simulator.cpp',numeric42['independent_simulator_sha256']),
    ('projects/27-aicore-streams/research/batch42/default-aicore_bench.exe',numeric42['default_exe_sha256']),
):
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
compressed19, compressed19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-metadata-zlib/manifest.json')
assert compressed19['status'] == 'verified_optional_compressed_metadata'
assert compressed19['ctest'] == 9 and compressed19['original_c_comparisons'] == 72
assert not compressed19['compressed_option_default'] and compressed19['auto_policy_unchanged']
compressed_min19, compressed_min19_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-compressed-smallest/manifest.json')
compressed_min_review19, compressed_min_review19_ref = evidence('outputs/stage2-root-compressed-choice-review.json')
assert compressed_min19['status'] == 'verified_final_container_byte_minimum'
assert compressed_min_review19['passed'] and compressed_min_review19['independently_decoded_candidates'] == 36
assert compressed_min_review19['original_c_full_file_records'] == 24
assert [s['after'] for s in compressed_min_review19['actual_final_byte_selections']] == [731,735,912,481,397,225]
phase102, phase102_ref = evidence('projects/18-isa-scheduler/experiments/r102-phase-10000/report.json')
phase_source18, phase_source18_ref = evidence('projects/18-isa-scheduler/experiments/r102-phase-validation/source-provenance.json')
assert phase102['case_count'] == 10000 and phase_source18['tests']['count'] == 149
for variant in phase102['paired_variants'].values():
    assert phase102['summary'][variant]['verified'] == 9998
    assert phase102['summary'][variant]['total_inserted_copies_successes'] == 562
for relative, expected in phase_source18['core_manifest'].items():
    p = root/'projects/18-isa-scheduler'/phase_source18['snapshot']/Path(relative).name
    assert hashlib.sha256(p.read_bytes()).hexdigest() == expected
for relative, expected in phase_source18['evidence_sha256'].items():
    p = root/'projects/18-isa-scheduler'/relative
    assert hashlib.sha256(p.read_bytes()).hexdigest() == expected
resource43, resource43_ref = evidence('projects/27-aicore-streams/reports/final-checkpoint-batch43.json')
resource_review43, resource_review43_ref = evidence('outputs/stage2-root-resource-pairs-r43.json')
assert resource43['status'] == 'validated_equivalent_resource_default_milestone'
assert resource43['strict_regression_records'] == 979 and resource43['known_witness_unresolved'] == 63
assert resource43['numeric_fixed_plan_gold'] == 523
assert resource_review43['passed']
for relative, expected in (
    ('projects/27-aicore-streams/research/batch43/solution.cpp',resource43['source_sha256']),
    ('projects/27-aicore-streams/research/batch43/default-aicore_bench.exe',resource43['default_exe_sha256']),
):
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
root_control43, root_control43_ref = evidence('outputs/stage2-memory-structure/extreme-memory-r43-default-root-result.json')
assert root_control43['summary'] == dict(total=1,passed=1,failed=0) and not root_control43['cases'][0]['valid']
age105, age105_ref = evidence('projects/18-isa-scheduler/experiments/r105-age-budget250/report.json')
age_review105, age_review105_ref = evidence('outputs/stage2-root-age-replay-r105.json')
assert age_review105['passed'] and age_review105['verified'] == 12
assert age105['case_count'] == 16 and age105['summary']['age_fast']['verified'] == 12
assert age105['summary']['age_fast']['total_inserted_copies_successes'] == 2876

state['updated_unix'] = time.time()
state['project18'] = dict(current='R91 complete milestone: 141 regressions and fresh 10000 graphs; 9998 legal outputs/2 identity-model certificates. All 336 retained: 272 legal, 47 identity-model certificates, 9 budget and 8 heuristic failures. Joint 272 COPY195525 to194736 (8 improve/264 equal/0 regress), median speedup0.976. All 272 serialized/identity replays passed. R90 strict comb holdout48/48 zero COPY vs29/48 old legal; research portfolio remains opt-in.',
                         successful_subset_mean_copy_output=mean_ratio,all_input_count=336,
                         evidence=[comb_ref,milestone_ref,serialized_ref,identity_ref,oracle18_ref,root_review_ref,opportunity18_ref],
                         new_bound_audit='R93 forced DAG interval bound mathematically reviewed within the stated identity model. R94 independent raw-JSON age-state Dijkstra: 1200 graphs,1057 complete optima,3 complete identity-model infeasible,140 budget-unknown;23 positive certificates with complete optima,0 violations. New consumer portfolio still undergoing full336 comparison.',
                         limitation='Mean13.918 percent is only the 272 successful subset, still above Level1. Official Level2 and ratio denominator remain unspecified. Necessary bounds are identity-model scoped, and the full336 corpus includes47 infeasible identities; no official Level failure claim. Wall-time budgets cause baseline candidate-completion variation between rounds; compare within each pair.')
state['project19'] = dict(current='Metadata phase complete: opt-in DYNCHOL3 and --smallest-metadata select among six lossless formats after one AST/IR compilation. 8/8 CTest (405 strict C comparisons/53 rejections), wire60 and min24 strict comparisons pass; default schema2 output46/46 unchanged. Noop306 to284; scalar2250 to1719, page2655 to1934, blocked3739 to2626. Default schema2 retained. Grain48 complete45/45 original-C whole-file matches; B48 rejected. Independent B128 holdout complete30/30 exact C comparisons: fresh6145/8193 medians improve7.20/7.74 percent,5/5 pairs each; old10000 repeat improves7.39 percent,4/5 pairs with one regression retained. Preparing coherent normal-build Runtime release for already verified Metadata capabilities; tile AUTO unchanged.',
                         evidence=[wire_ref,minimum_ref,suite19_ref,default19_ref,grain_result19_ref,grain_summary19_ref,references19_ref,holdout_result19_ref,'projects/19-dynamic-graph/artifacts/stage2-packed-ready/performance.json','projects/19-dynamic-graph/artifacts/stage2-metadata-tables/report.json'],
                         completed_grain48_plan=grain19_ref,completed_grain128_plan=holdout19_ref,
                         limitation='Metadata byte reduction is not official 15-point conversion. Packed ready queue remains OFF. B128 ranges overlap and only16 workers/three shapes/one source were measured, so no universal performance or AUTO threshold promotion. Historical baselines stay frozen during normal-build integration.')
state['project27'] = dict(current='R39 default frozen and independently validated: three full-202 pairs137 to139 legal, two recovered/0 lost; all common137 T/peak equal. All solve wall24.731626 to25.173202 seconds (+1.79 percent), threadCPU22.859375 to23.578125 (+3.14 percent), including failures. New36 independently witnessed nested-forkjoin graphs14 to36 legal, commonT/peak retained; all solve wall1.985639 to1.787678 and CPU1.796875 to1.593750 seconds. 979strict,144optima/33certificates,1120frontier checks,5/5CTest and warning-free standalone compilation pass. 63 witness-feasible hard cases remain unsolved.',
                         evidence=[final27_ref,paired27_ref,forkjoin27_ref,hard_ref,research27_ref,overlap_ref,structure_ref,root_review_ref,extreme27_ref],
                         known_correctness_issue='Root reproduced an accepted int64 boundary counterexample against frozen R39: hardware capacity INT64_MAX, single operator workspace6e18/output6e18. Required12e18 exceeds capacity, yet both models return valid and peak0. Shared signed-add overflow invalidates model agreement as an independent boundary proof. Dedicated correctness repair and boundary controls take priority; R39 previous normal-range results remain historical evidence.',
                         source_sha256=final27['source_sha256'],binary_sha256=final27['default_exe_sha256'],
                         lower_bound=dict(independent_subset_tests=400,hard_cases=202,improved_cases=24,improved_failed_cases=5,exceeds_capacity=0,failed_cases_above_frontier_768_limit=18),
                         limitation='No official score, real NPU validation or universal solver guarantee. New static necessary memory bound does not certify any remaining case impossible. Only1/65 R36 failures was augmented TTSP, maximum outdegree3; this input-only structural discovery led to a general strict nested fork/join candidate, not witness matching.')
state['project18'].update(
    current='R100 opt-in root-phases portfolio: all336 retained (272 legal/47 identity-model certificates/9 budget/8 heuristic failures), COPY194251 to194178,8 improve/264 equal/0 regress. Fresh R10164 graphs retain60 legal/3 certificates/1 budget, COPY75048 to74780,21 improve/39 equal/0 regress. All272 and60 saved outputs independently replayed as raw identities and symbolic/three signed integer inputs. Default v14 remains unchanged.',
    successful_subset_mean_copy_output=phase_summaries[0]['successful_subset_mean_copy_output'],
    phase_pairs=phase_summaries,
    new_bound_audit='R99 necessary COPY bounds: full336 lower mean11.7792 percent and prior272 successful subset10.086440523 percent using equal-block output denominators. Root independently checked138 new certificates, including2 complete shared reductions, from raw JSON without importing project modules. Mathematical proof scope and older-copy age inequality reviewed. These are necessary lower bounds, not achieved COPY counts or official Level failures.',
    limitation='Global Level1–3 remains unproved. Current self-generated successful mean remains above10 percent; necessary bound now exceeds10 percent even on the same272 success subset in the strict identity model. Official Level2, denominator and averaging remain unspecified. Fresh shared-family COPY savings have measurable overhead; portfolio stays explicit opt-in. Failure states and wall-budget-dependent baseline variations are retained.')
state['project18']['evidence'].extend([phase100_ref,phase101_ref,bound99_ref,bound_review18_ref,*phase_replay_refs])
state['project18']['evidence'].extend([phase102_ref,phase_source18_ref])
state['project18']['phase_frozen_validation'] = dict(snapshot=phase_source18['snapshot'],
    core_aggregate_sha256=phase_source18['core_aggregate_sha256'],regression_tests=149,
    fresh_graphs=10000,legal=9998,identity_model_certificates=2,copies_both_frozen_r91_and_phase=562,
    limitation='Frozen explicit phase portfolio, not a change to the default auto strategy or an official Level certificate. Whole-source SHA distinction for the CLI-only R100 change is retained in provenance.')
state['project18']['evidence'].extend([age105_ref,age_review105_ref])
state['project18']['age_cache_candidate'] = dict(
    current='R105 bounded physical-age cached column scheduler on the same16 original dot inputs:12 supported legal,4 restricted matcher failures; legal COPY4112 to2876.4095/W8 COPY3138 to2196;52/247/1014 W8 improve28 to19,178 to124,768 to537. Root independently replayed all12 exact original identities/ordered references/registers and window distances from raw JSON, no project imports.',
    default=False,independent_raw_identity_replays=12,
    limitation='Four matcher failures are not infeasibility certificates. Different row counts, initial topological order and original argument-order holdouts pending, then complete336 portfolio comparison with old fallback. R105 functional timing observed concurrent work and is not an isolated causal speed claim; no new global Level success claim.')
state['project19']['current'] = state['project19']['current'].replace(
    'Preparing coherent normal-build Runtime release for already verified Metadata capabilities; tile AUTO unchanged.',
    'Ordinary Release runtime now installed and frozen at SHA4f73ceaa:8/8 CTest,60 wire and24 minimum comparisons plus the documented quickstart pass. Tile AUTO and frontend default schema2 unchanged. Further generic lossless compression is isolated opt-in work, not yet part of this release.')
state['project19']['released_runtime_sha256'] = release19['runtime_sha256']
state['project19']['evidence'].append(release19_ref)
state['project19']['evidence'].extend([compressed19_ref,release_review_ref])
state['project19']['optional_compression'] = dict(
    current='Complete bounded RFC1950 container implemented with pinned official zlib1.3.2 static source; optional build only.9/9 CTest,72 whole-file original-C comparisons,42 native/Python roundtrips,26 corrupt-container and4 inner-schema rejections. Root verified all255 official archive/vendor files, decoded42 native-produced whole Metadata files independently, and recomputed57 full-file sizes.',
    runtime_sha256=compressed19['runtime_sha256'],
    six_current_bytes=[760,763,958,492,407,225],
    further_final_size_selection='Root measured compress-all-six selection can reach731/735/912/481/397/225 bytes. Frontend implementation and actual-C validation in progress; these are current frozen candidate opportunities, not yet installed selector results.',
    limitation='Preserves complete graph/PROGRAM/dependencies; no official15-point or kernel speed claim. Ordinary4f73 release remains unchanged; loading/decompression/parser time recorded separately from compute.')
state['project19']['evidence'].extend([compressed_min19_ref,compressed_min_review19_ref])
state['project19']['optional_compression']['six_current_bytes'] = [731,735,912,481,397,225]
state['project19']['optional_compression']['further_final_size_selection'] = 'Implemented and independently frozen: --smallest-metadata plus --compress-metadata selects minimum final actual bytes across all six complete encodings with deterministic tie rule.24 new whole-file actual-C comparisons pass,36 candidate containers decoded/expanded exactly,AST/IR each once per source. Root independently decoded all36 actual saved candidates and checked the final byte/tie-rule selection. Prior uncompressed selector/default and explicit format paths retained; ordinary4f73 runtime unchanged.'
state['project27']['evidence'].extend([repaired_extreme27_ref,numeric42_ref,direct42_ref,release_review_ref])
state['project27']['historical_r39'] = dict(source_sha256=state['project27']['source_sha256'],binary_sha256=state['project27']['binary_sha256'],known_issue=state['project27'].pop('known_correctness_issue'))
state['project27'].update(
    current='R42 correctness repair is now default: checked actual memory/time arithmetic and exact multiply-then-divide priority scores.523 independent Python-bigint fixed plans (209 legal/314 expected rejection),20180 exact score controls,UBSan and10/10 CTest pass. Root independently reproduced the original R39 false acceptance and verified candidate rejection. Direct frozen R39/R42 comparisons confirm all979 normal strict records have identical pass/T/peak;202 hard cases remain139 legal/63 unresolved and36 new nested-forkjoin cases remain legal. R41 resource changes still isolated for later replay.',
    source_sha256=numeric42['source_sha256'],binary_sha256=numeric42['default_exe_sha256'],
    numerical_correctness='Historical raw signed overflow false acceptance repaired in R42; valid INT64_MAX peak/time endpoints are preserved. Full historical output sum can exceed INT64_MAX when values were released, so whole-graph sum is not used to reject feasible graphs. Boundary evidence is stronger than two C++ models merely agreeing, but is not a universal correctness proof.',
    limitation='No official score or real NPU validation. All63 witness-feasible unresolved cases remain; numeric correctness is not a new feasibility recovery. Single-run validation timing is not a speedup claim; resource optimization remains separate.')
state['project27']['historical_r42'] = dict(source_sha256=numeric42['source_sha256'],binary_sha256=numeric42['default_exe_sha256'],status=numeric42['status'])
state['project27']['evidence'].extend([resource43_ref,resource_review43_ref,root_control43_ref])
state['project27'].update(
    current='R43 equivalent resource optimization now default, retaining R42 checked numerical semantics. Streaming best greedy macro, canonical pending-set bitmask deduplication and linear explicit fork/join order emission.979 strict regressions,144 optimum checks/33 certificates,523 real-source UBSan fixed plans and10/10 CTest pass.332 macro order/work/state/budget equivalence cases and105 structure-order cases pass.202 difficulty and36 structural cases retain every per-record pass/T/peak in all3 paired runs;63 known feasible cases still unresolved. Root independently checked raw paired reports and reproduced correct default rejection of the historical overflow counterexample.',
    source_sha256=resource43['source_sha256'],binary_sha256=resource43['default_exe_sha256'],
    paired_resource_cost=dict(
        hard202=resource_review43['groups']['hard'],
        structure36=resource_review43['groups']['forkjoin'],
        scope='Same Release flags and isolated3-round alternating local pairs; measured candidate binary is separately frozen from final default rebuild. All failures included.',
        interpretation='For202 CPU ratio of separate medians0.942689 (-5.73 percent), while median per-pair ratio0.979433 (-2.06 percent). All3 per-pair improvements0.75–5.73 percent retained.36 has one worse CPU pair and slightly worse aggregate wall time; no stable structural acceleration or RAM-reduction claim.'),
    limitation='Resource equivalence reduces some local search cost; it recovers none of63 witness-feasible unresolved cases. No official score/real NPU/universal solver guarantee. Necessary bounds and numeric controls do not prove all hidden inputs feasible or optimally scheduled.')
age109_review, age109_review_ref = evidence('outputs/stage2-root-age-portfolio-review-r109.json')
age109_source, age109_source_ref = evidence('projects/18-isa-scheduler/experiments/r109-age-validation/source-provenance.json')
age109_fuzz, age109_fuzz_ref = evidence('projects/18-isa-scheduler/experiments/r109-age-10000/report.json')
age107, age107_ref = evidence('projects/18-isa-scheduler/experiments/r107-age-portfolio-336/report.json')
age108, age108_ref = evidence('projects/18-isa-scheduler/experiments/r108-age-portfolio-heldout/report.json')
assert age109_review['passed'] and age109_review['verified'] == 334
assert age109_review['frozen_core_sha256'] == age109_source['core_aggregate_sha256']
for relative, expected in age109_source['core_manifest'].items():
    frozen_file = root/'projects/18-isa-scheduler'/age109_source['snapshot']/Path(relative).name
    assert hashlib.sha256(frozen_file.read_bytes()).hexdigest() == expected
for relative, expected in age109_source['evidence_sha256'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler'/relative).read_bytes()).hexdigest() == expected
tests109 = (root/'projects/18-isa-scheduler/experiments/r109-age-validation/tests.log').read_text(encoding='utf-8')
assert 'Ran 153 tests in 45.037s' in tests109 and '\nOK\n' in tests109
for variant in ('phase_r102', 'age_portfolio'):
    assert age109_fuzz['summary'][variant]['statuses'] == {'proven_infeasible_under_model': 2, 'verified': 9998}
    assert age109_fuzz['summary'][variant]['total_inserted_copies_successes'] == 562
for audited in age109_review['reviews']:
    assert audited['regressed'] == 0
for dataset, expected_count, expected_copies in ((age107,272,192929),(age108,62,15538)):
    assert dataset['summary']['age_portfolio']['verified'] == expected_count
    assert dataset['summary']['age_portfolio']['total_inserted_copies_successes'] == expected_copies
state['project18']['historical_age_cache_probe'] = state['project18'].pop('age_cache_candidate')
state['project18']['current'] = 'R109 frozen opt-in age_portfolio validated:153 regressions and10000 graphs9998 legal/2 model certificates,COPY562 unchanged. Original336 retain272 legal/47 certificates/9 budget/8 heuristic failures; COPY194519 to192929,5 improve267 equal0 regress. New72 retain62 legal/9 budget/1 heuristic failure; COPY21752 to15538,21 improve41 equal0 regress. Root independently replayed all334 saved outputs including16 register-hazard blocks and checked every frozen source/evidence SHA. Default auto v14 unchanged.'
state['project18']['successful_subset_mean_copy_output'] = sum(r['inserted_copies']/r['output_count'] for r in age107['records'] if r['variant']=='age_portfolio' and r['status']=='verified') / 272
state['project18']['age_portfolio'] = dict(status='validated_frozen_opt_in',
    core_sha256=age109_source['core_aggregate_sha256'], regressions=153, small_graphs=10000,
    full336={k:v for k,v in age109_review['reviews'][0].items() if k not in ('checks','evidence')},
    heldout72={k:v for k,v in age109_review['reviews'][1].items() if k not in ('checks','evidence')},
    heldout_successful_subset_mean_copy_output=sum(r['inserted_copies']/r['output_count'] for r in age108['records'] if r['variant']=='age_portfolio' and r['status']=='verified')/62,
    attribution='Of1590 fewer COPY in R107,1236 came from new reduction_age;354 came from legacy pressure wall-budget completion variation. Functional timings ran with other projects; no isolated speedup claim.',
    correctness='Root raw identities, exact ordered operands and physical window, complete original-node permutation, and rebuilt GET/SET RAW/WAR/WAW edges independently pass334 outputs. This proves those outputs under deterministic primitive semantics for all initial registers; does not prove universal acceptance or optimality.')
state['project18']['evidence'] += [age109_review_ref,age109_source_ref,age109_fuzz_ref,age107_ref,age108_ref]
state['project18']['limitation'] = 'Original272 successful-subset equal-block mean13.7396 percent remains above10 percent. New62-of72 successful subset9.3227 percent does not establish Level1 for all inputs or official tests. All408 inputs and47 model-scoped certificates/27 budget-heuristic failures retained. Official Level2/denominator unspecified; Level1–3 acceptance unproved.'
report109, report109_ref = evidence('projects/18-isa-scheduler/experiments/r109-age-validation/report-provenance.json')
for relative, expected in report109['sha256'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler'/relative).read_bytes()).hexdigest() == expected
state['project18']['evidence'].append(report109_ref)
state['project18']['age_portfolio']['report'] = dict(source='projects/18-isa-scheduler/reports/project18-age-research.tex', pages=4, compiler='Root builtin compile_latex_document success; agent separate XeLaTeX4-page render QA recorded in report-provenance.')
shallow44_root, shallow44_root_ref = evidence('outputs/stage2-root-shallow-recovery-r44.json')
assert shallow44_root['passed'] and shallow44_root['recovered_records']==2
for artifact in shallow44_root['evidence'].values():
    assert hashlib.sha256((root/artifact['path']).read_bytes()).hexdigest() == artifact['sha256']
state['project27']['shallow_recovery_candidate'] = dict(status='isolated_preliminary_not_default', recovered_records=2, recovered_topologies=1,
    root_independent_checks=shallow44_root['checks'], evidence=shallow44_root_ref,
    scope='Root Python bigint validates the two actual serial plans against unchanged202 hardware/nodes/deadline. Complete202/36/new72 candidate regression still in progress; default43 remains139 legal63 unsolved.',
    producer_sort_condition='Constant live prefix and independent newly-opened producers whose output persists until the consumer. If nonzero prefix output is freed inside the segment, descending-W optimality does not apply; root preserved121-versus111 counterexample.')
functional44_root, functional44_root_ref = evidence('outputs/stage2-root-functional-plans-r44.json')
assert functional44_root['passed'] and functional44_root['independently_validated'] == 249
assert functional44_root['recovered_records'] == 6
for suite in functional44_root['suites']:
    assert suite['lost'] == 0
    for artifact in suite['evidence'].values():
        assert hashlib.sha256((root/artifact['path']).read_bytes()).hexdigest() == artifact['sha256']
state['project27']['shallow_recovery_candidate'].update(status='full_functional_candidate_not_default',
    source_sha256='d88860f2da7eb9b18d0271abec308a2aa1e6f426742eeecd01d58d87fd7034a3',
    full_hard202=dict(before_legal=139,after_legal=141,unresolved=61),
    new_heldout72=dict(before_legal=68,after_legal=72,recovered_records=4),
    full_functional_root_review=functional44_root_ref,
    recovered_records=6,
    scope='Root independent heap-event Python model verified every249 passing actual candidate plan in202/36/new72, including explicit8-stream Wait/Record. All243 common old successes retain exact T/peak. Original2 recovered parameter records plus4 fresh seed records; no default promotion/performance claim. Actual effective source is expanded single file d888; initial1dd textual LF hash was replaced by actual on-disk CRLF bytes hash.',
    root_independent_checks='Complete node coverage, exact explicit direct cross-stream sync, same-clock completion/start rules, separate pools, BEGIN W+O, END direct-last-parent release, sinks through T, duration and deadline; arbitrary-precision memory with int64 timestamp limits.61 original hard cases remain unresolved.')
avx_plan, avx_plan_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-avx512/initial-plan.json')
avx_features, avx_features_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-avx512/cpu-features.json')
assert avx_plan['cpu_features'] == avx_features
assert avx_features['xcr0']&0xe6 == 0xe6
for field,bit,leaf in [('avx512f',16,'leaf7_ebx'),('avx2',5,'leaf7_ebx'),('xsave',26,'leaf1_ecx'),('osxsave',27,'leaf1_ecx'),('avx',28,'leaf1_ecx'),('fma',12,'leaf1_ecx')]:
    assert avx_features[field] == bool(avx_features[leaf]&(1<<bit))
state['project19']['avx512_candidate'] = dict(status='isolated_correctness_in_progress_performance_not_started',
    actual_cpuid_features=avx_features, evidence=[avx_plan_ref,avx_features_ref],
    scope='Explicit optional row-major4-row16-column AVX512F kernel. DefaultOFF, ordinary4f73 Runtime and autoAVX2 unchanged. Primary Intel/AMD sources and frozen AVX2 asm inspected before implementation; Zen4 double-pumped256 execution means no predicted2x claim. Full-C bit comparisons pending; root recorded feature-bit/XCR0 consistency and noYMM/ZMM/EVEX in saved entry/detector object asm.')
retention113, retention113_ref = evidence('projects/18-isa-scheduler/experiments/r113-retention-stage/source-provenance.json')
retention_root, retention_root_ref = evidence('outputs/stage2-root-retention-closure-r113.json')
rook_root, rook_root_ref = evidence('outputs/stage2-root-rook-r114.json')
oracle111, oracle111_ref = evidence('projects/18-isa-scheduler/experiments/r111-retention-oracle/report.json')
oracle112, oracle112_ref = evidence('projects/18-isa-scheduler/experiments/r112-retention-negative-holdout/report.json')
assert retention_root['passed'] and retention_root['certificates'] == 9
assert rook_root['passed'] and rook_root['new_identity_model_infeasible'] == 6
for relative, expected in retention113['core_manifest'].items():
    frozen = root/'projects/18-isa-scheduler/experiments/r113-retention-stage'/relative
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == expected
for relative, expected in retention113['evidence_sha256'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler'/relative).read_bytes()).hexdigest() == expected
for relative, expected in rook_root['evidence'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler/experiments/r114-rook-failures'/relative).read_bytes()).hexdigest() == expected
assert oracle111['joint_completed'] == 1992 and not oracle111['violations']
assert oracle112['joint_completed'] == 232 and not oracle112['violations']
state['project18']['offline_retention_diagnostics'] = dict(
    original_unresolved=17, new_closed_mask_certificates=9, new_rook_minor_certificates=6,
    remaining_unknown=2, new_legal_outputs=0,
    core_snapshot_sha256=retention113['core_aggregate_sha256'],
    physical_oracle_comparisons=dict(random_joint_complete=1992,negative_holdout_joint_complete=232,
                                    random_comparisons=2000,negative_holdout_comparisons=240,
                                    free_order_negative_holdout=46,contradictions=0),
    scope='Offline refinement only: original336 still272 emitted legal outputs. Prior47 plus15 newly proved identity-model infeasible,2 matrix unknown. Does not change age_portfolio/default, COPY counts, official Level result, or treat theorem<=W as feasibility. Root checked actual raw closed masks and all8 rook minors,6 bounds exceed capacity; hazard edges excluded from minor graph.')
state['project18']['evidence'] += [retention113_ref,retention_root_ref,rook_root_ref,oracle111_ref,oracle112_ref]
cpsat118, cpsat118_ref = evidence('outputs/stage2-root-cpsat-r118.json')
cpsat119, cpsat119_ref = evidence('projects/18-isa-scheduler/experiments/r119-cpsat-sources/source-provenance.json')
assert cpsat118['passed'] and cpsat118['actual_constructed_outputs'] == 2118
assert cpsat118['comparisons'] == 2240 and cpsat118['matrix_unknown'] == 2
for suite in cpsat118['suites']:
    for relative, expected in suite['evidence'].items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
for relative, expected in cpsat119['source_sha256'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler/experiments/r119-cpsat-sources'/relative).read_bytes()).hexdigest() == expected
for relative, expected in cpsat119['evidence_sha256'].items():
    assert hashlib.sha256((root/'projects/18-isa-scheduler'/relative).read_bytes()).hexdigest() == expected
state['project18']['optional_cpsat'] = dict(status='validated_small_graphs_matrix_unknown',
    comparisons=2240,constructed_outputs=2118,raw_oracle_agreed_backend_infeasible=122,
    root_review=cpsat118_ref,source_snapshot=cpsat119_ref,
    original_matrix_attempts=dict(records=2,budget_ms_each=30000,workers=1,unknown=2,new_outputs=0),
    scope=cpsat118['scope'],next='Input-graph automorphism row/column symmetry elimination, same budget; original internal operations remain freely interleaved. No COPY objective or default change.')
state['project18']['evidence'] += [cpsat118_ref,cpsat119_ref]
symmetry121, symmetry121_ref = evidence('outputs/stage2-root-symmetry-r121.json')
assert symmetry121['passed'] and symmetry121['root_replayed_outputs'] == 18
assert symmetry121['original_matrix_unknown_attempts'] == 4
for relative, expected in symmetry121['evidence'].items():
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
state['project18']['optional_cpsat']['symmetry'] = dict(raw_graphs=24,root_checked_generators=72,
    actual_replayed_outputs=18,tamper_rejections=24,original_matrix_paired_attempts=4,
    original_matrix_unknown=4,new_original_matrix_outputs=0,
    scope='Verified resourcegraph row/column birth sorting only, no atomic output cells or fixed internal k order. Same30s/1worker old/new pair remainsUNKNOWN; no quality or causal speed result.')
state['project18']['optional_cpsat']['next'] = 'Return to actual sharedDAG COPY gap from audited lowerbounds; retain all existing legal incumbents and failures. No repeated higher matrix budget.'
state['project18']['evidence'].append(symmetry121_ref)

default44, default44_ref = evidence('outputs/stage2-root-default-r44.json')
final44, final44_ref = evidence('projects/27-aicore-streams/reports/final-checkpoint-batch44.json')
cost44, cost44_ref = evidence('outputs/stage2-root-resource-pairs-r44.json')
heap44, heap44_ref = evidence('outputs/stage2-root-heap-numeric-gold-r44.json')
assert default44['passed'] and default44['normal_records'] == 979 and default44['ctest'] == 11
assert cost44['passed'] and heap44['passed'] and heap44['total'] == 523
assert final44['status'] == 'validated_recovery_default_milestone'
assert final44['hard_legal'] == 141 and final44['known_witness_unresolved'] == 61
for relative, expected in default44['evidence'].items():
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
for relative, expected in cost44['evidence'].items():
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
state['project27']['historical_r43'] = dict(source_sha256=resource43['source_sha256'],binary_sha256=resource43['default_exe_sha256'],paired_resource_cost=state['project27']['paired_resource_cost'])
state['project27']['shallow_recovery_candidate'].update(status='validated_default_r44',scope='Final default validated after full functional/numeric/profile and paired-cost review; preliminary2 serial outputs remain historical, distinct from final8-stream recovered plans.')
state['project27'].update(
    current='R44 is default: input-only shared-producer affinity and bounded consumer insertion recovery, used only after older candidates fail. Hard202 legal139 to141; new72 legal68 to72; structure36 alllegal. All243 common passing outputs retain exact T/peak. Root independently validates all249 actual plans with arbitrary-precision heap simulation,523 numeric controls, and all979 normal before/after records.11/11 CTest;144 optimum audits/33 certificates.61 known witness-feasible hard cases remain unresolved.',
    source_sha256=final44['source_sha256'],binary_sha256=final44['default_exe_sha256'],
    hard202=dict(legal=141,unresolved=61),heldout72=dict(legal=72,recovered=4),
    paired_resource_cost=dict(hard202=cost44['groups']['hard'],heldout72=cost44['groups']['heldout'],
                             scope='All failures included in3 isolated alternating full pairs with same Release build flags. Measured8d43 Release and default7861 are separately frozen; early997f O2 functional executable is not the measured binary.',
                             interpretation=cost44['interpretation']),
    limitation='Quality recovery has cost: hard202 median within-pair CPU+9.19percent, ratio of separate-side medians+4.49percent.61 known feasible unresolved, no universal feasibility/optimality guarantee, official score, real NPU validation or global RAM reduction. No time improvement inferred from concurrent functional tests.')
state['project27']['evidence'] += [functional44_root_ref,default44_ref,final44_ref,cost44_ref,heap44_ref]
projection45, projection45_ref = evidence('outputs/stage2-root-projection-r45.json')
assert projection45['passed'] and projection45['recovered_records'] == 2
for relative, expected in projection45['evidence'].items():
    assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
state['project27']['ancestor_projection_candidate'] = dict(
    status='isolated_preliminary_not_default',input_only_unresolved=61,applicable=35,
    recovered_records=2,recovered_topologies=1,root_independent_replays=projection45['recovered'],
    evidence=projection45_ref,scope=projection45['scope'],
    pending='Complete numerical/profile contract, unseen retention holdout, full failed-only integration/regression and isolated resource-cost comparison. DefaultR44 remains141/202; do not report143 default outputs from preliminary diagnostic plans.')
state['project27']['evidence'].append(projection45_ref)
functional45, functional45_ref = evidence('outputs/stage2-root-functional-plans-r45.json')
assert functional45['passed'] and functional45['independently_validated'] == 185
for suite in functional45['suites']:
    assert suite['lost'] == 0 and suite['common_T_peak_identical']
    for relative, expected in suite['evidence'].items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
state['project27']['ancestor_projection_candidate'].update(
    status='full_functional_candidate_not_default',full_hard202=dict(legal=143,remaining_unknown=59),
    fresh_retention48=dict(before_legal=42,after_legal=42,remaining_unknown=6,recovered=0),
    full_functional_root_review=functional45_ref,
    pending='Complete sanitizer/numerical profile contract, full normal/new72/structure36 regression and isolated resource-cost comparison. Actual defaultR44 remains141/202. Fresh48 zero recovery retained as negative result.')
state['project27']['evidence'].append(functional45_ref)
negative47, negative47_ref = evidence('projects/27-aicore-streams/research/batch47/functional-checkpoint.json')
negative47_hard, negative47_hard_ref = evidence('projects/27-aicore-streams/reports/projection-unresolved-diagnostic-batch47.json')
negative47_heldout, negative47_heldout_ref = evidence('projects/27-aicore-streams/reports/projection-heldout-unresolved-diagnostic-batch47.json')
assert len(negative47_hard['cases']) == 61 and sum(r['pass'] for r in negative47_hard['cases']) == 0
assert len(negative47_heldout['cases']) == 6 and sum(r['pass'] for r in negative47_heldout['cases']) == 0
assert all(r['actual_exit_code'] == 0 for r in negative47['statuses'])
state['project27']['rejected_ready_affinity_r47'] = dict(
    status='negative_not_promoted',old61_recovered=0,new6_recovered=0,
    previous_r45_old61_recovered=2,limitation='Changing only dependency-ready seeds loses both R45 recoveries. No default change; profile correctness does not make this an optimization. R46 coverage expansion likewise produced no additional recovery.',
    evidence=[negative47_ref,negative47_hard_ref,negative47_heldout_ref])
state['project27']['evidence'] += [negative47_ref,negative47_hard_ref,negative47_heldout_ref]

avx_review, avx_review_ref = evidence('outputs/stage2-root-avx512-review.json')
avx_final, avx_final_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-avx512/final-manifest.json')
avx_snapshot, avx_snapshot_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-avx512/candidate-source/snapshot-manifest.json')
assert avx_review['passed'] and avx_review['actual_small_output_files'] == 240
assert avx_review['performance_records'] == 60 and avx_review['negative_pairs'] == 11
for relative, expected in avx_snapshot['files'].items():
    frozen = root/'projects/19-dynamic-graph/artifacts/stage2-avx512/candidate-source'/relative
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == expected
for relative, expected in avx_review['evidence'].items():
    assert hashlib.sha256((root/'projects/19-dynamic-graph/artifacts/stage2-avx512'/relative).read_bytes()).hexdigest() == expected
for relative, expected in [('build/cholesky_runtime.exe',avx_final['ordinary_sha256']),('artifacts/stage2-avx512/candidate/runtime.exe',avx_final['candidate_runtime_sha256'])]:
    assert hashlib.sha256((root/'projects/19-dynamic-graph'/relative).read_bytes()).hexdigest() == expected
state['project19']['avx512_candidate'].update(status='validated_optional_not_promoted',
    root_small_output_files=240,native_guard_page_cases=1400,ieee754_goldens=16,ctest=9,
    performance_records=60,negative_pairs=11,paired_summaries=avx_review['summaries'],
    source_snapshot=avx_snapshot_ref,candidate_exe_sha256=avx_final['candidate_runtime_sha256'],
    scope=avx_review['scope'],interpretation=avx_review['interpretation'])
state['project19']['avx512_candidate']['evidence'] += [avx_review_ref,avx_final_ref,avx_snapshot_ref]
state['project19']['evidence'] += [avx_review_ref,avx_final_ref,avx_snapshot_ref]
vm_phase1, vm_phase1_ref = evidence('outputs/stage2-root-prepared-vm-phase1.json')
assert vm_phase1['passed'] and vm_phase1['actual_output_files'] == 172
assert vm_phase1['root_rerun_native_contract']['comparisons'] == 404
for relative, expected in vm_phase1['evidence'].items():
    assert hashlib.sha256((root/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1'/relative).read_bytes()).hexdigest() == expected
state['project19']['prepared_vm_phase1'] = dict(status='validated_functional_optional_not_default',
    candidate_exe_sha256=vm_phase1['candidate_exe_sha256'],whole_file_C_comparisons=172,
    required_VM_sources=9,source_files=103,native_opcodes=33,native_comparisons=404,
    original_error_contracts=7,ctest=9,root_review=vm_phase1_ref,
    scope=vm_phase1['scope'],performance='Not measured. Legacy/native/default4f73 unchanged; preparation per matrix is within compute and plan bytes separately accounted. No TOS/threaded dispatch/fusion/cache.')
state['project19']['evidence'].append(vm_phase1_ref)
vm_fp, vm_fp_ref = evidence('outputs/stage2-root-vm-fp.json')
vm_measure, vm_measure_ref = evidence('outputs/stage2-root-vm-measurements.json')
vm_final, vm_final_ref = evidence('projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1/final-manifest.json')
assert vm_fp['passed'] and vm_fp['independent_constant_bit_checks'] == 10464
assert vm_measure['passed'] and vm_measure['performance_records'] == 90 and vm_measure['negative_pairs'] == 2
for record in (vm_fp,vm_measure):
    for relative, expected in record['evidence'].items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
for relative, expected in vm_final['proof_sha256'].items():
    assert hashlib.sha256((root/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1'/relative).read_bytes()).hexdigest() == expected
for relative, expected in vm_final['final_evidence_source_sha256'].items():
    assert hashlib.sha256((root/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1/final-evidence-source'/relative).read_bytes()).hexdigest() == expected
state['project19']['prepared_vm_phase1'].update(status='validated_measured_optional_not_default',
    whole_file_C_comparisons=180,fp_independent_bit_checks=10464,
    maximum_shape=dict(n=10000,full_outputs=4,bytes_each=800000008,peak_working_set_bytes=vm_measure['max_peak_working_set'],
                       original_VM_steps=1700000012,explicit_step_budget=10000000000,
                       limitation='Default1e9 unchanged and insufficient for this1.7b-step copy VM; explicit1e10 resource run is not a default large-N fallback acceptance proof.'),
    performance=dict(trials=90,pairs=45,negative_pairs=2,paired_summaries=vm_measure['summaries'],
                     host_busy_percent_range=vm_measure['host_busy_percent_range'],
                     scope='Same frozen candidate binary, legacy vs decoded;9 genuineVM sources5 pairs. Decode within compute. All45 pairs retained;9 source medians2.36–18.79percent lower,2 individual intarith regressions. Recorded activehost background prevents idle-machine/universal claims.'),
    scope=vm_measure['scope'])
state['project19']['evidence'] += [vm_fp_ref,vm_measure_ref,vm_final_ref]
state['project19']['next_work'] = 'Independent optional phase2 top-two FP64 stack cache, preserving every original opcode step/error/order/FP bit and4096 overflow boundary. No threaded dispatch, fusion, plan cache or default promotion. Phase1 bf54 and ordinary4f73 preserved; new tests/performance require own evidence.'
assert state['project11'] == paused
state['completion'] = 'Not achieved.11 explicitly paused, full correctness unproved.18 global Level1–3 unproved,19 prepared VM optimization underway,27 default still61 known witness-feasible hard cases unresolved. Continue18/19/27.'
path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(updated=path.as_posix(),project11_status=state['project11']['status'],status=state['status']),ensure_ascii=False))
import update_stage2_incremental
update_stage2_incremental.main()
