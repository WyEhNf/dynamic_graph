// Baseline ISA. XGETBV is used only after XSAVE/OSXSAVE CPUID validation.
#include "cholesky/simd_dispatch.hpp"
#include <cpuid.h>
namespace chol {
SimdCapabilities detect_simd_capabilities() {
  SimdCapabilities caps;unsigned a=0,b=0,c=0,d=0;
  if(__get_cpuid_max(0,nullptr)<1)return caps;
  __cpuid(1,a,b,c,d);
  caps.xsave=(c&(1u<<26))!=0;caps.osxsave=(c&(1u<<27))!=0;caps.avx=(c&(1u<<28))!=0;caps.fma=(c&(1u<<12))!=0;
  if(caps.xsave&&caps.osxsave) {
    unsigned lo=0,hi=0;asm volatile("xgetbv":"=a"(lo),"=d"(hi):"c"(0));caps.xcr0=(std::uint64_t(hi)<<32)|lo;
  }
  if(__get_cpuid_max(0,nullptr)>=7){__cpuid_count(7,0,a,b,c,d);caps.avx2=(b&(1u<<5))!=0;caps.avx512f=(b&(1u<<16))!=0;}
  return caps;
}
}
