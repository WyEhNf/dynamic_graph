#pragma once
#include "cholesky/runtime.hpp"
namespace chol {
struct DecodedInstruction;
Matrix run_threaded_vm(const Matrix&,const Metadata&,Options,
                       const std::vector<DecodedInstruction>* shared_plan=nullptr);
}
