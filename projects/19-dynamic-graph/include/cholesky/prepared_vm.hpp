#pragma once
#include "cholesky/runtime.hpp"
#include <bit>
namespace chol {
// Runtime-only representation; original Metadata::program is never rewritten.
// Indexed opcodes consume a checked integer payload. Every other opcode keeps
// the exact FP64 argument bits. Invalid indices retain their original bits and
// fail only when the original instruction is executed.
struct DecodedInstruction {
  Opcode opcode{};
  bool valid_index=false;
  // Private whole-program stack certificate; only element zero of an immutable
  // PreparedVM plan carries it. Ordinary decode leaves this false.
private:
  friend struct detail::PreparedVMState;
  bool stack_proved_=false;
public:
  bool has_proved_stack()const noexcept{return stack_proved_;}
  std::uint64_t payload=0;
  DecodedInstruction()=default;
  DecodedInstruction(Opcode code,double value) noexcept
    :opcode(code),payload(std::bit_cast<std::uint64_t>(value)){}
  double argument()const noexcept{return std::bit_cast<double>(payload);}
  std::size_t index()const noexcept{return static_cast<std::size_t>(payload);}
  void set_index(std::size_t value)noexcept{payload=value;}
};
static_assert(sizeof(DecodedInstruction)==16);
static_assert(sizeof(std::size_t)<=sizeof(std::uint64_t));
std::vector<DecodedInstruction> decode_vm_program(const Metadata&);
bool prove_vm_stack(const std::vector<DecodedInstruction>&) noexcept;
}
