#include "cholesky/prepared_vm.hpp"
#include <cmath>
#include <new>
#include <stdexcept>
namespace chol {
std::vector<DecodedInstruction> decode_vm_program(const Metadata& metadata) {
  std::vector<DecodedInstruction> result;result.reserve(metadata.program.size());
  for(const auto& source:metadata.program) {
    DecodedInstruction instruction{source.opcode,source.argument};
    std::size_t bound=0;bool indexed=false;
    switch(source.opcode) {
      case Opcode::Load:case Opcode::Store:case Opcode::Uninit:bound=metadata.slots;indexed=true;break;
      case Opcode::Jump:case Opcode::Jz:case Opcode::Jnz:bound=metadata.program.size();indexed=true;break;
      default:break;
    }
    if(indexed) {
      const auto value=source.argument;
      instruction.valid_index=std::isfinite(value)&&value>=0&&std::trunc(value)==value&&value<static_cast<double>(bound);
      if(instruction.valid_index)instruction.set_index(static_cast<std::size_t>(value));
      // Bad immediates remain represented, including unreachable ones. The
      // executing handler throws at the same original PC as legacy execution.
    }
    result.push_back(instruction);
  }
  return result;
}
// This proves operand-stack/control-flow safety, not array bounds or program
// termination. All arithmetic and VM error-producing operations still execute.
// Exact height joins reject ambiguous paths; all branch arms are examined.
bool prove_vm_stack(const std::vector<DecodedInstruction>& program) noexcept {
  constexpr std::size_t instruction_cap=100000;
  constexpr std::size_t work_cap=400000;
  if(program.empty()||program.size()>instruction_cap)return false;
  try {
    std::vector<int> heights(program.size(),-1);
    std::vector<std::size_t> pending;pending.reserve(program.size());
    heights[0]=0;pending.push_back(0);
    std::size_t work=0;
    auto reach=[&](std::size_t pc,int height) {
      if(++work>work_cap||pc>=program.size())return false;
      if(heights[pc]<0){heights[pc]=height;pending.push_back(pc);return true;}
      return heights[pc]==height;
    };
    for(std::size_t cursor=0;cursor<pending.size();++cursor) {
      if(++work>work_cap)return false;
      const auto pc=pending[cursor];const auto& instruction=program[pc];
      const int before=heights[pc];int required=0,change=0;
      bool branch=false,conditional=false,returns=false;
      switch(instruction.opcode) {
        case Opcode::Const:case Opcode::Load:change=1;break;
        case Opcode::Store:case Opcode::Pop:required=1;change=-1;break;
        case Opcode::Uninit:break;
        case Opcode::Read:required=1;break;
        case Opcode::Write:required=2;change=-2;break;
        case Opcode::Dup:required=1;change=1;break;
        case Opcode::Neg:case Opcode::Not:case Opcode::Bool:case Opcode::Trunc:
        case Opcode::Sqrt:case Opcode::Abs:required=1;break;
        case Opcode::Add:case Opcode::Sub:case Opcode::Mul:case Opcode::Div:
        case Opcode::IntDiv:case Opcode::Mod:case Opcode::Min:case Opcode::Max:
        case Opcode::Lt:case Opcode::Le:case Opcode::Gt:case Opcode::Ge:
        case Opcode::Eq:case Opcode::Ne:required=2;change=-1;break;
        case Opcode::Fma:required=3;change=-2;break;
        case Opcode::Jump:branch=true;break;
        case Opcode::Jz:case Opcode::Jnz:
          required=1;change=-1;branch=true;conditional=true;break;
        case Opcode::Return:required=1;change=-1;returns=true;break;
        default:return false;
      }
      if(before<required)return false;
      const int after=before+change;
      if(after<0||after>4096)return false;
      if(returns){if(after!=0)return false;continue;}
      if(branch) {
        if(!instruction.valid_index||!reach(instruction.index(),after))return false;
        if(!conditional)continue;
      }
      if(!reach(pc+1,after))return false;
    }
    return true;
  } catch(const std::bad_alloc&) {return false;}
    catch(const std::length_error&) {return false;}
}

}
