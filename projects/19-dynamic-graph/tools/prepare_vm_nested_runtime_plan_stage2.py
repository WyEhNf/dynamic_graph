"""Freeze only a proposed optional nested Runtime integration and actual-C inputs."""
import hashlib,json,shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
OUT=STAGE/'runtime-integration/initial-plan'
COMPONENT=STAGE/'component-acceptance'
ACCEPT=P/'artifacts/stage2-vm-proved-budget/runtime-integration/acceptance'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    assert not OUT.exists();component=read(COMPONENT/'manifest.json');accepted=read(ACCEPT/'manifest.json')
    assert component['passed'] and sha(COMPONENT/'manifest.json')=='bfdc335f1f47190ccc6ada6d2e709cb056455066d4909901a40aab68174fcf70'
    old_report=P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json';old=read(old_report)
    assert old['passed'] and len(old['runs'])==469 and len(old['failures'])==7 and len(old['cli'])==9
    assert sha(P/'src/vm_step_bound.cpp')=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    assert sha(P/'build/cholesky_runtime.exe')==accepted['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==accepted['memory_sha256']
    OUT.mkdir(parents=True,exist_ok=False);files={}
    def copy(source,relative,expected=None):
        if expected:assert sha(source)==expected
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);files[relative.as_posix()]={'sha256':sha(target),'origin':str(source),'bytes':target.stat().st_size}
    # Original current ABI/runtime and all native/frontend/compiler-facing sources.
    for source in sorted((ACCEPT/'source').rglob('*')):
        if source.is_file():copy(source,Path('baseline-source')/source.relative_to(ACCEPT/'source'),accepted['source_sha256'][source.relative_to(ACCEPT/'source').as_posix()])
    for relative in ['src/vm_nested_step_bound.cpp','include/cholesky/vm_nested_step_bound.hpp','tests/vm_nested_step_bound_tests.cpp']:
        copy(COMPONENT/'source'/relative,Path('nested-source')/relative)
    for source in [COMPONENT/'manifest.json',ACCEPT/'manifest.json']:
        copy(source,Path('dependency-manifests')/('nested-component.json'if source.parent==COMPONENT else'proved-runtime.json'))
    copy(P/'tools/windows_file_resource_probe_stage2.py',Path('capture-source/tools/windows_file_resource_probe_stage2.py'))
    copy(Path(__file__),Path('plan-source/tools')/Path(__file__).name)
    copy(P/'docs/stage2-vm-nested-budget-design.md',Path('plan-source/docs/stage2-vm-nested-budget-design.md'))
    root_audit=P.parents[1]/'outputs/stage2-root-vm-nested-component.json'
    assert read(root_audit)['passed'];copy(root_audit,Path('dependency-manifests/root-component-review.json'))
    fresh={
      'nested-rect-strides':('nested_rect','required nested proof; generic VM', '''int nested_rect(double *a,double *l,int n){
  for(int i=1;i<n;i+=2){
    for(int j=0;j<n;j+=3){l[i*n+j]=a[i*n+j]*0.5-0.0;}
  }
  return 0;
}
'''),
      'nested-triangular':('nested_triangle','required nested proof; parent-dependent range; generic VM', '''int nested_triangle(double *a,double *l,int n){
  for(int i=0;i<n;i++){
    for(int j=0;j<i;j++){l[i*n+j]=a[i*n+j]*0.75;}
  }
  return 0;
}
'''),
      'nested-gram-three':('nested_gram','required nested proof; three-level matrix accumulation; generic VM', '''int nested_gram(double *a,double *l,int n){
  for(int i=0;i<n;i++){
    for(int j=0;j<n;j++){
      double sum=0.0;
      for(int k=0;k<n;k++){sum=sum+a[i*n+k]*a[j*n+k];}
      l[i*n+j]=sum;
    }
  }
  return 0;
}
'''),
      'strict-cholesky-control':('nested_cholesky','native AUTO bypass; forced-VM functional status recorded, no timing claim', '''/* Self-built strict source, not official competition C. */
#include <math.h>
int nested_cholesky(const double *a,double *l,int n){
  for(int i=0;i<n;i++){
    for(int j=0;j<i+1;j++){
      double sum=0.0;
      for(int k=0;k<j;k++){sum+=l[i*n+k]*l[j*n+k];}
      if(i==j)l[i*n+j]=sqrt(a[i*n+i]-sum);
      else l[i*n+j]=(a[i*n+j]-sum)/l[j*n+j];
    }
  }
  return 0;
}
'''),
      'unknown-data-step':('nested_data_step','required unknown; nonconstant induction step; defined finite C', '''int nested_data_step(double *a,double *l,int n){
  int increment=a[0]>0.0?1:2;
  for(int i=0;i<n;i+=increment){
    for(int j=0;j<n;j++){l[i*n+j]=a[i*n+j];}
  }
  return 0;
}
'''),
      'unknown-parent-bound-write':('nested_changed_bound','required unknown; parent guard invariant written; defined finite C', '''int nested_changed_bound(double *a,double *l,int n){
  int limit=n;
  for(int i=0;i<limit;i++){
    limit=n-i;
    for(int j=0;j<n;j++){l[i*n+j]=a[i*n+j]*0.25;}
  }
  return 0;
}
''')}
    sources=[]
    for label,(function,requirement,text)in fresh.items():
        path=OUT/'fresh-C'/label/'source.c';path.parent.mkdir(parents=True);path.write_text(text,encoding='utf-8');sources.append({'label':label,'function':function,'path':str(path),'sha256':sha(path),'required_behavior':requirement,'sizes':[3,7,13,29,53],'families':['dense-SPD','diagonal-signedzero-SPD'],'whole_C_output_comparisons':14,'source_is_new_or_holdout':True,'AST_IR_or_C_compiled':False})
    # Old oracle executions are not repeated: index every actual source/input/reference.
    inherited=[]
    for row in old['runs']:
        if row['mode']!='fixed-auto':continue
        assert sha(row['metadata'])==row['metadata_sha256'] and sha(row['input'])==row['input_sha256'] and sha(row['reference'])==row['reference_sha256']
        inherited.append({key:row[key]for key in ['source','family','metadata','input','reference','metadata_sha256','input_sha256','reference_sha256','vm_steps','matrices','bytes','sha256']})
    assert len(inherited)==67 and sum(row['matrices']for row in inherited)==566
    source_lineage=[]
    for source in old['sources']:
        folder=Path(source['folder']);hashes={name:sha(folder/name)for name in ['source.c','program.meta','oracle.c','oracle.exe']}
        assert hashes['source.c']==source['source_sha256'] and hashes['program.meta']==source['metadata_sha256'] and hashes['oracle.c']==source['harness_sha256'] and hashes['oracle.exe']==source['oracle_binary_sha256']
        source_lineage.append({'source':source['label'],'folder':str(folder),'files_sha256':hashes})
    builds=[
      {'label':'gnu-nested','source_mirror':'workspace','build':'build-gnu-nested','CHOL_PROVED_VM_BUDGET':True,'CHOL_NESTED_VM_BUDGET':True,'CHOL_THREADED_VM_FORCE_PORTABLE':False},
      {'label':'portable-nested','source_mirror':'workspace','build':'build-portable-nested','CHOL_PROVED_VM_BUDGET':True,'CHOL_NESTED_VM_BUDGET':True,'CHOL_THREADED_VM_FORCE_PORTABLE':True},
      {'label':'proved-only-compat','source_mirror':'workspace','build':'build-proved-only','CHOL_PROVED_VM_BUDGET':True,'CHOL_NESTED_VM_BUDGET':False,'CHOL_THREADED_VM_FORCE_PORTABLE':False},
      {'label':'disabled','source_mirror':'workspace','build':'build-disabled','CHOL_PROVED_VM_BUDGET':False,'CHOL_NESTED_VM_BUDGET':False,'CHOL_THREADED_VM_FORCE_PORTABLE':False}]
    plan={'schema':'optional-nested-VM-runtime-integration-plan-v1','status':'static proposal only; no build/AST/oracle/VM execution','frozen_files':files,'component_manifest_sha256':sha(COMPONENT/'manifest.json'),'root_component_audit_sha256':sha(root_audit),'baseline_acceptance_sha256':sha(ACCEPT/'manifest.json'),'baseline_b9_RUNTIME_sha256':accepted['binaries']['gnu']['cholesky_runtime.exe']['sha256'],'ordinary_sha256':accepted['ordinary_sha256'],'memory_sha256':accepted['memory_sha256'],'source_scope':{'isolated_mirror_only':True,'anticipated_copied_file_changes':['CMakeLists.txt','include/cholesky/runtime.hpp','src/runtime.cpp','src/main.cpp'],'new_files':['src/vm_nested_step_bound.cpp','include/cholesky/vm_nested_step_bound.hpp','tests/vm_nested_step_bound_tests.cpp','tests/vm_nested_budget_selection_tests.cpp'],'original_vm_step_bound_cpp_SHA_unchanged':accepted['source_sha256']['src/vm_step_bound.cpp'],'native_frontend_and_VM_execution_sources_unchanged':True,'mirror_required_directories':['src','include','tests','tools','fixtures','docs'],'mirror_auxiliary_files':['CMakeLists.txt','CMakePresets.json','README.md'],'no_normal_build_install':True},'builds':builds,'build_flags':'same accepted local-mingw cache/preset, strict FP64 and original AUTO/native/SIMD/queue defaults; only new opt-in flag and portable override as listed','new_CMake_flag':{'name':'CHOL_NESTED_VM_BUDGET','default':False,'requires':'CHOL_PROVED_VM_BUDGET=ON; nestedON/provedOFF configuration rejects','no_new_cli_budget_mode':True},'integration_contract':{'native_bypass_position':'after original metadata/input checks, return native before either proof; retain all original native/AUTO/FP behavior','fixed_mode':'no first or nested proof; original explicit/default step limit and errors','proved_mode':'original first proof with unchanged250000 work; if proved use original bound and skip nested entirely; if unknown only then attempt nested with remaining aggregate work; both failed/unknown retain1e9','total_analysis_work_cap':250000,'nested_work_limit':'250000-first.work, checked; if zero skip with work-limit reason','reason_for_shared_work_cap':'preserve a finite per-execution analysis cap instead of silently doubling original worst-case work','bound_selection':'first successful proof bound only; max(original automatic1e9,successful bound); never replace a successful first proof by nested bound','explicit_limit':'all original literal-limit conflicts and validation order unchanged, including literal1e9 and either CLI order','no_PREPROGRAM_execution_or_error':'proof exceptions caught as unknown, untaken errors remain delayed in original VM','unknown':'keeps original execution, cap, steps, PC and exception strings/status; no aliases or source-name heuristics','no_caching':'state belongs only to one execution/shape/block, no reuse ofPROGRAM or old data','metadata':'full original graph/PROGRAM/ordering/dependencies, no new schema or frontend modification'},'proposed_observability':{'existing_fields':'retain original successful first-proof fields and total final status/bound/effective cap; budget_proof_ms and work become total analysis on fallback','additional_fields':['first-proof proved/unknown counts and first-proof time/work','nested attempted/proved/unknown/work-exhausted-skipped counts','nested time/work/bound/reason','selected proof stage none/first/nested'],'compute_includes_all_analysis_decode':True,'raw_per_matrix_failure_metrics_for_selection_contract':True,'fallback_bounds_recorded_even_below1e9':True},'fresh_C_sources':sources,'input_contract':{'generation':'unchanged frozen evaluate_source.make_input deterministic strictly diagonally-dominant symmetric positive definite matrix, or positive diagonal with signed offdiagonal zeros','not_used_as_numeric_oracle':True,'reference':'compile each actual C once GCC stdc11/O2/fno-fast-math/ffp-contract=off, independent executable at block32; full header+FP64 bytes from realC only','frontend':'once unchanged analyze_source per actualC, clang AST plus IR; optimizednone required for3 generic positives and2 unknowns; recognized scalar for strict control','fresh_files_created_in_static_phase':['six C source files only'],'future_source_metadata_input_harness_compiler_binary_reference_all_SHA':True,'N_upper_in_this_gate':53,'FP_accumulation':'ordinary mul/add in original order; no implicitFMA or reference tolerance'},'backend_modes':['fixed-auto GNU','proved-auto GNU','proved-legacy GNU','proved-decoded GNU','proved-tos2 GNU','proved-threaded GNU','proved-auto portable fallback'],'denominators':{'old_C_groups':67,'old_C_sources':15,'old_C_whole_file_comparisons':469,'fresh_C_sources':6,'fresh_C_groups':12,'fresh_C_comparisons':84,'strict_cholesky_forced_VM_extra_comparisons':4,'total_whole_C_comparisons':557,'all_actual_C_sources':21,'old_error_groups':7,'old_error_modes':7,'old_exact_error_checks':49,'old_CLI_cases':9,'new_invalid_CMake_configuration_cases':1,'first_stage_old_proved_auto_matrices':306,'first_stage_old_unknown_auto_matrices':260,'old_proved_auto_total_matrices':566,'fresh_required_generic_nested_proved_auto_matrices':30,'fresh_required_unknown_auto_matrices':20,'fresh_required_native_no_proof_auto_matrices':10,'fresh_total_proved_auto_matrices':60,'first_unknown_fallback_attempts':'<=first-stage unknown; work-exhausted first-stage skips counted, not fabricated successful proof','strict_forced_VM_status':'record actual first/nested/unknown/work reason; functional bytes/errors must match without asserting proof if250k cap exhausted'},'old_actual_C_source_lineage':source_lineage,'old_C_reference_groups':inherited,'old_report_sha256':sha(old_report),'selection_contract_gold':{'first_proved_skips_nested':'single counted loop/direct acyclic or known proof; zero nested time/work/count','first_unknown_nested_proved':'independent two/three natural counted loops; finalB matches component and effective capmax1e9/B','both_unknown':'data-step/parent guard write/shared/sideentry/irreducible/stack/overflow/work exhausted; cap1e9','native_bypass':'recognized strictCholesky denseAUTO and signedzeroAUTO plus explicittiled controls; neither proof runs','fixed_and_explicit':'all existing error/step boundaries exact','backends':['legacy','decoded','decoded-tos2','decoded-threaded GNU','auto GNU','auto portable decoded-fallback'],'original_step_and_error_contracts':['old934 threaded','derived934 proved','prepared404','TOS480/100000payload','old517/6358/832 boundcomponent','new1081/2162/16320/4995 nestedcomponent'],'N10000_analysis_only_bound_can_raise':'complete synthetic nested3..10000 arithmetic gold, no matrix large execution; must report merely proof computation','new_component_unchanged_e417':True},'CTest_scope':{'GNU_full':'all old15 plus nestedcomponent and new selection contract, intended17 tests','portable_small':'all old11 plus same two new, intended13 tests','proved-only_small':'all old11 plus new selection; nested not compiled, intended12 tests','disabled_small':'all old9 plus selection/rejection contract, intended10 tests','full_old405C_and53diagnostics':'unchanged fullGNU tests; if test-count changes from actualCMake definition report explicit discovered count, no omission'},'control_compat_scope':{'nestedOFF_vs_frozen_b9':'all67cachedC groups once auto proved plus7original errors, preserve first-stage counts306/260/566, no cachedC reexecution','wire_min':'reuse exact originalC/frozeninputs schema1/2/3 and min tests included original CTest frontend contract; no promotion of default metadata schema','disabled':'original proved-disabled errors/help and literal override behavior unchanged','UBSan':'separate predeclared compiler build of component+selection+original/derived934 with strictFP and file stdio capture, no timing claim'},'future_steps':['root static review before any source-mirror edits/build/run','isolate copied runtime CMake/API/metrics branches with component source frozen and originalc761 unchanged','four isolated configure/builds,2compiler threads max,F temp, file-stdio capture','contract first, then complete old469+fresh84+strict4 fullC+49errors+9CLI and67proved-only compat','one fullGNU17CTest plus small portable/proved-only/disabled and specified UBSan contracts','final source/flags/binary/raw/metrics/wholeC hashes freeze/root independent audit','N10000 and policy overhead/default assessment remain separate and not authorized here'],'process_environment':{key:str(STAGE/'compiler-temp')for key in ['TEMP','TMP','TMPDIR']},'minimum_launch_RAM_bytes':268435456,'minimum_F_free_bytes':536870912,'capture_layer':'frozen file-stdio resource probe; no undrained PIPE compiler capture','resource_reporting':'actual parent process PeakWS/commit and host counters, compile parent stats not falsely claimed entire process tree','source_oracle_execution_started':False,'runtime_build_started':False,'large_shape_or_performance_started':False,'default_promoted':False}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':True,'plan_sha256':sha(OUT/'plan.json'),'static_frozen_files':len(files),'fresh_C_sources':6,'declared_whole_C':557,'old_exact_errors':49,'CLI':9,'no_build_AST_or_VM_execution':True}))

if __name__=='__main__':main()
