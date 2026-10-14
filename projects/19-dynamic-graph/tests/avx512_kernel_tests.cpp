#include "cholesky/simd_dispatch.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
namespace chol {void ordered_update_avx512(double*,std::size_t,const double*,const double*,std::size_t,std::size_t,std::size_t,std::size_t,bool,bool);}
namespace {
void require(bool good,const char* message){if(!good)throw std::runtime_error(message);}
struct Guarded {
  void* allocation=nullptr;double* data=nullptr;std::size_t size=0;
  explicit Guarded(std::size_t count):size(count) {
    SYSTEM_INFO info;GetSystemInfo(&info);const std::size_t page=info.dwPageSize,bytes=count*sizeof(double),rounded=((bytes+page-1)/page+1)*page;
    allocation=VirtualAlloc(nullptr,rounded+2*page,MEM_COMMIT|MEM_RESERVE,PAGE_NOACCESS);require(allocation!=nullptr,"VirtualAlloc failed");
    auto* middle=static_cast<char*>(allocation)+page;DWORD previous=0;require(VirtualProtect(middle,rounded,PAGE_READWRITE,&previous)!=0,"VirtualProtect failed");
    data=reinterpret_cast<double*>(middle+rounded-bytes);
  }
  ~Guarded(){if(allocation)VirtualFree(allocation,0,MEM_RELEASE);}
  Guarded(const Guarded&)=delete;Guarded& operator=(const Guarded&)=delete;
};
std::uint64_t bits(double value){return std::bit_cast<std::uint64_t>(value);}
}
int main() {
  try {
    // Independent gate cases never execute an unsupported vector instruction.
    const chol::SimdCapabilities enabled{true,true,true,true,true,true,0xe7};
    require(chol::usable_avx512(enabled),"full capability rejected");unsigned rejected=0;
    for(unsigned flag=0;flag<6;++flag){auto c=enabled;switch(flag){case 0:c.xsave=false;break;case 1:c.osxsave=false;break;case 2:c.avx=false;break;case 3:c.fma=false;break;case 4:c.avx2=false;break;case 5:c.avx512f=false;break;}require(!chol::usable_avx512(c),"missing hardware/OS feature accepted");++rejected;}
    for(unsigned bit:{1u,2u,5u,6u,7u}){auto c=enabled;c.xcr0&=~(UINT64_C(1)<<bit);require(!chol::usable_avx512(c),"missing extended state accepted");++rejected;}
    if(!chol::usable_avx512(chol::detect_simd_capabilities())) {std::cout<<"AVX512F unavailable; gate cases passed, vector tests skipped\n";return 77;}
    struct Golden {double x,y,z;std::uint64_t plain,fma;};
    const double maximum=std::bit_cast<double>(UINT64_C(0x7fefffffffffffff));
    const std::array<Golden,8> goldens{{
      {1.0+0x1p-27,1.0-0x1p-27,-1.0,0,UINT64_C(0xbc90000000000000)},
      {-0.0,1.0,-0.0,UINT64_C(0x8000000000000000),UINT64_C(0x8000000000000000)},
      {-0.0,1.0,+0.0,0,0},
      {0x1p-1074,1.0,0.0,1,1},
      {0x1p-1022,0.5,0.0,UINT64_C(0x0008000000000000),UINT64_C(0x0008000000000000)},
      {0x1p-1074,0.5,0.0,0,0},
      {maximum,1.0,0.0,UINT64_C(0x7fefffffffffffff),UINT64_C(0x7fefffffffffffff)},
      {maximum,2.0,-maximum,UINT64_C(0x7ff0000000000000),UINT64_C(0x7fefffffffffffff)}}};
    unsigned golden_count=0;
    for(const auto& g:goldens)for(bool fused:{false,true}) {
      const std::size_t b=17,rows=5,cols=17,stride=19;Guarded left(rows),right(cols),out((rows-1)*stride+cols);
      std::fill_n(left.data,left.size,g.x);std::fill_n(right.data,right.size,g.y);std::fill_n(out.data,out.size,g.z);
      chol::ordered_update_avx512(out.data,stride,left.data,right.data,rows,cols,1,b,false,fused);
      for(std::size_t row=0;row<rows;++row)for(std::size_t col=0;col<cols;++col)require(bits(out.data[row*stride+col])==(fused?g.fma:g.plain),"independent arithmetic bit golden mismatch");
      ++golden_count;
    }
    unsigned cases=0;
    for(std::size_t rows:{1u,3u,4u,5u,8u,9u,17u})for(std::size_t cols:{1u,7u,8u,9u,15u,16u,17u,31u,32u,33u})for(std::size_t depth:{0u,1u,3u,7u,17u})for(bool diagonal:{false,true})for(bool fused:{false,true}) {
      const auto b=std::max(rows,cols),stride=cols+3;
      Guarded left(depth?(depth-1)*b+rows:0),right(depth?(depth-1)*b+cols:0),out((rows-1)*stride+cols);
      for(std::size_t i=0;i<left.size;++i)left.data[i]=std::ldexp(static_cast<double>(static_cast<int>((i*17)%29)-14),-20);
      for(std::size_t i=0;i<right.size;++i)right.data[i]=std::ldexp(static_cast<double>(static_cast<int>((i*13)%31)-15),-20);
      for(std::size_t i=0;i<out.size;++i)out.data[i]=i%3?std::ldexp(static_cast<double>(i%11),-15):-0.0;
      std::vector<double> expected(out.data,out.data+out.size);
      for(std::size_t j=0;j<rows;++j)for(std::size_t h=0;h<(diagonal?std::min(cols,j+1):cols);++h)
        for(std::size_t k=0;k<depth;++k){const auto x=left.data[k*b+j],y=right.data[k*b+h];if(fused)expected[j*stride+h]=std::fma(x,y,expected[j*stride+h]);else{volatile double product=x*y;expected[j*stride+h]=product+expected[j*stride+h];}}
      chol::ordered_update_avx512(out.data,stride,left.data,right.data,rows,cols,depth,b,diagonal,fused);
      for(std::size_t i=0;i<out.size;++i)require(bits(out.data[i])==bits(expected[i]),"ordered/tail/upper/padding bits differ");
      ++cases;
    }
    std::cout<<"{\"passed\":true,\"gate_rejections\":"<<rejected<<",\"ieee754_goldens\":"<<golden_count<<",\"guard_page_cases\":"<<cases<<"}\n";
  }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
