#include "cholesky/runtime.hpp"
#include "cholesky/prepared_vm.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
using O=chol::Opcode;using I=chol::Instruction;
namespace {
void require(bool good,const char* message){if(!good)throw std::runtime_error(message);}
struct Result {chol::Matrix output{0,{}};chol::RunMetrics metrics;std::string error;};
chol::Metadata meta(std::vector<I> program) {
  chol::Metadata m;m.algorithm="ast_vm_v2";m.arithmetic="fp64_source_order_no_implicit_fma";m.dependencies="source_control_flow";m.optimized="none";m.slots=3;m.shape_slot=0;m.block_slot=-1;m.program=std::move(program);return m;
}
Result run(const chol::Metadata& metadata,const char* backend,std::uint64_t limit=100000) {
  Result result;chol::Options options;options.engine="vm";options.simd="portable";options.vm_backend=backend;options.vm_step_limit=limit;options.metrics=&result.metrics;
  try{result.output=chol::execute({3,{4,0,0,0,9,0,0,0,16}},metadata,options);}catch(const std::exception& e){result.error=e.what();}return result;
}
std::uint64_t bits(double value){return std::bit_cast<std::uint64_t>(value);}
unsigned comparisons=0;std::set<O> coverage;
Result pair(const chol::Metadata& m,const std::string& error="",std::uint64_t limit=100000) {
  const auto a=run(m,"legacy",limit),b=run(m,"decoded",limit);
  require(a.error==error&&b.error==error,"legacy/decoded error contract mismatch");
  require(a.metrics.vm_steps==b.metrics.vm_steps&&a.metrics.vm_last_pc==b.metrics.vm_last_pc,"original steps/PC changed");
  require(a.output.n==b.output.n&&a.output.values.size()==b.output.values.size(),"result shape differs");
  for(std::size_t i=0;i<a.output.values.size();++i)require(bits(a.output.values[i])==bits(b.output.values[i]),"result bits differ");
  for(const auto& op:m.program)coverage.insert(op.opcode);++comparisons;return b;
}
void number(std::vector<I> operations,std::uint64_t expected) {
  std::vector<I> program{{O::Const,0}};program.insert(program.end(),operations.begin(),operations.end());program.insert(program.end(),{{O::Write,1},{O::Const,0},{O::Return,0}});
  const auto out=pair(meta(program));require(bits(out.output.values[0])==expected,"independent bit golden differs");
  for(std::uint64_t limit=0;limit<=program.size()+1;++limit) {
    const auto value=pair(meta(program),limit<program.size()?"VM instruction limit exceeded":"",limit);
    require(value.metrics.vm_steps==(limit<program.size()?limit+1:program.size()),"step budget boundary differs");
  }
}
}
int main(){try {
  const std::array<std::pair<O,std::uint64_t>,14> binary{{
    {O::Add,UINT64_C(0x4014000000000000)},{O::Sub,UINT64_C(0x3ff0000000000000)},
    {O::Mul,UINT64_C(0x4018000000000000)},{O::Div,UINT64_C(0x3ff8000000000000)},
    {O::Min,UINT64_C(0x4000000000000000)},{O::Max,UINT64_C(0x4008000000000000)},
    {O::Lt,0},{O::Le,0},{O::Gt,UINT64_C(0x3ff0000000000000)},{O::Ge,UINT64_C(0x3ff0000000000000)},
    {O::Eq,0},{O::Ne,UINT64_C(0x3ff0000000000000)},{O::IntDiv,UINT64_C(0x3ff0000000000000)},{O::Mod,UINT64_C(0x3ff0000000000000)}}};
  for(const auto& [op,value]:binary)number({{O::Const,3},{O::Const,2},{op,0}},value);
  number({{O::Const,-5},{O::Const,2},{O::IntDiv,0}},UINT64_C(0xc000000000000000));
  number({{O::Const,-5},{O::Const,2},{O::Mod,0}},UINT64_C(0xbff0000000000000));
  number({{O::Const,+0.0},{O::Neg,0}},UINT64_C(0x8000000000000000));
  number({{O::Const,-0.0},{O::Abs,0}},0);number({{O::Const,-0.0},{O::Not,0}},UINT64_C(0x3ff0000000000000));
  number({{O::Const,-0.0},{O::Bool,0}},0);number({{O::Const,-0.5},{O::Trunc,0}},0);
  number({{O::Const,4},{O::Sqrt,0}},UINT64_C(0x4000000000000000));
  number({{O::Const,0x1p-1074},{O::Const,1},{O::Mul,0}},1);
  number({{O::Const,0x1p-1022},{O::Const,0.5},{O::Mul,0}},UINT64_C(0x0008000000000000));
  number({{O::Const,1+0x1p-27},{O::Const,1-0x1p-27},{O::Mul,0},{O::Const,-1},{O::Add,0}},0);
  number({{O::Const,1+0x1p-27},{O::Const,1-0x1p-27},{O::Const,-1},{O::Fma,0}},UINT64_C(0xbc90000000000000));
  number({{O::Const,-0.0},{O::Dup,0},{O::Pop,0}},UINT64_C(0x8000000000000000));
  number({{O::Const,7},{O::Store,1},{O::Load,1}},UINT64_C(0x401c000000000000));
  number({{O::Const,0},{O::Read,0}},UINT64_C(0x4010000000000000));
  number({{O::Const,0},{O::Read,1}},0);
  number({{O::Uninit,1},{O::Const,7},{O::Store,1},{O::Load,1}},UINT64_C(0x401c000000000000));
  // Full32/64-bit immediates and inactive faulty operations are C++ API cases.
  const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
  for(double invalid:{-1.0,0.5,3.0,nan,inf})for(O op:{O::Load,O::Store,O::Uninit}) {
    pair(meta({{op,invalid},{O::Const,0},{O::Return,0}}),"invalid slot");
    pair(meta({{O::Const,0},{O::Return,0},{op,invalid}}));
  }
  for(double invalid:{-1.0,0.5,100.0,nan,inf}) {
    pair(meta({{O::Jump,invalid},{O::Const,0},{O::Return,0}}),"invalid jump target");
    pair(meta({{O::Const,0},{O::Return,0},{O::Jump,invalid}}));
    pair(meta({{O::Jz,invalid},{O::Const,0},{O::Return,0}}),"bytecode stack underflow");
    pair(meta({{O::Const,1},{O::Jz,invalid},{O::Const,0},{O::Return,0}}));
    pair(meta({{O::Const,0},{O::Jnz,invalid},{O::Const,0},{O::Return,0}}));
    pair(meta({{O::Const,0},{O::Jz,invalid},{O::Const,0},{O::Return,0}}),"invalid jump target");
    pair(meta({{O::Const,1},{O::Jnz,invalid},{O::Const,0},{O::Return,0}}),"invalid jump target");
  }
  pair(meta({{O::Jump,2},{O::Load,-1},{O::Const,0},{O::Return,0}}));
  pair(meta({{O::Jump,0}}),"VM instruction limit exceeded",17);
  pair(meta({{O::Const,0},{O::Return,0},{static_cast<O>(999),0}}));
  pair(meta({{O::Const,0},{O::Const,0},{static_cast<O>(999),0}}),"invalid bytecode operation");
  pair(meta({{O::Load,1},{O::Const,0},{O::Return,0}}),"read of uninitialized scalar");
  pair(meta({{O::Const,1},{O::Store,1},{O::Uninit,1},{O::Load,1}}),"read of uninitialized scalar");
  pair(meta({{O::Const,9},{O::Read,0}}),"invalid array index");
  pair(meta({{O::Const,-1},{O::Const,1},{O::Write,1}}),"invalid array index");
  pair(meta({{O::Const,0},{O::Const,inf},{O::Write,1}}),"non-finite result produced by source program");
  pair(meta({{O::Const,1},{O::Return,0}}),"source function returned a nonzero status");
  pair(meta({{O::Const,4},{O::Const,0},{O::Return,0}}),"unbalanced bytecode stack at return");
  pair(meta({{O::Const,0}}),"program ended without return");
  pair(meta({{O::Pop,0}}),"bytecode stack underflow");
  for(double invalid:{inf,nan,2147483648.0,-2147483649.0})pair(meta({{O::Const,invalid},{O::Trunc,0}}),"C int conversion outside representable int32 range");
  for(O op:{O::IntDiv,O::Mod}) {
    pair(meta({{O::Const,1},{O::Const,0},{op,0}}),"undefined C integer division/remainder");
    pair(meta({{O::Const,-2147483648.0},{O::Const,-1},{op,0}}),"undefined C integer division/remainder");
  }
  std::vector<I> overflow(4097,{O::Const,0});pair(meta(overflow),"bytecode stack overflow");
  std::vector<I> boundary(4096,{O::Const,-0.0});boundary.insert(boundary.end(),4096,{O::Pop,0});boundary.insert(boundary.end(),{{O::Const,0},{O::Return,0}});pair(meta(boundary),"",9000);
  // Direct C++ objects keep legacy READ nonzero/WRITE ignored-arg behavior;
  // serialized protocols separately reject such array identifiers.
  number({{O::Const,0},{O::Read,2}},0);
  pair(meta({{O::Const,0},{O::Const,7},{O::Write,0},{O::Const,0},{O::Return,0}}));
  require(coverage.size()==34,"opcode coverage missing"); //33 plus invalid enum
  std::cout<<"{\"passed\":true,\"opcode_coverage\":33,\"comparisons\":"<<comparisons<<",\"stack_limit\":4096,\"decode_phase_only\":true}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
