#include "cholesky/threaded_vm.hpp"
#include "cholesky/prepared_vm.hpp"
#ifdef CHOL_BOUNDED_OPERAND_STACK
#include "cholesky/bounded_operand_stack.hpp"
#endif
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>
// Owning locals precede the first dispatch. Handler blocks contain only POD
// temporaries and end before NEXT. RETURN and exceptions unwind normally.
#if defined(__GNUC__) && !defined(__clang__)
#define CHOL_STABLE __attribute__((noinline,noclone))
#elif defined(__clang__)
#define CHOL_STABLE __attribute__((noinline))
#else
#error This translation unit requires the labels-as-values compiler probe
#endif
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wpedantic"
namespace chol {
namespace {
std::size_t array_index(double value,std::size_t bound) {
  if(!std::isfinite(value)||value<0||std::trunc(value)!=value||value>=static_cast<double>(bound))throw std::runtime_error("invalid array index");
  return static_cast<std::size_t>(value);
}
}
template<bool StackProved>
CHOL_STABLE Matrix run_threaded_vm_impl(const Matrix& input,const Metadata& metadata,const Options& options,const std::vector<DecodedInstruction>* shared_plan) {
  const auto prepare_start=std::chrono::steady_clock::now();
  const auto owned_plan=shared_plan?std::vector<DecodedInstruction>{}:decode_vm_program(metadata);
  const auto& decoded=shared_plan?*shared_plan:owned_plan;
  if(options.metrics) {
    if(!shared_plan) {
      options.metrics->vm_prepare_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-prepare_start).count();
      options.metrics->vm_plan_builds=1;
    }
    options.metrics->vm_plan_bytes=decoded.capacity()*sizeof(DecodedInstruction);
    options.metrics->vm_backend="decoded-threaded";
  }
  Matrix output{input.n,std::vector<double>(input.values.size(),0.0)};
  std::vector<double> slots(metadata.slots,0.0);
#ifdef CHOL_BOUNDED_OPERAND_STACK
  BoundedOperandStack stack;
#else
  std::vector<double> stack;
#endif
  std::vector<bool> initialized(metadata.slots,false);
  slots[metadata.shape_slot]=input.n;initialized[metadata.shape_slot]=true;
  if(metadata.block_slot>=0){slots[metadata.block_slot]=options.block_size;initialized[metadata.block_slot]=true;}
  stack.reserve(64);
  // Keep underflow and post-opcode overflow checks at the original source PC.
  auto pop=[&]{if constexpr(!StackProved){if(stack.empty())throw std::runtime_error("bytecode stack underflow");}const auto value=stack.back();stack.pop_back();return value;};
  std::size_t pc=0,last_pc=0;
  std::uint64_t steps=0;
  struct FinalSteps {RunMetrics* metrics;std::uint64_t& value;std::size_t& pc;~FinalSteps(){if(metrics){metrics->vm_steps=value;metrics->vm_last_pc=pc;}}} final_steps{options.metrics,steps,last_pc};
#ifdef CHOL_INSTRUCTION_POINTER
  const DecodedInstruction* instruction_pointer=nullptr;
#define instruction (*instruction_pointer)
#define FETCH_INSTRUCTION() instruction_pointer=&decoded[pc]
#else
  DecodedInstruction instruction{};
#define FETCH_INSTRUCTION() instruction=decoded[pc]
#endif
  auto immediate=[&](const char* description){if(!instruction.valid_index)throw std::runtime_error(std::string("invalid ")+description);return instruction.index();};
  static void* const targets[]={&&LConst,&&LLoad,&&LStore,&&LUninit,&&LRead,&&LWrite,&&LDup,&&LPop,
    &&LAdd,&&LSub,&&LMul,&&LDiv,&&LIntDiv,&&LMod,&&LNeg,&&LNot,&&LBool,&&LTrunc,&&LSqrt,&&LAbs,
    &&LMin,&&LMax,&&LFma,&&LLt,&&LLe,&&LGt,&&LGe,&&LEq,&&LNe,&&LJump,&&LJz,&&LJnz,&&LReturn};
  static_assert(sizeof(targets)/sizeof(targets[0])==33);
#define DISPATCH() do { \
  if constexpr(!StackProved){if(pc>=decoded.size())throw std::runtime_error("program ended without return");} \
  last_pc=pc; \
  if(++steps>options.vm_step_limit)throw std::runtime_error("VM instruction limit exceeded"); \
  FETCH_INSTRUCTION();++pc; \
  const auto code=static_cast<unsigned>(instruction.opcode); \
  if constexpr(!StackProved){if(code>=33)goto LInvalid;} \
  goto *targets[code]; \
} while(false)
#define NEXT() do {if constexpr(!StackProved){if(stack.size()>4096)throw std::runtime_error("bytecode stack overflow");}DISPATCH();}while(false)
  DISPATCH();
