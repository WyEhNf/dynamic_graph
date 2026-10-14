"""Create an isolated source-only opt-in LOAD+LOAD candidate on the owned G root."""
import ast,difflib,json,math,shutil
from pathlib import Path
from benchmark_vm_nested_policy_stage2 import read,sha,write

P=Path(__file__).resolve().parents[1]
ACCEPT=P/'artifacts/stage2-vm-nested-budget/runtime-integration/acceptance'
DESIGN=P/'artifacts/stage2-vm-nested-budget/execution-static-design-v2'
ROOT=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
WORK=ROOT/'workspace'

DISCOVERY=r'''
namespace {
struct LoadPairPlan {
  std::vector<unsigned char> starts;
  std::uint64_t pairs=0;
  bool valid=false;
};
LoadPairPlan discover_load_pairs(const std::vector<DecodedInstruction>& decoded) {
  LoadPairPlan result;
  if(decoded.empty())return result;
  std::vector<unsigned char> entries(decoded.size(),0);entries[0]=1;
  // Full PROGRAM validation is classification, never an execution error.
  // Any unused bad control operand or enum disables fusion for this execution.
  for(std::size_t pc=0;pc<decoded.size();++pc) {
    const auto& op=decoded[pc];
    if(static_cast<unsigned>(op.opcode)>=33)return result;
    if(op.opcode==Opcode::Jump||op.opcode==Opcode::Jz||op.opcode==Opcode::Jnz) {
      if(!op.valid_index||op.index>=decoded.size())return result;
      entries[op.index]=1;
    }
    if((op.opcode==Opcode::Jump||op.opcode==Opcode::Jz||op.opcode==Opcode::Jnz||op.opcode==Opcode::Return)&&pc+1<decoded.size())entries[pc+1]=1;
  }
  result.starts.assign(decoded.size(),0);result.valid=true;
  for(std::size_t pc=0;pc+1<decoded.size();) {
    if(decoded[pc].opcode==Opcode::Load&&decoded[pc+1].opcode==Opcode::Load&&!entries[pc+1]) {
      result.starts[pc]=1;++result.pairs;pc+=2; // Greedy disjoint pairs.
    }else ++pc;
  }
  return result;
}
}
'''

FUSED_LOAD=r'''LLoad: {
  const auto slot=immediate("slot");
  if(!initialized[slot])throw std::runtime_error("read of uninitialized scalar");
  stack.push_back(slots[slot]);
  if(load_pairs.valid&&load_pairs.starts[pc-1]) {
    // Exact old first-LOAD NEXT boundary before touching the second opcode.
    if(stack.size()>4096)throw std::runtime_error("bytecode stack overflow");
    last_pc=pc;
    if(++steps>options.vm_step_limit)throw std::runtime_error("VM instruction limit exceeded");
    instruction=decoded[pc];++pc; // Discovery proved this exact immutable opcode is LOAD.
    const auto second_slot=immediate("slot");
    if(!initialized[second_slot])throw std::runtime_error("read of uninitialized scalar");
    stack.push_back(slots[second_slot]);++executed_pairs;
  }
}NEXT();'''

