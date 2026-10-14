#pragma once
#include "cholesky/runtime.hpp"
namespace chol {
struct StepBoundProof {
  bool proved=false;
  std::uint64_t bound=0,work=0;
  std::size_t loops=0;
  const char* reason="unknown";
};
// Analysis only: never executes/reorders PROGRAM or emits a VM execution error.
// Unknown conservatively retains the caller's fixed budget. No source hints.
StepBoundProof prove_vm_step_bound(const Metadata&,std::uint32_t n,unsigned block,
                                  std::uint64_t work_limit=250000) noexcept;
}
