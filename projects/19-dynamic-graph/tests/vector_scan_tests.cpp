#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
namespace chol {
bool all_finite_avx2(const double*,std::size_t);
std::size_t first_nonzero_avx2(const double*,std::size_t);
}
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
int main() {
  if(!__builtin_cpu_supports("avx2")||!__builtin_cpu_supports("fma"))return 77;
  try {
    const std::uint64_t patterns[]={0,0x8000000000000000ULL,1,0x8000000000000001ULL,
      0xfffffffffffffULL,0x800fffffffffffffULL,0x10000000000000ULL,0x8010000000000000ULL,
      0x3ff0000000000000ULL,0xbff0000000000000ULL,0x7fefffffffffffffULL,0xffefffffffffffffULL,
      0x7ff0000000000000ULL,0xfff0000000000000ULL,0x7ff8000000000001ULL,
      0xfff8000000000001ULL,0x7ff0000000000001ULL,0xfff0000000000001ULL};
    std::size_t comparisons=0;
    for(std::size_t count=0;count<=65;++count)for(std::size_t offset=0;offset<8;++offset) {
      std::vector<double> storage(count+offset+8,-0.0);auto* values=storage.data()+offset;
      require(chol::all_finite_avx2(values,count),"finite zero array failed");
      require(chol::first_nonzero_avx2(values,count)==count,"signed zero classified as nonzero");
      for(std::size_t position=0;position<count;++position)for(auto bits:patterns) {
        values[position]=std::bit_cast<double>(bits);
        const bool expected=std::all_of(values,values+count,[](double x){return std::isfinite(x);});
        require(chol::all_finite_avx2(values,count)==expected,"finite classification differs from scalar standard library");
        if(expected) {
          const auto first=std::find_if(values,values+count,[](double x){return x!=0.0;})-values;
          require(chol::first_nonzero_avx2(values,count)==static_cast<std::size_t>(first),"first nonzero differs from scalar comparison");
        }
        values[position]=-0.0;++comparisons;
      }
    }
#ifdef _WIN32
    SYSTEM_INFO info;GetSystemInfo(&info);const auto page=info.dwPageSize;
    auto* memory=static_cast<unsigned char*>(VirtualAlloc(nullptr,2*page,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    require(memory!=nullptr,"guard allocation failed");DWORD old;
    require(VirtualProtect(memory+page,page,PAGE_NOACCESS,&old)!=0,"guard protection failed");
    for(std::size_t count=0;count<=33;++count) {
      auto* values=reinterpret_cast<double*>(memory+page-count*sizeof(double));
      for(std::size_t i=0;i<count;++i)std::construct_at(values+i,-0.0);
      require(chol::all_finite_avx2(values,count),"finite scanner crosses guard or misclassifies zero");
      require(chol::first_nonzero_avx2(values,count)==count,"zero scanner crosses guard");
      if(count) {
        values[count-1]=std::bit_cast<double>(std::uint64_t{1});
        require(chol::first_nonzero_avx2(values,count)==count-1,"subnormal tail skipped");
        values[count-1]=std::bit_cast<double>(std::uint64_t{0x7ff0000000000001ULL});
        require(!chol::all_finite_avx2(values,count),"signalling NaN tail skipped");
      }
    }
    require(VirtualFree(memory,0,MEM_RELEASE)!=0,"guard release failed");
#endif
    std::cout<<"PASS finite/zero bit classes: "<<comparisons<<" scalar comparisons; lengths 0..65, offsets 0..7; protected tails 0..33\n";
  } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
