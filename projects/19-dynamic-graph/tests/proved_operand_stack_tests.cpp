#include "cholesky/prepared_vm.hpp"
#include <atomic>
#include <bit>
#include <cfenv>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>

// Force each analyzer allocation to fail independently. The decoded program
// already exists when this switch is set; VM execution is never fault-injected.
thread_local int allocation_countdown=-1;
void* operator new(std::size_t size) {
  if(allocation_countdown>=0&&allocation_countdown--==0)throw std::bad_alloc{};
  if(void* p=std::malloc(size?size:1))return p;
  throw std::bad_alloc{};
}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
using O=chol::Opcode;using I=chol::Instruction;
template<class T> concept PublicCertificateWrite=requires(T& value){value.stack_proved_=true;};
static_assert(!PublicCertificateWrite<chol::DecodedInstruction>);
static_assert(sizeof(chol::DecodedInstruction)==16);
void require(bool good,const char* text){if(!good)throw std::runtime_error(text);}
chol::Metadata metadata(std::vector<I> code){
  chol::Metadata m;m.algorithm="ast_vm_v2";m.slots=3;m.shape_slot=0;m.block_slot=1;
  m.program=std::move(code);return m;
}
struct Outcome {chol::Matrix output{0,{}};std::string error;std::uint64_t steps=0,pc=0;};
Outcome run(const chol::Metadata& m,const char* backend,bool session,std::uint64_t limit) {
  chol::Options o;o.engine="vm";o.simd="portable";o.vm_backend=backend;o.vm_step_limit=limit;
  chol::RunMetrics metrics;o.metrics=&metrics;Outcome out;
  const chol::Matrix input{3,{4,-0.0,0x1p-1074,0,9,0,0,0,16}};
  try {
    if(session){chol::PreparedVM owner(m);out.output=chol::execute(input,owner,o);}
    else out.output=chol::execute(input,m,o);
  }catch(const std::exception& e){out.error=e.what();}
  out.steps=metrics.vm_steps;out.pc=metrics.vm_last_pc;return out;
}
void equal(const Outcome& a,const Outcome& b) {
  require(a.error==b.error&&a.steps==b.steps&&a.pc==b.pc,"error/steps/PC changed");
  require(a.output.n==b.output.n&&a.output.values.size()==b.output.values.size(),"output shape changed");
  for(std::size_t i=0;i<a.output.values.size();++i)
    require(std::bit_cast<std::uint64_t>(a.output.values[i])==std::bit_cast<std::uint64_t>(b.output.values[i]),"output bits changed");
}
unsigned proof_cases=0,semantic_cases=0,accepted=0,rejected=0;
void check(std::vector<I> code,bool expected,const char* error="",std::uint64_t limit=10000,bool execute=true) {
  const auto m=metadata(std::move(code));const auto decoded=chol::decode_vm_program(m);
  for(const auto& instruction:decoded)require(!instruction.has_proved_stack(),"ordinary decode published certificate");
  const bool proof=chol::prove_vm_stack(decoded);
  require(proof==expected,"unexpected static certificate");++proof_cases;
  if(proof)++accepted;else ++rejected;
  if(!execute)return;
  const auto legacy=run(m,"legacy",false,limit);
  require(legacy.error==error,"independent expected error disagrees");
  equal(legacy,run(m,"decoded-threaded",false,limit));
  equal(legacy,run(m,"decoded-threaded",true,limit));
  equal(legacy,run(m,"decoded",true,limit));
  ++semantic_cases;
}
int main(){try{
  check({},false,"",10,false);
  check({{O::Const,0},{O::Return,0}},true);
  check({{O::Const,0},{O::Return,0}},true,"VM instruction limit exceeded",0);
  check({{O::Const,0},{O::Return,0}},true,"VM instruction limit exceeded",1);
  check({{O::Const,0},{O::Return,0}},true,"",2);
  check({{O::Const,0}},false,"program ended without return");
  check({{O::Pop,0},{O::Const,0},{O::Return,0}},false,"bytecode stack underflow");
  check({{O::Const,1},{O::Const,2},{O::Fma,0}},false,"bytecode stack underflow");
  check({{O::Const,1},{O::Return,0}},true,"source function returned a nonzero status");
  check({{O::Const,7},{O::Const,0},{O::Return,0}},false,"unbalanced bytecode stack at return");
  check({{O::Jump,0}},true,"VM instruction limit exceeded",17);
  check({{O::Const,0},{O::Jump,0}},false,"bytecode stack overflow",10000);
  check({{O::Const,0},{O::Return,0},{static_cast<O>(999),0}},true);
  check({{O::Jump,2},{static_cast<O>(999),0},{O::Const,0},{O::Return,0}},true);
  check({{O::Const,0},{O::Const,0},{static_cast<O>(999),0}},false,"invalid bytecode operation");
  check({{O::Jump,999},{O::Const,0},{O::Return,0}},false,"invalid jump target");
  // Both arms join at identical height; guard data does not affect the proof.
  check({{O::Load,0},{O::Jz,4},{O::Const,7},{O::Jump,5},{O::Const,8},
         {O::Pop,0},{O::Const,0},{O::Return,0}},true);
  // Non-taken arm leaves one extra operand: reject rather than trusting one path.
  check({{O::Const,1},{O::Jz,4},{O::Jump,5},{O::Pop,0},{O::Const,8},
         {O::Const,0},{O::Return,0}},false);
  check({{O::Const,1},{O::Jz,999},{O::Const,0},{O::Return,0}},false);
  check({{O::Const,0},{O::Return,0},{O::Jump,999}},true);
  // Successful stack proof must not suppress other original errors.
  check({{O::Load,2},{O::Pop,0},{O::Const,0},{O::Return,0}},true,"read of uninitialized scalar");
  check({{O::Load,-1},{O::Pop,0},{O::Const,0},{O::Return,0}},true,"invalid slot");
  check({{O::Const,9},{O::Read,0},{O::Pop,0},{O::Const,0},{O::Return,0}},true,"invalid array index");
  const double inf=std::numeric_limits<double>::infinity();
  check({{O::Const,-1},{O::Const,inf},{O::Write,1},{O::Const,0},{O::Return,0}},true,"invalid array index");
  check({{O::Const,0},{O::Const,inf},{O::Write,1},{O::Const,0},{O::Return,0}},true,"non-finite result produced by source program");
  check({{O::Const,2147483648.0},{O::Trunc,0},{O::Pop,0},{O::Const,0},{O::Return,0}},true,"C int conversion outside representable int32 range");
  for(O operation:{O::IntDiv,O::Mod})
    check({{O::Const,1},{O::Const,0},{operation,0},{O::Pop,0},{O::Const,0},{O::Return,0}},true,"undefined C integer division/remainder");
  for(unsigned depth:{1u,64u,4095u,4096u}) {
    std::vector<I> code(depth,{O::Const,-0.0});
    code.insert(code.end(),depth,{O::Pop,0});code.insert(code.end(),{{O::Const,0},{O::Return,0}});
    check(code,true);
  }
  std::vector<I> dup(4096,{O::Const,0});dup.push_back({O::Dup,0});
  check(dup,false,"bytecode stack overflow");
  std::vector<I> overflow(4097,{O::Const,0});check(overflow,false,"bytecode stack overflow");
  std::vector<I> capped(100001,{O::Pop,0});capped[0]={O::Const,0};capped[1]={O::Return,0};
  check(capped,false);
  // Analyzer allocation failure must return unknown without throwing; first
  // and second allocations exercise complete and partial-construction cleanup.
  const auto small=chol::decode_vm_program(metadata({{O::Const,0},{O::Return,0}}));
  unsigned allocation_failures=0;
  for(int fail_after:{0,1}) {
    allocation_countdown=fail_after;
    const bool result=chol::prove_vm_stack(small);
    allocation_countdown=-1;
    require(!result,"allocation failure published certificate");++allocation_failures;
  }
  // Static analysis itself must not alter even FE_INEXACT. Runtime telemetry
  // has a separate historical limitation; this integer-only proof has none.
  const auto original_round=std::fegetround();const auto original_flags=std::fetestexcept(FE_ALL_EXCEPT);
  const auto snan=std::bit_cast<double>(UINT64_C(0x7ff0000000001234));
  auto fp=chol::decode_vm_program(metadata({{O::Const,snan},{O::Pop,0},{O::Const,0},{O::Return,0}}));
  unsigned fenv_checks=0;
  for(int round:{FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO})for(int flags:{0,FE_DIVBYZERO,FE_INEXACT,FE_INVALID|FE_OVERFLOW}) {
    require(std::fesetround(round)==0,"round mode unsupported");std::feclearexcept(FE_ALL_EXCEPT);
    if(flags)std::feraiseexcept(flags);
    const int before=std::fetestexcept(FE_ALL_EXCEPT);
    const bool proof=chol::prove_vm_stack(fp);
    const int after=std::fetestexcept(FE_ALL_EXCEPT);
    require(proof&&before==after&&std::fegetround()==round,"static proof changed fenv");++fenv_checks;
  }
  std::fesetround(original_round);std::feclearexcept(FE_ALL_EXCEPT);
  if(original_flags)std::feraiseexcept(original_flags);
  std::cout<<"{\"passed\":true,\"proof_cases\":"<<proof_cases
    <<",\"semantic_cases\":"<<semantic_cases<<",\"accepted\":"<<accepted
    <<",\"rejected\":"<<rejected<<",\"allocation_failures\":"<<allocation_failures
    <<",\"strict_static_fenv_checks\":"<<fenv_checks
    <<",\"public_certificate_write\":false,\"decoded_record_bytes\":16}\n";
}catch(const std::exception& e){allocation_countdown=-1;std::cerr<<e.what()<<'\n';return 1;}}
