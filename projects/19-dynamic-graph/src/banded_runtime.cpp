#include "cholesky/runtime.hpp"
#include "native_input_scan.hpp"
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
#include "cholesky/native_workspace.hpp"
#endif
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace chol {
#if defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
std::size_t first_nonzero_avx2(const double*,std::size_t);
#endif
namespace {
using Clock=std::chrono::steady_clock;
double elapsed(Clock::time_point start){return std::chrono::duration<double,std::milli>(Clock::now()-start).count();}
template<bool Fused,bool InPlace=false> void band_factor(const Matrix& input,Matrix& output,std::size_t width) {
  const std::size_t n=input.n;
  for(std::size_t i=0;i<n;++i) {
    const auto first=i>width?i-width:0;
    // All structurally omitted products precede the retained reduction range.
    // Their operands include an exact zero and the accumulator starts at +0.
    // Preserve off-band input zero signs; (+/-0 - +0)/positive = +/-0.
    // In-place input already contains these exact +/-0 bits. Do not invoke
    // copy_n on the same source/destination range.
    if constexpr(!InPlace)std::copy_n(input.values.data()+i*n,first,output.values.data()+i*n);
    for(std::size_t j=first;j<=i;++j) {
      double sum=0.0;
      for(std::size_t k=first;k<j;++k) {
        if constexpr(Fused)sum=std::fma(output.values[i*n+k],output.values[j*n+k],sum);
        else sum=output.values[i*n+k]*output.values[j*n+k]+sum;
      }
      const auto remainder=input.values[i*n+j]-sum;
      if(i==j) {
        if(!(remainder>0.0)||!std::isfinite(remainder))throw std::runtime_error("matrix is not positive definite at band pivot "+std::to_string(i));
        output.values[i*n+j]=std::sqrt(remainder);
      } else {
        const auto factor=remainder/output.values[j*n+j];
        if(!std::isfinite(factor))throw std::runtime_error("non-finite band factor");
        output.values[i*n+j]=factor;
      }
    }
  }
}
}

bool try_structured_factor(const Matrix& input,Matrix& output,Options options,bool fused) {
  return try_structured_factor(input,output,std::move(options),fused,nullptr,nullptr);
}
bool try_structured_factor(const Matrix& input,Matrix& output,Options options,bool fused,const NativeInputScan* scan) {
  return try_structured_factor(input,output,std::move(options),fused,scan,nullptr);
}
bool try_structured_factor(const Matrix& input,Matrix& output,Options options,bool fused,[[maybe_unused]]const NativeInputScan* scan,[[maybe_unused]]Matrix* owned_input) {
  if(options.structure=="dense")return false;
  const auto scan_start=Clock::now();const std::size_t n=input.n;
  const auto limit=std::min<std::size_t>(options.band_limit,(n-1)/4);
  std::size_t width=0;
#if defined(CHOL_FUSED_FINITE_BAND_SCAN) && defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
  if(scan&&scan->matches(input.values.data(),n,limit)) {
    // The combined interval is already included in input_validation_ms.
    // Keep structure_scan_ms free of that same time; no work is omitted from
    // whole compute. The input has not been swapped or modified at this point.
    if(options.metrics)options.metrics->structure_scan_kernel="avx2_combined_finite_band_reused";
    if(!scan->facts.band_known)return false;
    width=scan->facts.width;
  } else
#endif
  {
#ifdef CHOL_VECTOR_SCANS
  bool scan_simd=false;
#ifdef CHOL_HAVE_X86_SIMD
  scan_simd=options.simd!="portable"&&__builtin_cpu_supports("avx2")&&__builtin_cpu_supports("fma");
#endif
  if(options.metrics)options.metrics->structure_scan_kernel=scan_simd?"avx2_first_nonzero_bits":"scalar_first_nonzero";
  for(std::size_t i=1;i<n;++i) {
    std::size_t j=0;
#ifdef CHOL_HAVE_X86_SIMD
    if(scan_simd)j=first_nonzero_avx2(input.values.data()+i*n,i);else
#endif
    while(j<i&&input.values[i*n+j]==0.0)++j;
    // The earliest nonzero maximizes i-j in this row. Later coordinates
    // cannot increase its half-bandwidth; all input finiteness was checked.
    if(j<i)width=std::max(width,i-j);
    if(width>limit) {
      if(options.metrics)options.metrics->structure_scan_ms+=elapsed(scan_start);
      return false;
    }
  }
#else
  if(options.metrics)options.metrics->structure_scan_kernel="scalar_full_lower";
  for(std::size_t i=1;i<n;++i)for(std::size_t j=0;j<i;++j)if(input.values[i*n+j]!=0.0) {
    width=std::max(width,i-j);
    if(width>limit) {
      if(options.metrics)options.metrics->structure_scan_ms+=elapsed(scan_start);
      return false;
    }
  }
#endif
  if(options.metrics)options.metrics->structure_scan_ms+=elapsed(scan_start);
  }
  // Reserve the sparse-band path for a meaningful reduction in work. A dense
  // small matrix whose entire lower triangle fits the cap is not classified
  // as a sparse workload merely because its dimension is small.
  if(width&&width*4>=n)return false;
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
  // Classification has proved this call never uses tiled factor storage.
  // No workspace lease or worker-context lock is held on this path. Close
  // before owned callers allocate full L; close/wait stays inside execute.
  if(options.native_workspace&&options.native_workspace->trim_on_structured())options.native_workspace->close();
#endif
  // Only the actual owned input with deferred output allocation is eligible.
  // Borrowed/preallocated calls keep disjoint input and output storage.
  bool reuse_structured=false;
#ifdef CHOL_REUSE_STRUCTURED_INPUT
  reuse_structured=owned_input==&input&&output.values.empty();
#endif
  if(!reuse_structured&&output.values.empty())output.values.assign(input.values.size(),0.0);
  const auto kernel_start=Clock::now();
  if(reuse_structured) {
    // Each original A(i,j) is consumed immediately before this cell is
    // overwritten. Earlier rows/columns are read only as completed L factors.
    // Do not swap the vector yet: input aliases *owned_input throughout math.
    if(fused)band_factor<true,true>(input,*owned_input,width);
    else band_factor<false,true>(input,*owned_input,width);
  } else {
    if(fused)band_factor<true>(input,output,width);else band_factor<false>(input,output,width);
  }
  const auto kernel_ms=options.metrics?elapsed(kernel_start):0.0;
  if(reuse_structured) {
    const auto recycle_start=Clock::now();
    for(std::size_t row=0;row<n;++row)
      std::fill(owned_input->values.begin()+row*n+row+1,
                owned_input->values.begin()+(row+1)*n,0.0);
    output.values.swap(owned_input->values);
    // No input.values access follows the swap. This submetric covers exactly
    // upper +0 clearing and ownership swap; factor math remains kernel_ms.
    if(options.metrics) {
      options.metrics->input_buffer_reused=true;
      options.metrics->input_recycle_ms=elapsed(recycle_start);
    }
  }
  if(options.metrics) {
    options.metrics->engine=width?"banded":"diagonal";
    options.metrics->structure_bandwidth=static_cast<unsigned>(width);
    options.metrics->kernel_ms=kernel_ms;
    options.metrics->worker_threads=1;
  }
  return true;
}
}
