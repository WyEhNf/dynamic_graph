"""Static immutable component plan; never invokes compiler, C, or VM."""
import hashlib,json,shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
WORK=STAGE/'component-work'
OUT=STAGE/'initial-freeze'
ACCEPT=P/'artifacts/stage2-vm-proved-budget/runtime-integration/acceptance'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    accepted=read(ACCEPT/'manifest.json');assert accepted['passed'];OUT.mkdir(exist_ok=False)
    assert sha(P/'src/vm_step_bound.cpp')==accepted['source_sha256']['src/vm_step_bound.cpp']=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    ordinary=P/'build/cholesky_runtime.exe';memory=P/'build-memory/cholesky_runtime.exe'
    assert sha(ordinary)==accepted['ordinary_sha256'] and sha(memory)==accepted['memory_sha256']
    frozen={}
    def copy(source,relative,expected=None):
        if expected:assert sha(source)==expected
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        frozen[relative.as_posix()]={'sha256':sha(target),'origin':str(source),'bytes':target.stat().st_size}
    for source in sorted((ACCEPT/'source').rglob('*')):
        if source.is_file():copy(source,Path('dependencies/accepted-source')/source.relative_to(ACCEPT/'source'),accepted['source_sha256'][source.relative_to(ACCEPT/'source').as_posix()])
    copy(ACCEPT/'gnu/libcholesky_core.a',Path('dependencies/libcholesky_core.a'),accepted['binaries']['gnu']['libcholesky_core.a']['sha256'])
    for source in sorted((ACCEPT/'gnu/build-provenance').rglob('*')):
        if source.is_file():copy(source,Path('dependencies/build-provenance')/source.relative_to(ACCEPT/'gnu/build-provenance'))
    for source in sorted((WORK/'source').rglob('*')):
        if source.is_file():copy(source,Path('candidate-source')/source.relative_to(WORK/'source'))
    for source in [Path(__file__),P/'docs/stage2-vm-nested-budget-design.md']:
        copy(source,Path('plan-source')/source.relative_to(P))
    copy(ACCEPT/'manifest.json',Path('dependencies/acceptance-manifest.json'))
    old=P/'artifacts/stage2-vm-proved-budget/component-acceptance/manifest.json'
    supplement=P/'artifacts/stage2-vm-proved-budget/component-dependency-supplement/manifest.json'
    copy(old,Path('historical-component-manifest.json'));copy(supplement,Path('historical-ABI-supplement-manifest.json'))
    compiler=Path('E:/mingw64/bin/g++.exe');cpp=OUT/'candidate-source/src/vm_nested_step_bound.cpp';test=OUT/'candidate-source/tests/vm_nested_step_bound_tests.cpp';exe=STAGE/'component-gate/vm-nested-bound-tests.exe'
    flags=['-std=gnu++20','-O2','-g','-Wall','-Wextra','-Wpedantic','-fno-fast-math','-ffp-contract=off','-DCHOL_HAVE_THREADED_DISPATCH=1','-DCHOL_PREPARED_VM=1','-DCHOL_THREADED_VM=1','-DCHOL_PROVED_VM_BUDGET=1']
    command=[str(compiler),*flags,'-I',str(OUT/'candidate-source/include'),'-I',str(OUT/'dependencies/accepted-source/include'),str(cpp),str(test),str(OUT/'dependencies/libcholesky_core.a'),'-o',str(exe)]
    plan={'schema':'isolated-nested-VM-bound-component-plan-v1','status':'predeclared only; no compile/C/VM execution','passed_static_freeze':True,'design_sha256':sha(P/'docs/stage2-vm-nested-budget-design.md'),'acceptance_manifest_sha256':sha(ACCEPT/'manifest.json'),'frozen_files':frozen,'compiler':{'path':str(compiler),'sha256':sha(compiler),'version_lineage':'accepted GNU15.2 frozen CMake/provenance; version not executed in prepare'},'compile_command':command,'compile_flags':flags,'compiler_runtime_search_directory':'E:/mingw64/bin','future_compile_environment':{key:str(STAGE/'compiler-temp')for key in ['TEMP','TMP','TMPDIR']},'minimum_launch_RAM_bytes':268435456,'minimum_F_free_bytes':268435456,'compile_started':False,'C_execution_started':False,'original_VM_execution_started':False,'maximum_shape_execution_started':False,'performance_started':False,'runtime_integrated':False,'current_core_source_modified':False,'component_API':'chol::prove_vm_nested_step_bound(Metadata, N, block, work=250000) -> existing StepBoundProof; distinct symbol from frozen first component','ABI':{'runtime_header_sha256':accepted['source_sha256']['include/cholesky/runtime.hpp'],'library_sha256':accepted['binaries']['gnu']['libcholesky_core.a']['sha256'],'header_and_library_both_from_same_f5_acceptance':True,'do_not_link_new_header_to476ad_old_ABI':True,'old_component07481_and09f31_retained':True},'algorithm':{'full_conservative_reachable_CFG':True,'dominator_matrix_before_loop_discovery':True,'natural_reverse_predecessor_nodes_and_single_entry':True,'strict_subset_forest_no_shared_or_irreducible_cycles':True,'canonical_positive_int32_increasing_Lt_Jz_single_latch':True,'all_cycles_checked_after_verified_latch_removal':True,'recursive_leaf_child_weight_and_all_exit_edges':True,'parent_range_max_child_trips':True,'child_entry_requires_initialized_every_invocation':True,'all_loop_writes_killed_before_body_and_exit':True,'child_cannot_write_parent_iv_or_guard_invariants':True,'entry_exit_stack_and_merge_checked':True,'integer_intervals_with_exact_FP64_representability':True,'checked_uint64_bound_below_max':True,'work_limit':250000,'recursion_depth_limit':64,'all_dominator_matrix_allocation_charged_before_allocation':True,'large_or_ambiguous_PROGRAM_returns_unknown':True,'guards_not_added':['descending','inclusive','nonconstant increment','data-dependent monotonic certificate'],'source_or_hash_detection':False,'cache_dispatch_or_default_change':False},'golden_plan':{'original_VM':'same accepted core execute engine=vm backend=legacy budget fixed; actual metrics.vm_steps; small N3 matrix9 values only','independent_oracle':'direct integer iteration instruction enumeration plus independently formulated conservative maximum; no candidate computation used as gold','rectangular_goldens':576,'triangular_goldens':217,'three_level_goldens':288,'expected_total_counted_goldens':1081,'boundary_contracts':2162,'early_or_pre_error_groups':4,'zero_and_one_and_odd_trip_cases':True,'actual_data_values':[0,1],'untaken_bad_immediate':True,'targeted_unknown_groups':['child retained or uninitialized state','fractional/nonfinite init','child writes parent iv or bound','partial or bypass latch','side entry','zero/negative/fractional step','unsupported inclusive guard','stack mismatch or underflow','int32 final-update overflow','uint64 nested cost overflow','irreducible cycle','exhausted work'],'work_exhaustion_trials':200,'two_mutation_seed_PROGRAMs':'2-level rectangular and parent-dependent triangular complete30-op PROGRAMs','mutation_opcode_variants':34,'mutation_immediates':['-1','0','1','2','3','7','NaN','Infinity'],'planned_single_position_mutations':16320,'proved_mutation_VM_data_cases':2,'mutation_VM_explicit_budget':20000,'every_returned_bound_must_cover_original_pre_error_steps':True,'no_true_C_oracle_claim':True,'no_large_N_execution':True},'future_gate_sequence':['root static audit and explicit component compile authorization','single GNU compile from frozen sources/headers/library into independent component-gate','original_VM small gold/targeted unknown/single-position mutations once; preserve failure and actual tool handles','source/EXE/raw/contract freeze and root independent replay','Runtime integration or N10000 only separate later scope'],'estimated_cost_not_measurement':{'static_source_bytes':'under100KB candidate; dependencies reuse existing accepted artifact','compile_seconds_range':[3,20],'small_contract_seconds_range':[5,60],'N3_VM_matrix_bytes_each':72,'disk_required_gate_bytes':268435456},'ordinary_sha256':sha(ordinary),'memory_sha256':sha(memory),'ordinary_default':'fixed1e9; proof OFF; no promotion','primary_refs':['https://llvm.org/docs/LoopTerminology.html','https://llvm.org/doxygen/classllvm_1_1ScalarEvolution.html']}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':True,'schema':plan['schema'],'plan_sha256':sha(OUT/'plan.json'),'frozen_files':len(frozen),'candidate_CPP_sha256':sha(cpp),'candidate_test_sha256':sha(test),'library_sha256':plan['ABI']['library_sha256'],'no_compile_or_VM_execution':True}))

if __name__=='__main__':main()
