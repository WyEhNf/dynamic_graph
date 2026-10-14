#pragma once
#include <cstdint>
namespace chol {
struct SimdCapabilities {
  bool xsave=false,osxsave=false,avx=false,fma=false,avx2=false,avx512f=false;
  std::uint64_t xcr0=0;
};
inline bool usable_avx512(const SimdCapabilities& c) {
  return c.xsave&&c.osxsave&&c.avx&&c.fma&&c.avx2&&c.avx512f&&(c.xcr0&0xe6u)==0xe6u;
}
SimdCapabilities detect_simd_capabilities();
}
