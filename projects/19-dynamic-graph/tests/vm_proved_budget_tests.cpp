#include "cholesky/runtime.hpp"
#include <bit>
#include <iostream>
#include <limits>
#include <stdexcept>
using O=chol::Opcode;using I=chol::Instruction;
namespace {
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
chol::Metadata meta(std::vector<I> p){chol::Metadata m;m.algorithm="ast_vm_v2";m.arithmetic="fp64_source_order_no_implicit_fma";m.dependencies="source_control_flow";m.slots=4;m.program=std::move(p);return m;}
struct Result {chol::Matrix output{0,{}};chol::RunMetrics metrics;std::string error;};
Result run(const chol::Metadata& m,chol::Options options,bool spd=false){Result r;options.metrics=&r.metrics;chol::Matrix input{3,std::vector<double>(9,1)};if(spd)input.values={4,0,0,0,9,0,0,0,16};try{r.output=chol::execute(input,m,options);}catch(const std::exception& e){r.error=e.what();}return r;}
void equal(const Result& a,const Result& b){
  require(a.error==b.error&&a.metrics.vm_steps==b.metrics.vm_steps&&a.metrics.vm_last_pc==b.metrics.vm_last_pc,"proof changed error/step/PC contract");
  require(a.output.n==b.output.n&&a.output.values.size()==b.output.values.size(),"proof changed shape");
  for(std::size_t k=0;k<a.output.values.size();++k)require(std::bit_cast<std::uint64_t>(a.output.values[k])==std::bit_cast<std::uint64_t>(b.output.values[k]),"proof changed IEEE754 bits");
}
}
int main(){try {
  chol::Options o;require(o.vm_step_limit==1000000000ull&&o.vm_budget_mode=="fixed"&&!o.vm_step_limit_explicit,"default fixed budget changed");o.simd="portable";
  auto simple=meta({{O::Const,0},{O::Const,-0.0},{O::Write,1},{O::Const,0},{O::Return},{O::Load,-1}});
  auto fixed=run(simple,o);require(fixed.error.empty()&&fixed.metrics.vm_budget_proof_status=="fixed"&&fixed.metrics.vm_budget_work==0&&fixed.metrics.vm_effective_step_limit==1000000000ull,"fixed policy unexpectedly analyzed");
  o.vm_budget_mode="invalid";require(run(simple,o).error=="VM budget mode must be fixed or proved","invalid mode accepted");o.vm_budget_mode="proved";
#ifndef CHOL_PROVED_VM_BUDGET
  require(run(simple,o).error=="proved VM budget is disabled in this build","disabled proved mode accepted");
  std::cout<<"{\"passed\":true,\"proved_feature_enabled\":false,\"fixed_default\":true}\n";
#else
  const char* backends[]={"auto","legacy"
#ifdef CHOL_PREPARED_VM
    ,"decoded","decoded-tos2"
#endif
#ifdef CHOL_THREADED_VM
    ,"decoded-threaded"
#endif
  };
  unsigned comparisons=0;
  const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
  std::vector<chol::Metadata> programs{
    simple,
    // Invalid target in an untaken conditional must remain a VM success, even
    // though conservative CFG analysis declines to prove it.
    meta({{O::Const,1},{O::Jz,nan},{O::Const,0},{O::Return}}),
    meta({{O::Const,0},{O::Jnz,inf},{O::Const,0},{O::Return}}),
    meta({{O::Jz,nan},{O::Const,0},{O::Return}}),
    meta({{O::Store,nan},{O::Const,0},{O::Return}}),
    meta({{O::Load,1},{O::Const,0},{O::Return}}),
    meta({{O::Const,0},{O::Const,inf},{O::Write,1}}),
    meta({{O::Const,inf},{O::Trunc}}),
    meta({{O::Const,-2147483648.0},{O::Const,-1},{O::IntDiv}}),
    meta({{O::Const,1},{O::Const,0},{O::Mod}}),
    meta({{O::Const,0},{O::Const,0},{static_cast<O>(999),0}}),
    meta({{O::Const,0},{O::Return},{static_cast<O>(999),0},{O::Load,nan}}),
    meta({{O::Const,0},{O::Const,1},{O::Return}}),
    meta({{O::Const,0},{O::Load,0},{O::Load,0},{O::Const,3},{O::Fma},{O::Write,1},{O::Const,0},{O::Return}}),
    // Finite natural loop: 3 prefix+4(T+1)guard+8T body/latch+2 suffix.
    meta({{O::Const,2},{O::Trunc},{O::Store,1},{O::Load,1},{O::Const,9},{O::Lt},{O::Jz,15},{O::Const,0},{O::Pop},{O::Load,1},{O::Const,2},{O::Add},{O::Trunc},{O::Store,1},{O::Jump,3},{O::Const,0},{O::Return}})
  };
  auto exhausted=simple;exhausted.program.resize(100000,{O::Load,-1});programs.push_back(exhausted);
  for(const auto* backend:backends) {
    o.vm_backend=backend;
    for(const auto& m:programs){auto p=run(m,o);auto f=o;f.vm_budget_mode="fixed";equal(run(m,f),p);require(p.metrics.vm_budget_mode=="proved"&&p.metrics.vm_budget_work<=250000&&p.metrics.vm_effective_step_limit==1000000000ull&&p.metrics.vm_budget_proof_ms>=0,"proof metrics/cap contract differs");++comparisons;}
    auto p=run(simple,o);require(p.metrics.vm_budget_proof_status=="proved"&&p.metrics.vm_budget_bound==5&&p.metrics.vm_budget_proof_reason=="proved","unreachable bad instruction invalidated proof");
    p=run(programs[1],o);require(p.error.empty()&&p.metrics.vm_budget_proof_status=="unknown"&&p.metrics.vm_budget_bound==0,"unknown proof changed delayed VM error");
    p=run(exhausted,o);require(p.error.empty()&&p.metrics.vm_budget_proof_status=="unknown"&&p.metrics.vm_budget_proof_reason=="work-limit","work-limit fallback failed");
    auto explicit_limit=o;explicit_limit.vm_step_limit_explicit=true;
    require(run(simple,explicit_limit).error=="proved VM budget cannot combine with an explicit VM step limit","literal default limit lost explicit meaning");
    explicit_limit.vm_step_limit_explicit=false;explicit_limit.vm_step_limit=10000000000ull;
    require(run(simple,explicit_limit).error=="proved VM budget cannot combine with an explicit VM step limit","nondefault API limit accepted with proved");
    explicit_limit.vm_budget_mode="fixed";explicit_limit.vm_step_limit=3;explicit_limit.vm_step_limit_explicit=true;
    auto short_run=run(simple,explicit_limit);require(short_run.error=="VM instruction limit exceeded"&&short_run.metrics.vm_steps==4&&short_run.metrics.vm_last_pc==3,"fixed per-op budget changed");
  }
  auto native=simple;native.optimized="scalar_cholesky_column_dag";o.engine="stage";
  for(const char* structure:{"auto","dense"}){o.structure=structure;auto n=run(native,o,true);require(n.error.empty()&&n.metrics.engine==(o.structure=="auto"?"diagonal":"stage")&&n.metrics.vm_budget_proof_status=="not-run"&&n.metrics.vm_budget_work==0&&n.metrics.vm_budget_proof_ms==0&&n.metrics.vm_effective_step_limit==0,"native path performed VM proof");}
  std::cout<<"{\"passed\":true,\"proved_feature_enabled\":true,\"fixed_default\":true,\"original_steps_and_errors_comparisons\":"<<comparisons<<",\"backends\":"<<sizeof(backends)/sizeof(backends[0])<<",\"native_bypass\":true,\"N10000_execution_started\":false}\n";
#endif
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
