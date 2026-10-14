"""Static-only source mirror construction; never configure or execute a VM."""
import difflib,hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1]
R=P/'artifacts/stage2-vm-nested-budget/runtime-integration'
W=R/'workspace'
I=R/'initial-plan'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(path,before,after):
    text=path.read_text(encoding='utf-8');assert text.count(before)==1,(path,before[:80]);path.write_text(text.replace(before,after),encoding='utf-8')
def main():
    assert not W.exists()
    assert sha(I/'plan.json')=='32aafc022a3fe8ad375c36bdbccf66823048847c88bc45a3cd18b20abc867253'
    assert sha(R/'contract-supplement/plan.json')=='7aa25cc3a060cffc700aee41799877346d74dc0999a61d33e78b6a172735b5a3'
    initial=json.loads((I/'plan.json').read_text(encoding='utf-8'));W.mkdir()
    for d in ['src','include','tests','tools','fixtures','docs']:
        shutil.copytree(P/d,W/d,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for f in ['CMakeLists.txt','CMakePresets.json','README.md']:shutil.copyfile(P/f,W/f)
    # Restore every accepted baseline file, including exact ABI headers, before editing.
    for rel,entry in initial['frozen_files'].items():
        if not rel.startswith('baseline-source/'):continue
        source=I/rel;assert sha(source)==entry['sha256'];target=W/rel.removeprefix('baseline-source/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    for rel in ['src/vm_nested_step_bound.cpp','include/cholesky/vm_nested_step_bound.hpp','tests/vm_nested_step_bound_tests.cpp']:
        source=I/'nested-source'/rel;assert sha(source)==initial['frozen_files']['nested-source/'+rel]['sha256'];shutil.copyfile(source,W/rel)
    replace(W/'CMakeLists.txt','option(CHOL_PREPARED_VM', '''option(CHOL_NESTED_VM_BUDGET "Experimental nested counted-loop fallback; requires proved policy" OFF)
if(CHOL_NESTED_VM_BUDGET)
  if(NOT CHOL_PROVED_VM_BUDGET)
    message(FATAL_ERROR "CHOL_NESTED_VM_BUDGET requires CHOL_PROVED_VM_BUDGET")
  endif()
  target_sources(cholesky_core PRIVATE src/vm_nested_step_bound.cpp)
  target_compile_definitions(cholesky_core PUBLIC CHOL_NESTED_VM_BUDGET=1)
endif()
option(CHOL_PREPARED_VM''')
    replace(W/'CMakeLists.txt','if(BUILD_TESTING)\n', '''if(BUILD_TESTING)
  if(CHOL_NESTED_VM_BUDGET)
    add_executable(vm_nested_step_bound_tests tests/vm_nested_step_bound_tests.cpp)
    target_link_libraries(vm_nested_step_bound_tests PRIVATE cholesky_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
      target_compile_options(vm_nested_step_bound_tests PRIVATE -fno-fast-math -ffp-contract=off)
    endif()
    add_test(NAME nested_program_step_bound COMMAND vm_nested_step_bound_tests)
  endif()
  add_executable(vm_nested_budget_selection_tests tests/vm_nested_budget_selection_tests.cpp)
  target_link_libraries(vm_nested_budget_selection_tests PRIVATE cholesky_core)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(vm_nested_budget_selection_tests PRIVATE -fno-fast-math -ffp-contract=off)
  endif()
  add_test(NAME nested_vm_budget_selection COMMAND vm_nested_budget_selection_tests)
''')
    replace(W/'include/cholesky/runtime.hpp','  double vm_budget_proof_ms=0;', '''  double vm_budget_proof_ms=0;
  // Isolated nested integration ABI: all core and caller objects rebuild together.
  std::string vm_budget_first_status,vm_budget_first_reason,vm_budget_nested_status,vm_budget_nested_reason,vm_budget_selected_stage;
  std::uint64_t vm_budget_first_bound=0,vm_budget_first_work=0,vm_budget_nested_bound=0,vm_budget_nested_work=0;
  double vm_budget_first_ms=0,vm_budget_nested_ms=0;''')
    replace(W/'src/runtime.cpp','#ifdef CHOL_HAVE_THREADED_DISPATCH\n#include "cholesky/threaded_vm.hpp"', '''#ifdef CHOL_NESTED_VM_BUDGET
#include "cholesky/vm_nested_step_bound.hpp"
#endif
#ifdef CHOL_HAVE_THREADED_DISPATCH
#include "cholesky/threaded_vm.hpp"''')
    before='''    const auto proof_start=std::chrono::steady_clock::now();
    const auto proof=prove_vm_step_bound(metadata,input.n,options.block_size);
    if(proof.proved)options.vm_step_limit=std::max(options.vm_step_limit,proof.bound);
    if(options.metrics) {
      options.metrics->vm_budget_proof_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-proof_start).count();
      options.metrics->vm_budget_proof_status=proof.proved?"proved":"unknown";
      options.metrics->vm_budget_proof_reason=proof.reason;
      options.metrics->vm_budget_bound=proof.bound;
      options.metrics->vm_budget_work=proof.work;
      options.metrics->vm_effective_step_limit=options.vm_step_limit;
    }'''
    after='''    using ProofClock=std::chrono::steady_clock;
    constexpr std::uint64_t work_limit=250000;
    const auto proof_start=ProofClock::now();
    const auto first=prove_vm_step_bound(metadata,input.n,options.block_size);
    const double first_ms=std::chrono::duration<double,std::milli>(ProofClock::now()-proof_start).count();
    auto selected=first;
    std::uint64_t total_work=first.work;
    const char* selected_stage=first.proved?"first":"none";
    const char* nested_status="feature-disabled";
    StepBoundProof nested{false,0,0,0,"not-called"};
    double nested_ms=0;
    // A component invariant violation fails closed, never replacing a VM error.
    if(first.work>work_limit) {
      selected={false,0,0,0,"analysis-contract"};total_work=std::min(first.work,work_limit);selected_stage="none";nested_status="contract-skip";
    } else if(first.proved)nested_status="first-proved-skip";
    else {
#ifdef CHOL_NESTED_VM_BUDGET
      // A work-limit reason alone does not imply zero remaining work.
      const auto remaining=work_limit-first.work;
      if(!remaining)nested_status="work-exhausted-skip";
      else {
        const auto nested_start=ProofClock::now();
        nested=prove_vm_nested_step_bound(metadata,input.n,options.block_size,remaining);
        nested_ms=std::chrono::duration<double,std::milli>(ProofClock::now()-nested_start).count();
        if(nested.work>remaining) {
          nested={false,0,0,0,"analysis-contract"};nested_status="unknown";
        } else {
          total_work+=nested.work; // <=first.work+remaining, checked before addition.
          nested_status=nested.proved?"proved":"unknown";
          if(nested.proved){selected=nested;selected_stage="nested";}
        }
      }
#endif
    }
    if(selected.proved)options.vm_step_limit=std::max(options.vm_step_limit,selected.bound);
    if(options.metrics) {
      auto& metric=*options.metrics;
      metric.vm_budget_first_status=first.proved?"proved":"unknown";
      metric.vm_budget_first_reason=first.reason;metric.vm_budget_first_bound=first.bound;metric.vm_budget_first_work=first.work;metric.vm_budget_first_ms=first_ms;
      metric.vm_budget_nested_status=nested_status;metric.vm_budget_nested_reason=nested.reason;metric.vm_budget_nested_bound=nested.bound;metric.vm_budget_nested_work=nested.work;metric.vm_budget_nested_ms=nested_ms;
      metric.vm_budget_selected_stage=selected_stage;
      metric.vm_budget_proof_status=selected.proved?"proved":"unknown";
      metric.vm_budget_proof_reason=selected.reason;
      metric.vm_budget_bound=selected.bound;metric.vm_budget_work=total_work;
      metric.vm_effective_step_limit=options.vm_step_limit;
      metric.vm_budget_proof_ms=std::chrono::duration<double,std::milli>(ProofClock::now()-proof_start).count();
    }'''
    replace(W/'src/runtime.cpp',before,after)
    replace(W/'src/main.cpp','    unsigned input_buffers_reused=0;', '''    double vm_budget_first_ms=0,vm_budget_nested_ms=0;
    std::uint64_t vm_budget_first_work=0,vm_budget_nested_work=0,vm_budget_first_bound_peak=0,vm_budget_nested_bound_peak=0;
    unsigned vm_budget_first_proved_matrices=0,vm_budget_first_unknown_matrices=0,vm_budget_nested_attempted_matrices=0,vm_budget_nested_proved_matrices=0,vm_budget_nested_unknown_matrices=0,vm_budget_nested_work_exhausted_skips=0;
    std::string vm_budget_first_reason_last,vm_budget_nested_reason_last,vm_budget_selected_stage_last;
    unsigned input_buffers_reused=0;''')
    replace(W/'src/main.cpp','      engine = metrics.engine;', '''      vm_budget_first_ms+=metrics.vm_budget_first_ms;vm_budget_nested_ms+=metrics.vm_budget_nested_ms;
      vm_budget_first_work+=metrics.vm_budget_first_work;vm_budget_nested_work+=metrics.vm_budget_nested_work;
      vm_budget_first_bound_peak=std::max(vm_budget_first_bound_peak,metrics.vm_budget_first_bound);vm_budget_nested_bound_peak=std::max(vm_budget_nested_bound_peak,metrics.vm_budget_nested_bound);
      vm_budget_first_proved_matrices+=metrics.vm_budget_first_status=="proved";vm_budget_first_unknown_matrices+=metrics.vm_budget_first_status=="unknown";
      vm_budget_nested_proved_matrices+=metrics.vm_budget_nested_status=="proved";vm_budget_nested_unknown_matrices+=metrics.vm_budget_nested_status=="unknown";
      vm_budget_nested_attempted_matrices+=metrics.vm_budget_nested_status=="proved"||metrics.vm_budget_nested_status=="unknown";
      vm_budget_nested_work_exhausted_skips+=metrics.vm_budget_nested_status=="work-exhausted-skip";
      vm_budget_first_reason_last=metrics.vm_budget_first_reason;vm_budget_nested_reason_last=metrics.vm_budget_nested_reason;vm_budget_selected_stage_last=metrics.vm_budget_selected_stage;
      engine = metrics.engine;''')
    needle='      << ",\\\"resident_task_states_peak\\\":" << resident_task_states'
    extra='''      << ",\\\"vm_budget_first_ms\\\":" << vm_budget_first_ms << ",\\\"vm_budget_nested_ms\\\":" << vm_budget_nested_ms
      << ",\\\"vm_budget_first_work\\\":" << vm_budget_first_work << ",\\\"vm_budget_nested_work\\\":" << vm_budget_nested_work
      << ",\\\"vm_budget_first_bound_peak\\\":" << vm_budget_first_bound_peak << ",\\\"vm_budget_nested_bound_peak\\\":" << vm_budget_nested_bound_peak
      << ",\\\"vm_budget_first_proved_matrices\\\":" << vm_budget_first_proved_matrices << ",\\\"vm_budget_first_unknown_matrices\\\":" << vm_budget_first_unknown_matrices
      << ",\\\"vm_budget_nested_attempted_matrices\\\":" << vm_budget_nested_attempted_matrices << ",\\\"vm_budget_nested_proved_matrices\\\":" << vm_budget_nested_proved_matrices << ",\\\"vm_budget_nested_unknown_matrices\\\":" << vm_budget_nested_unknown_matrices
      << ",\\\"vm_budget_nested_work_exhausted_skips\\\":" << vm_budget_nested_work_exhausted_skips
      << ",\\\"vm_budget_first_reason_last\\\":\\\"" << vm_budget_first_reason_last << "\\\",\\\"vm_budget_nested_reason_last\\\":\\\"" << vm_budget_nested_reason_last << "\\\",\\\"vm_budget_selected_stage_last\\\":\\\"" << vm_budget_selected_stage_last << "\\\""
'''
    replace(W/'src/main.cpp',needle,extra+needle)
    # No implementation freeze until selection and runners have been written.
    changes={}
    for rel in ['CMakeLists.txt','include/cholesky/runtime.hpp','src/runtime.cpp','src/main.cpp']:
        baseline=I/'baseline-source'/rel;changes[rel]={'before_sha256':sha(baseline),'after_sha256':sha(W/rel)}
        target=R/'implementation-work'/(rel.replace('/','__')+'.diff');target.parent.mkdir(exist_ok=True);target.write_text(''.join(difflib.unified_diff(baseline.read_text(encoding='utf-8').splitlines(True),(W/rel).read_text(encoding='utf-8').splitlines(True),fromfile='baseline/'+rel,tofile='workspace/'+rel)),encoding='utf-8')
    assert sha(P/'src/vm_step_bound.cpp')==initial['source_scope']['original_vm_step_bound_cpp_SHA_unchanged']
    assert sha(P/'build/cholesky_runtime.exe')==initial['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==initial['memory_sha256']
    (R/'implementation-work/mirror-changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
    print(json.dumps({'static_source_mirror_written':True,'changes':changes,'compile_or_VM_started':False}))
if __name__=='__main__':main()