DRIVER_HEAD=r'''#include "cholesky/runtime.hpp"
#include "cholesky/prepared_vm.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
using O=chol::Opcode;using I=chol::Instruction;
namespace {
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
struct Result {chol::Matrix output{0,{}};chol::RunMetrics metric;std::string error;};
chol::Metadata meta(std::vector<I> code) {
  chol::Metadata m;m.algorithm="ast_vm_v2";m.arithmetic="fp64_source_order_no_implicit_fma";
  m.dependencies="source_control_flow";m.optimized="none";m.slots=3;m.shape_slot=0;m.block_slot=-1;m.program=std::move(code);return m;
}
Result run(const chol::Metadata& m,const char* backend,std::uint64_t limit) {
  Result r;chol::Options o;o.engine="vm";o.simd="portable";o.vm_backend=backend;o.vm_budget_mode="fixed";
  o.vm_step_limit=limit;o.metrics=&r.metric;
  try{r.output=chol::execute({3,{4,0,0,0,9,0,0,0,16}},m,o);}catch(const std::exception& e){r.error=e.what();}return r;
}
std::uint64_t bits(double value){return std::bit_cast<std::uint64_t>(value);}
unsigned comparisons=0,original_groups=0,prefix_cases=0,extra_cases=0;
Result compare(const chol::Metadata& m,std::uint64_t limit) {
  const auto a=run(m,"legacy",limit),b=run(m,"decoded-threaded",limit),c=run(m,"decoded-threaded-load-pair",limit);
  require(a.error==b.error&&a.error==c.error,"error text/status changed");
  require(a.metric.vm_steps==b.metric.vm_steps&&a.metric.vm_steps==c.metric.vm_steps,"original steps changed");
  require(a.metric.vm_last_pc==b.metric.vm_last_pc&&a.metric.vm_last_pc==c.metric.vm_last_pc,"original lastpc changed");
  require(a.output.n==b.output.n&&a.output.n==c.output.n&&a.output.values.size()==b.output.values.size()&&a.output.values.size()==c.output.values.size(),"output shape changed");
  for(std::size_t i=0;i<a.output.values.size();++i)require(bits(a.output.values[i])==bits(b.output.values[i])&&bits(a.output.values[i])==bits(c.output.values[i]),"output IEEE bits changed");
  require(c.metric.vm_budget_work==0&&c.metric.vm_budget_proof_ms==0,"proof must remain fixed/off");
  const auto decoded=chol::decode_vm_program(m);
  require(decoded.size()==m.program.size(),"PROGRAM altered");
  for(std::size_t i=0;i<decoded.size();++i)require(bits(decoded[i].argument)==bits(m.program[i].argument),"decoded argument IEEE payload changed");
  ++comparisons;return c;
}
void group(const char* label,chol::Metadata m,const char* expected,std::set<std::uint64_t> limits) {
  const auto full=compare(m,1000000000);require(full.error==expected,label);++original_groups;
  // Every original instruction prefix, including zero and one past the PROGRAM.
  for(std::uint64_t i=0;i<=m.program.size()+1;++i)limits.insert(i);
  limits.erase(1000000000);
  for(auto limit:limits){(void)compare(m,limit);++prefix_cases;}
}
void number(double left,double right,std::vector<I> operation,std::uint64_t expected) {
  std::vector<I> p{{O::Const,left},{O::Store,1},{O::Const,right},{O::Store,2},{O::Const,0},{O::Load,1},{O::Load,2}};
  p.insert(p.end(),operation.begin(),operation.end());p.insert(p.end(),{{O::Write,1},{O::Const,0},{O::Return,0}});
  const auto r=compare(meta(p),1000000000);require(r.error.empty()&&bits(r.output.values[0])==expected,"independent numeric bit gold failed");++extra_cases;
  for(std::uint64_t limit=0;limit<=p.size()+1;++limit){(void)compare(meta(p),limit);++extra_cases;}
}
}
int main(){try {
'''