LConst: stack.push_back(instruction.argument());NEXT();
LLoad: {const auto slot=immediate("slot");if(!initialized[slot])throw std::runtime_error("read of uninitialized scalar");stack.push_back(slots[slot]);}NEXT();
LStore: {const auto slot=immediate("slot");slots[slot]=pop();initialized[slot]=true;}NEXT();
LUninit: initialized[immediate("slot")]=false;NEXT();
LRead: {const auto index=array_index(pop(),input.values.size());stack.push_back(instruction.argument()==0?input.values[index]:output.values[index]);}NEXT();
LWrite: {const auto value=pop();const auto index=array_index(pop(),output.values.size());if(!std::isfinite(value))throw std::runtime_error("non-finite result produced by source program");output.values[index]=value;}NEXT();
LDup: {const auto value=pop();stack.push_back(value);stack.push_back(value);}NEXT();
LPop: (void)pop();NEXT();
LJump: pc=immediate("jump target");NEXT();
LJz: if(pop()==0)pc=immediate("jump target");NEXT();
LJnz: if(pop()!=0)pc=immediate("jump target");NEXT();
LReturn: if(pop()!=0)throw std::runtime_error("source function returned a nonzero status");
  if(!stack.empty())throw std::runtime_error("unbalanced bytecode stack at return");
  return output;
LNeg: stack.push_back(-pop());NEXT();
LNot: stack.push_back(pop()==0);NEXT();
LBool: stack.push_back(pop()!=0);NEXT();
LTrunc: {const auto value=std::trunc(pop());if(!std::isfinite(value)||value<std::numeric_limits<std::int32_t>::min()||value>std::numeric_limits<std::int32_t>::max())throw std::runtime_error("C int conversion outside representable int32 range");stack.push_back(value==0.0?0.0:value);}NEXT();
LSqrt: stack.push_back(std::sqrt(pop()));NEXT();
LAbs: stack.push_back(std::fabs(pop()));NEXT();
LFma: {const auto c=pop(),b=pop(),a=pop();stack.push_back(std::fma(a,b,c));}NEXT();
#define BINARY(label,expression) label: {const auto right=pop(),left=pop();const double value=(expression);stack.push_back(value);}NEXT()
  BINARY(LAdd,left+right);
  BINARY(LSub,left-right);
  BINARY(LMul,left*right);
  BINARY(LDiv,left/right);
  BINARY(LMin,std::fmin(left,right));
  BINARY(LMax,std::fmax(left,right));
  BINARY(LLt,left<right);
  BINARY(LLe,left<=right);
  BINARY(LGt,left>right);
  BINARY(LGe,left>=right);
  BINARY(LEq,left==right);
  BINARY(LNe,left!=right);
LIntDiv: {const auto right=pop(),left=pop();if(right==0||(left==std::numeric_limits<std::int32_t>::min()&&right==-1))throw std::runtime_error("undefined C integer division/remainder");double value=std::trunc(left/right);if(value==0.0)value=0.0;stack.push_back(value);}NEXT();
LMod: {const auto right=pop(),left=pop();if(right==0||(left==std::numeric_limits<std::int32_t>::min()&&right==-1))throw std::runtime_error("undefined C integer division/remainder");double value=std::fmod(left,right);if(value==0.0)value=0.0;stack.push_back(value);}NEXT();
LInvalid: (void)pop();(void)pop();throw std::runtime_error("invalid bytecode operation");
#undef BINARY
#undef NEXT
#undef DISPATCH
#undef FETCH_INSTRUCTION
#ifdef CHOL_INSTRUCTION_POINTER
#undef instruction
#endif
}
Matrix run_threaded_vm(const Matrix& input,const Metadata& metadata,Options options,
                       const std::vector<DecodedInstruction>* shared_plan) {
#ifdef CHOL_PROVED_OPERAND_STACK
  if(shared_plan&&!shared_plan->empty()&&shared_plan->front().has_proved_stack())
    return run_threaded_vm_impl<true>(input,metadata,options,shared_plan);
#endif
  return run_threaded_vm_impl<false>(input,metadata,options,shared_plan);
}

}
#pragma GCC diagnostic pop
