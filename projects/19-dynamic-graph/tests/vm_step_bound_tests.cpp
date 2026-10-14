#include "cholesky/vm_step_bound.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using O=chol::Opcode;using I=chol::Instruction;using U=std::uint64_t;
namespace {
unsigned goldens=0,unknowns=0,boundaries=0,mutated_programs=0,proved_mutations=0,mutation_executions=0;
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
chol::Metadata metadata(std::vector<I> program){chol::Metadata m;m.algorithm="ast_vm_v2";m.arithmetic="fp64_source_order_no_implicit_fma";m.dependencies="source_control_flow";m.slots=4;m.program=std::move(program);return m;}
chol::Metadata counted(int start,int bound,int increment,bool shape=false){
  std::vector<I> p{{O::Const,double(start)},{O::Trunc},{O::Store,1},{O::Load,1}};
  if(shape)p.insert(p.end(),{{O::Load,0},{O::Load,0},{O::Mul},{O::Trunc}});
  else p.push_back({O::Const,double(bound)});
  p.push_back({O::Lt});const auto guard=p.size();p.push_back({O::Jz,0});
  p.insert(p.end(),{{O::Const,0},{O::Pop},{O::Load,1},{O::Const,double(increment)},{O::Add},{O::Trunc},{O::Store,1},{O::Jump,3}});
  p[guard].argument=double(p.size());p.insert(p.end(),{{O::Const,0},{O::Return}});return metadata(p);
}
U run(const chol::Metadata& m,U budget=1000000,bool expected_limit=false){
  chol::Options o;chol::RunMetrics metrics;o.engine="vm";o.vm_backend="legacy";o.simd="portable";o.block_size=7;o.vm_step_limit=budget;o.metrics=&metrics;std::string error;
  try{(void)chol::execute({3,std::vector<double>(9,1)},m,o);}catch(const std::exception& e){error=e.what();}
  require(error==(expected_limit?"VM instruction limit exceeded":""),"actual interpreter/error differs");return metrics.vm_steps;
}
void exact(const chol::Metadata& m,U expected){
  auto p=chol::prove_vm_step_bound(m,3,7);if(!p.proved){std::cerr<<"unknown: "<<p.reason<<'\n';throw std::runtime_error("valid golden not proved");}
  require(p.bound==expected,"independent opcode-count golden differs");require(run(m)==expected,"original interpreter steps differ");
  require(run(m,expected)==expected,"exact-bound budget failed");require(run(m,expected-1,true)==expected,"one-short budget changed steps");++goldens;boundaries+=2;
}
void unknown(const chol::Metadata& m){auto p=chol::prove_vm_step_bound(m,3,7);require(!p.proved&&p.bound==0,"unsound mutation accepted");++unknowns;}
}
int main(){try{
  for(int begin=-3;begin<=5;++begin)for(int end=-4;end<=9;++end)for(int increment=1;increment<=4;++increment){
    auto m=counted(begin,end,increment);const U trips=end<=begin?0:U((end-begin+increment-1)/increment);
    exact(m,12*trips+9); //3 prefix+4(T+1)guard+8T body/latch+2 suffix
  }
  exact(counted(0,0,1,true),15*9+12); //3 prefix+7(T+1)+8T+2, N=3
  // Independent full copy PROGRAM, source order and exact observed N10000 bound.
  auto copy=counted(0,0,1,true);copy.program.erase(copy.program.begin()+10,copy.program.begin()+12);
  copy.program.insert(copy.program.begin()+10,{{O::Load,1},{O::Load,1},{O::Read,0},{O::Write,1}});copy.program[9].argument+=2;
  exact(copy,17*9+12);auto largest=chol::prove_vm_step_bound(copy,10000,7);require(largest.proved&&largest.bound==1700000012ull,"dynamic-shape full copy bound differs");++goldens;
  auto with_dead=counted(0,4,1);with_dead.program.push_back({O::Load,-1});with_dead.program.push_back({O::Const,std::numeric_limits<double>::quiet_NaN()});exact(with_dead,12*4+9);
  exact(metadata({{O::Const,0},{O::Return}}),2);
  exact(metadata({{O::Const,1},{O::Const,2},{O::Const,3},{O::Fma},{O::Pop},{O::Const,0},{O::Return}}),7);
  auto renamed=counted(2,9,2);for(auto& in:renamed.program)if((in.opcode==O::Load||in.opcode==O::Store)&&in.argument==1)in.argument=3;exact(renamed,12*4+9);
  auto blocked=counted(0,7,1);blocked.block_slot=2;blocked.program[4]={O::Load,2};exact(blocked,12*7+9);
  // General acyclic control flow conservatively chooses the longest branch.
  auto branch=metadata({{O::Load,0},{O::Jz,5},{O::Const,0},{O::Pop},{O::Jump,5},{O::Const,0},{O::Return}});exact(branch,7);
  // Disjoint counted loops with independent preheaders; every jump rebased.
  auto first=counted(0,3,1),second=counted(1,8,3);first.program.resize(first.program.size()-2);auto offset=first.program.size();
  for(auto in:second.program){if(in.opcode==O::Jump||in.opcode==O::Jz||in.opcode==O::Jnz)in.argument+=double(offset);first.program.push_back(in);}exact(first,(12*3+9)-2+(12*3+9));
  auto conditional=counted(0,3,1);conditional.program[6].argument+=5;
  conditional.program.insert(conditional.program.begin()+9,{{O::Const,0},{O::Read,0},{O::Jz,14},{O::Const,0},{O::Pop}});exact(conditional,60);
  auto early=conditional;early.program[11].argument=20;exact(early,60);
  // The same conservative proof remains valid when real input takes early exit.
  chol::RunMetrics early_metrics;chol::Options early_options;early_options.engine="vm";early_options.vm_backend="legacy";early_options.simd="portable";early_options.metrics=&early_metrics;
  (void)chol::execute({3,std::vector<double>(9,0)},early,early_options);
  auto early_proof=chol::prove_vm_step_bound(early,3,7);require(early_metrics.vm_steps==14&&early_metrics.vm_steps<=early_proof.bound,"early-exit upper bound underestimated");++goldens;
  auto m=counted(0,8,1);m.program[10].argument=0;unknown(m); //zero progress
  m=counted(0,8,1);m.program[10].argument=-1;unknown(m);
  m=counted(0,8,1);m.program[10].argument=.5;unknown(m);
  m=counted(0,8,1);m.program[13]={O::Store,0};unknown(m); //tail bound/induction mismatch
  m=counted(0,8,1);m.program[7]={O::Store,1};unknown(m); //non-tail induction store
  m=counted(0,8,1);m.program[7]={O::Jump,12};unknown(m); //jump into partial update
  m=counted(0,8,1);m.program[7]={O::Jump,14};unknown(m); //bypass update to latch
  m=counted(0,8,1);m.program[14].argument=4;unknown(m); //new header without condition form
  m=counted(0,8,1);m.program[4]={O::Load,2};unknown(m); //uninitialized bound
  m=counted(0,8,1);m.program[4]={O::Read,0};unknown(m); //data-controlled bound
  m=counted(0,8,1);m.program[0].argument=.125;unknown(m);
  m=counted(0,8,1);m.program[0].argument=std::numeric_limits<double>::infinity();unknown(m);
  m=counted(INT32_MAX-1,INT32_MAX,2);unknown(m); //final update outside int32
  m=counted(0,8,1);m.program[3].argument=-1;unknown(m);
  m=counted(0,8,1);m.program[7]={static_cast<O>(999),0};unknown(m);
  m=counted(0,8,1);m.program[14].argument=std::numeric_limits<double>::quiet_NaN();unknown(m);
  m=counted(0,0,1,true);m.program[10]={O::Uninit,0};unknown(m); //invariant shape bound changed
  auto nested=counted(0,2,1),inner=counted(0,2,1);inner.program.resize(inner.program.size()-2);const auto length=inner.program.size();
  for(auto& in:inner.program){if((in.opcode==O::Load||in.opcode==O::Store)&&in.argument==1)in.argument=2;if(in.opcode==O::Jump||in.opcode==O::Jz)in.argument+=9;}
  nested.program[6].argument+=double(length);nested.program.insert(nested.program.begin()+9,inner.program.begin(),inner.program.end());unknown(nested);
  unknown(metadata({{O::Const,0},{O::Jz,3},{O::Jump,0},{O::Const,1},{O::Jnz,2},{O::Const,0},{O::Return}})); //irreducible cycle
  // Exhausted work returns unknown, never a new execution error or exemption.
  auto good=counted(0,7,1);for(U limit=0;limit<100;++limit){auto p=chol::prove_vm_step_bound(good,3,7,limit);require(!p.proved&&p.work<=limit,"work gate bypassed");++unknowns;}
  auto p=chol::prove_vm_step_bound(good,3,7);require(p.proved,"post-work-limit analysis retained state");
  // Independent adversarial PROGRAM mutations: every opcode at every location,
  // changed operands, malformed immediates. Successful proofs are checked
  // against the real old interpreter's step counter, including early errors.
  const double operands[]={-1,0,1,2,3,7,14,15,16,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()};
  const auto base=counted(0,7,1);
  for(std::size_t pc=0;pc<base.program.size();++pc)for(unsigned opcode=0;opcode<34;++opcode)for(double argument:operands){
    auto mutant=base;mutant.program[pc]={static_cast<O>(opcode),argument};++mutated_programs;auto proof=chol::prove_vm_step_bound(mutant,3,7);
    if(!proof.proved)continue;
    require(proof.bound<5000,"mutation verification unexpectedly needs large workload");
    for(double data:{0.0,1.0}){
      chol::RunMetrics metrics;chol::Options opts;opts.engine="vm";opts.vm_backend="legacy";opts.simd="portable";opts.metrics=&metrics;opts.vm_step_limit=5000;
      try{(void)chol::execute({3,std::vector<double>(9,data)},mutant,opts);}catch(const std::exception&){}
      require(metrics.vm_steps<=proof.bound,"mutated PROGRAM proof below actual steps");++mutation_executions;
    }
    ++proved_mutations;
  }
  require(chol::Options{}.vm_step_limit==1000000000ull,"ordinary fixed budget changed");
  std::cout<<"{\"passed\":true,\"exhaustive_goldens\":"<<goldens<<",\"unknown_mutations\":"<<unknowns<<",\"exact_and_one_short_boundaries\":"<<boundaries<<",\"adversarial_program_mutations\":"<<mutated_programs<<",\"proved_mutations\":"<<proved_mutations<<",\"actual_mutation_VM_executions\":"<<mutation_executions<<",\"ordinary_runtime_changed\":false,\"N10000_execution_started\":false}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