DRIVER_TAIL=r'''
  number(1.0,-0.0,{{O::Mul,0}},UINT64_C(0x8000000000000000));
  number(-0.0,0x1p-1074,{{O::Sub,0}},UINT64_C(0x8000000000000001));
  number(1+0x1p-27,1-0x1p-27,{{O::Mul,0},{O::Const,-1},{O::Add,0}},0);
  number(1+0x1p-27,1-0x1p-27,{{O::Const,-1},{O::Fma,0}},UINT64_C(0xbc90000000000000));
  number(std::bit_cast<double>(UINT64_C(0x7ff8000000001234)),3,{{O::Min,0}},UINT64_C(0x4008000000000000));
  // Greedy disjoint four-LOAD chain and fully unused invalid CFGs.
  auto chain=meta({{O::Const,1},{O::Store,1},{O::Const,2},{O::Store,2},
                   {O::Load,1},{O::Load,2},{O::Load,1},{O::Load,2},
                   {O::Pop,0},{O::Pop,0},{O::Pop,0},{O::Pop,0},{O::Const,0},{O::Return,0}});
  auto result=compare(chain,1000000000);require(result.error.empty(),"chain failed");
#ifdef CHOL_HAVE_THREADED_DISPATCH
  require(result.metric.vm_fusion_pairs_discovered==2&&result.metric.vm_fusion_pairs_executed==2,"overlap/chain plan differs");
#endif
  ++extra_cases;
  for(I bad:std::vector<I>{{O::Jump,std::numeric_limits<double>::quiet_NaN()},{O::Jump,99999},{static_cast<O>(999),0}}) {
    auto unused=chain;unused.program.push_back(bad);result=compare(unused,1000000000);
    require(result.error.empty()&&result.metric.vm_fusion_pairs_executed==0,"unused invalid CFG not full-package fallback");
#ifdef CHOL_HAVE_THREADED_DISPATCH
    require(result.metric.vm_fusion_status=="invalid-cfg-fallback","invalid CFG status differs");
#endif
    ++extra_cases;
  }
  for(unsigned depth=0;depth<=2;++depth) {
    std::vector<I> p(depth,{O::Const,0});p.push_back({static_cast<O>(999),0});
    result=compare(meta(p),1000000000);require(result.error==(depth<2?"bytecode stack underflow":"invalid bytecode operation"),"invalid enum pop order changed");++extra_cases;
  }
  std::cout<<"{\"passed\":true,\"original_groups\":"<<original_groups<<",\"prefix_cases\":"<<prefix_cases
           <<",\"extra_cases\":"<<extra_cases<<",\"comparisons\":"<<comparisons<<"}\n";
  require(original_groups==15,"frozen original group denominator differs");return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
'''

def replace(path,old,new):
    data=path.read_bytes().decode();assert data.count(old)==1,(str(path),old[:80]);path.write_bytes(data.replace(old,new).encode())

