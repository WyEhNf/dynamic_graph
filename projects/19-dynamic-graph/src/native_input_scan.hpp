#pragma once
#include <cstddef>

// Internal, call-local scan facts. Never stored in public Options/Metadata,
// retained across calls, or reused after an input mutation or ownership swap.
namespace chol {
struct Matrix;
struct Options;
struct NativeBandFacts {
  bool finite=false;
  bool band_known=false;
  std::size_t width=0;
};
struct NativeInputScan {
  const double* values=nullptr;
  std::size_t n=0,limit=0;
  NativeBandFacts facts;
  bool matches(const double* data,std::size_t dimension,std::size_t bound) const noexcept {
    return facts.finite&&values==data&&n==dimension&&limit==bound;
  }
};
// Existing validated n*n input; limit <= (n-1)/4 and AVX2/FMA CPU gate required.
// Invalid input gives false,false,0; unknown width is a lower bound only.
NativeBandFacts fused_finite_band_avx2(const double*,std::size_t,std::size_t);
Matrix tiled_cholesky(const Matrix&,Options,bool,Matrix*,const NativeInputScan*);
bool try_structured_factor(const Matrix&,Matrix&,Options,bool,const NativeInputScan*);
bool try_structured_factor(const Matrix&,Matrix&,Options,bool,const NativeInputScan*,Matrix*);
}