def main():
    assert not ROOT.exists(),'source-only freeze must not overwrite an existing candidate';ROOT.mkdir(parents=True)
    accepted=read(ACCEPT/'manifest.json');assert accepted['passed']
    shutil.copytree(ACCEPT/'source',ROOT/'source-before');shutil.copytree(ACCEPT/'source',WORK)
    for source in sorted((ROOT/'source-before').rglob('*')):
        if source.is_file():
            relative='source/'+source.relative_to(ROOT/'source-before').as_posix()
            assert sha(source)==accepted['frozen_files'][relative]['sha256']
    for name in ['cholesky_runtime.exe','libcholesky_core.a','CMakeCache.txt']:
        dest=ROOT/'baseline-build'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(ACCEPT/'builds/gnu-nested'/name,dest)
    shutil.copytree(ACCEPT/'builds/gnu-nested/CMakeFiles',ROOT/'baseline-build/CMakeFiles')
    # Complete old threaded TU is unchanged; the prospective load-pair TU owns its labels.
    original=(WORK/'src/threaded_vm.cpp').read_text()
    candidate=original.replace('"cholesky/threaded_vm.hpp"','"cholesky/load_pair_vm.hpp"').replace('CHOL_STABLE Matrix run_threaded_vm(', 'CHOL_STABLE Matrix run_load_pair_vm(')
    candidate=candidate.replace('CHOL_STABLE Matrix run_load_pair_vm(',DISCOVERY+'\nCHOL_STABLE Matrix run_load_pair_vm(',1)
    candidate=candidate.replace('  if(options.metrics) {\n',
      '  const auto fusion_start=std::chrono::steady_clock::now();\n  const auto load_pairs=discover_load_pairs(decoded);\n  const double fusion_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-fusion_start).count();\n  if(options.metrics) {\n',1)
    candidate=candidate.replace('decoded.capacity()*sizeof(DecodedInstruction);','decoded.capacity()*sizeof(DecodedInstruction)+load_pairs.starts.capacity();',1)
    candidate=candidate.replace('options.metrics->vm_backend="decoded-threaded";',
      'options.metrics->vm_backend="decoded-threaded-load-pair";\n    options.metrics->vm_fusion_plan_ms=fusion_ms;\n    options.metrics->vm_fusion_plan_bytes=load_pairs.starts.capacity();\n    options.metrics->vm_fusion_pairs_discovered=load_pairs.pairs;\n    options.metrics->vm_fusion_status=load_pairs.valid?"entry-safe-pairs":"invalid-cfg-fallback";',1)
    candidate=candidate.replace('  DecodedInstruction instruction{};',
      '  std::uint64_t executed_pairs=0;\n  struct FinalPairs {RunMetrics* metrics;std::uint64_t& value;~FinalPairs(){if(metrics)metrics->vm_fusion_pairs_executed=value;}} final_pairs{options.metrics,executed_pairs};\n  DecodedInstruction instruction{};',1)
    old_load='LLoad: {const auto slot=immediate("slot");if(!initialized[slot])throw std::runtime_error("read of uninitialized scalar");stack.push_back(slots[slot]);}NEXT();'
    assert candidate.count(old_load)==1;candidate=candidate.replace(old_load,FUSED_LOAD)
    (WORK/'src/load_pair_vm.cpp').write_text(candidate,encoding='utf-8')
    (WORK/'include/cholesky/load_pair_vm.hpp').write_text('#pragma once\n#include "cholesky/runtime.hpp"\nnamespace chol { Matrix run_load_pair_vm(const Matrix&,const Metadata&,Options); }\n')
    header=WORK/'include/cholesky/runtime.hpp'
    replace(header,'  double vm_prepare_ms=0;',
      '  double vm_prepare_ms=0;\n  double vm_fusion_plan_ms=0;\n  std::uint64_t vm_fusion_plan_bytes=0,vm_fusion_pairs_discovered=0,vm_fusion_pairs_executed=0;\n  std::string vm_fusion_status;')
    runtime=WORK/'src/runtime.cpp'
    replace(runtime,'#ifdef CHOL_PREPARED_VM\r\n#include "cholesky/prepared_vm.hpp"',
      '#if defined(CHOL_LOAD_PAIR_VM) && defined(CHOL_HAVE_THREADED_DISPATCH)\n#include "cholesky/load_pair_vm.hpp"\n#endif\n#ifdef CHOL_PREPARED_VM\r\n#include "cholesky/prepared_vm.hpp"')
    token='  if(options.vm_backend=="auto"||options.vm_backend=="decoded-threaded") {'
    replace(runtime,'       &&options.vm_backend!="decoded-threaded"',
      '       &&options.vm_backend!="decoded-threaded"\n#ifdef CHOL_LOAD_PAIR_VM\n       &&options.vm_backend!="decoded-threaded-load-pair"\n#endif')
    replace(runtime,token,
      '#ifdef CHOL_LOAD_PAIR_VM\n  if(options.vm_backend=="decoded-threaded-load-pair") {\n#ifdef CHOL_HAVE_THREADED_DISPATCH\n    return run_load_pair_vm(input,metadata,options);\n#else\n    struct PairFallbackMetric {RunMetrics* metrics;~PairFallbackMetric(){if(metrics){metrics->vm_backend="decoded-fallback";metrics->vm_fusion_status="portable-fallback";}}} fallback_metric{options.metrics};\n    return run_program<true>(input,metadata,options);\n#endif\n  }\n#endif\n'+token)
    cmake=WORK/'CMakeLists.txt'
    token='option(CHOL_COMPRESSED_METADATA'
    data=cmake.read_bytes().decode();assert data.count(token)==1
    insert='''option(CHOL_LOAD_PAIR_VM "Experimental explicit entry-safe LOAD+LOAD backend; default unchanged" OFF)
if(CHOL_LOAD_PAIR_VM)
  if(NOT CHOL_THREADED_VM OR NOT CHOL_PREPARED_VM)
    message(FATAL_ERROR "CHOL_LOAD_PAIR_VM requires CHOL_THREADED_VM and CHOL_PREPARED_VM")
  endif()
  target_compile_definitions(cholesky_core PUBLIC CHOL_LOAD_PAIR_VM=1)
  if(CHOL_COMPILER_LABELS_AS_VALUES AND NOT CHOL_THREADED_VM_FORCE_PORTABLE)
    target_sources(cholesky_core PRIVATE src/load_pair_vm.cpp)
  endif()
endif()
'''
    cmake.write_bytes(data.replace(token,insert+token).encode())
    tests='''  if(CHOL_LOAD_PAIR_VM)
    add_executable(load_pair_vm_tests tests/load_pair_vm_tests.cpp)
    target_link_libraries(load_pair_vm_tests PRIVATE cholesky_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
      target_compile_options(load_pair_vm_tests PRIVATE -fno-fast-math -ffp-contract=off)
    endif()
    add_test(NAME load_pair_vm_contract COMMAND load_pair_vm_tests)
  endif()
'''
    replace(cmake,'  if(CHOL_PREPARED_VM)\r\n',tests+'  if(CHOL_PREPARED_VM)\r\n')
    maincpp=WORK/'src/main.cpp'
    replace(maincpp,'          << "|decoded-threaded"',
      '          << "|decoded-threaded"\n#ifdef CHOL_LOAD_PAIR_VM\n          << "|decoded-threaded-load-pair"\n#endif')
    replace(maincpp,'           &&value!="decoded-threaded"',
      '           &&value!="decoded-threaded"\n#ifdef CHOL_LOAD_PAIR_VM\n           &&value!="decoded-threaded-load-pair"\n#endif')
    replace(maincpp,'    double vm_budget_first_ms=0,vm_budget_nested_ms=0;',
      '    double vm_budget_first_ms=0,vm_budget_nested_ms=0;\n    double vm_fusion_plan_ms=0;\n    std::uint64_t vm_fusion_plan_bytes_peak=0,vm_fusion_pairs_discovered=0,vm_fusion_pairs_executed=0;\n    std::string vm_fusion_status_last;')
    replace(maincpp,'      vm_budget_first_ms+=metrics.vm_budget_first_ms;vm_budget_nested_ms+=metrics.vm_budget_nested_ms;',
      '      vm_budget_first_ms+=metrics.vm_budget_first_ms;vm_budget_nested_ms+=metrics.vm_budget_nested_ms;\n      vm_fusion_plan_ms+=metrics.vm_fusion_plan_ms;\n      vm_fusion_plan_bytes_peak=std::max(vm_fusion_plan_bytes_peak,metrics.vm_fusion_plan_bytes);\n      vm_fusion_pairs_discovered+=metrics.vm_fusion_pairs_discovered;vm_fusion_pairs_executed+=metrics.vm_fusion_pairs_executed;\n      vm_fusion_status_last=metrics.vm_fusion_status;')
    replace(maincpp,'      << ",\\\"vm_budget_first_ms\\\":" << vm_budget_first_ms',
      '      << ",\\\"vm_fusion_plan_ms\\\":" << vm_fusion_plan_ms << ",\\\"vm_fusion_plan_bytes_peak\\\":" << vm_fusion_plan_bytes_peak\n      << ",\\\"vm_fusion_pairs_discovered\\\":" << vm_fusion_pairs_discovered << ",\\\"vm_fusion_pairs_executed\\\":" << vm_fusion_pairs_executed\n      << ",\\\"vm_fusion_status_last\\\":\\\"" << vm_fusion_status_last << "\\\""\n      << ",\\\"vm_budget_first_ms\\\":" << vm_budget_first_ms')
    # The old934 contract's gold/steps/PC/output stays intact, with the fourth backend appended.
    oldtest=WORK/'tests/threaded_vm_tests.cpp'
    replace(oldtest,'  for(const auto& op:m.program)coverage.insert(op.opcode);++comparisons;return c;',
      '''#ifdef CHOL_LOAD_PAIR_VM
  const auto d=run(m,"decoded-threaded-load-pair",limit);
  require(d.error==error,"load-pair error contract mismatch");
  require(a.metrics.vm_steps==d.metrics.vm_steps&&a.metrics.vm_last_pc==d.metrics.vm_last_pc,"load-pair steps/PC changed");
  require(a.output.n==d.output.n&&a.output.values.size()==d.output.values.size(),"load-pair shape differs");
  for(std::size_t i=0;i<a.output.values.size();++i)require(bits(a.output.values[i])==bits(d.output.values[i]),"load-pair bits differ");
#endif
  for(const auto& op:m.program)coverage.insert(op.opcode);++comparisons;return c;''')
    opmap=dict(zip('CONST LOAD STORE UNINIT READ WRITE DUP POP ADD SUB MUL DIV IDIV MOD NEG NOT BOOL TRUNC SQRT ABS MIN MAX FMA LT LE GT GE EQ NE JUMP JZ JNZ RETURN'.split(),
                   'Const Load Store Uninit Read Write Dup Pop Add Sub Mul Div IntDiv Mod Neg Not Bool Trunc Sqrt Abs Min Max Fma Lt Le Gt Ge Eq Ne Jump Jz Jnz Return'.split()))
    errors={'all-prefix-budget-boundaries':'','second-invalid-slot':'invalid slot','first-invalid-slot':'invalid slot',
            'second-uninitialized':'read of uninitialized scalar','first-uninitialized':'read of uninitialized scalar',
            'side-entry-second':'','bad-unused-pair':'','overflow-after-first':'bytecode stack overflow','overflow-after-second':'bytecode stack overflow',
            'intdiv-min-overflow':'undefined C integer division/remainder','integer-zero-divisor':'undefined C integer division/remainder',
            'bad-read-index':'invalid array index','negativezero-and-subnormal':'','NaN-payload-slot-loads':'','empty-return-stack':'bytecode stack underflow'}
    gold=read(DESIGN/'original-counterexamples.json');assert len(gold)==15;driver=DRIVER_HEAD;prefix_count=0
    for row in gold:
        values=[]
        for pc,ins in enumerate(row['complete_original_PROGRAM']):
            arg=repr(ins[1])if len(ins)==2 else'0'
            if str(pc)in row['argument_bit_overrides']:arg='std::bit_cast<double>(UINT64_C(0x'+row['argument_bit_overrides'][str(pc)]+'))'
            values.append('{O::'+opmap[ins[0]]+','+arg+'}')
        limits=set(row['limits'])|set(range(len(values)+2));limits.discard(1000000000);prefix_count+=len(limits)
        driver+='  group('+json.dumps(row['label'])+',meta({'+','.join(values)+'}),'+json.dumps(errors[row['label']])+',{'+','.join(str(x)+'ull'for x in sorted(set(row['limits'])))+'});\n'
    driver+=DRIVER_TAIL;(WORK/'tests/load_pair_vm_tests.cpp').write_text(driver,encoding='utf-8')
    shutil.copyfile(DESIGN/'original-counterexamples.json',ROOT/'original-counterexamples.json')
    changed=[];diffs=[]
    oldfiles={x.relative_to(ROOT/'source-before').as_posix():sha(x)for x in (ROOT/'source-before').rglob('*')if x.is_file()}
    for file in sorted(WORK.rglob('*')):
        if not file.is_file():continue
        relative=file.relative_to(WORK).as_posix()
        if oldfiles.get(relative)!=sha(file):
            changed.append(relative)
            before=(ROOT/'source-before'/relative).read_text().splitlines()if relative in oldfiles else[]
            diffs.extend(difflib.unified_diff(before,file.read_text().splitlines(),fromfile='source-before/'+relative,tofile='workspace/'+relative))
    (ROOT/'implementation.diff').write_text('\n'.join(diffs)+'\n',encoding='utf-8')
    shutil.copyfile(Path(__file__),ROOT/'producer.py')
    frozen={x.relative_to(ROOT).as_posix():{'sha256':sha(x),'bytes':x.stat().st_size}for x in sorted(ROOT.rglob('*'))if x.is_file()}
    flags=['-DCMAKE_BUILD_TYPE=Release','-DCHOL_PREPARED_VM=ON','-DCHOL_THREADED_VM=ON','-DCHOL_LOAD_PAIR_VM=ON',
           '-DCHOL_PROVED_VM_BUDGET=OFF','-DCHOL_NESTED_VM_BUDGET=OFF','-DCHOL_PACKED_READY_KEYS=OFF']
    plan={'schema':'isolated-LOAD-LOAD-source-only-implementation-v1','status':'source-only frozen; no compile/C/VM/tests',
          'artifact_root':str(ROOT),'owned_root_scope':'only G:/Hackathon-stage2-artifacts/project19/load-pair; project18 and all old F evidence untouched',
          'source_before_acceptance_sha256':sha(ACCEPT/'manifest.json'),'static_design_sha256':sha(DESIGN/'plan.json'),
          'source_before_EXE_sha256':sha(ROOT/'baseline-build/cholesky_runtime.exe'),'source_before_core_sha256':sha(ROOT/'baseline-build/libcholesky_core.a'),
          'new_header_ABI_sha256':sha(WORK/'include/cholesky/runtime.hpp'),'old_threaded_TU_byte_identical':sha(WORK/'src/threaded_vm.cpp')==oldfiles['src/threaded_vm.cpp'],
          'changed_files':changed,'frozen_files':frozen,'explicit_backend':'decoded-threaded-load-pair','default_auto_backend_changed':False,
          'discovery':'full33-op CFG targets valid; invalid enum/control disables whole package; greedy disjoint LOAD pairs with no second-PC external entry; no operand error during discovery',
          'timing':'decode+perexecution discovery included vm_prepare_ms and enclosing compute; fusionplan time/bytes/discovered/executed metrics independent; no cache',
          'semantic_boundary':'first push then4096 check before second lastpc/++steps/limit/slot/init/push then4096 NEXT; no whole-span precharge',
          'proof_policy':'fixed only in experiment; future builds proof/nestedOFF; no runtime source/hash/N routing',
          'contract_scope':{'original934_gold_plus_fourth_backend':True,'original_counterexample_groups':15,'all_prefix_cases':prefix_count,
                            'additional_numeric_payload_chain_invalidCFG_cases':True,'full15_PROGRAM_emitted_in_CPP':True,
                            'source_only_no_contract_executed':True},
          'future_configure_flags':flags,'future_builds':['GNU enabled','forced portable enabled','disabled option'],
          'future_validation':'new934/fusion prefix driver, strictFP/ABI newcore+callers, fulloriginalC compatibility then independent fixed paired costs; no promotion from staticsites',
          'estimated_resources':{'fresh_build_peak_RAM_bytes':536870912,'GNU_build_disk_estimate_bytes':100663296,
                                 'three_build_disk_estimate_bytes':301989888,'future_fullC_output_estimate_bytes':350000000,
                                 'future_cost_output_estimate_bytes':500000000,'compiler_temp':str(ROOT/'compiler-temp')},
          'no_compile_VM_C_or_small_test':True,'ordinary_sha256':sha(P/'build/cholesky_runtime.exe'),
          'memory_sha256':sha(P/'build-memory/cholesky_runtime.exe'),'ordinary_src_include_CLI_default_Metadata_untouched':True,
          'G_free_bytes':shutil.disk_usage(ROOT).free}
    write(ROOT/'manifest.json',plan)
    print(json.dumps({'source_only':True,'manifest_sha256':sha(ROOT/'manifest.json'),'root':str(ROOT),'changed_files':changed,
                      'prefix_cases':prefix_count,'frozen_files':len(frozen),'G_free_bytes':plan['G_free_bytes'],'compiled_or_run':False}),flush=True)

if __name__=='__main__':main()
