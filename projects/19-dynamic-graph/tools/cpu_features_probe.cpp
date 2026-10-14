// Baseline x86 CPUID/XGETBV only: no AVX/AVX512 code in the detector.
#include <cpuid.h>
#include <cstdint>
#include <cstring>
#include <iostream>
int main() {
  unsigned a=0,b=0,c=0,d=0;__cpuid(0,a,b,c,d);const unsigned maximum=a;
  char vendor[13]{};std::memcpy(vendor,&b,4);std::memcpy(vendor+4,&d,4);std::memcpy(vendor+8,&c,4);
  __cpuid(1,a,b,c,d);const unsigned ecx=c;
  const bool xsave=(c&(1u<<26))!=0,osxsave=(c&(1u<<27))!=0,avx=(c&(1u<<28))!=0,fma=(c&(1u<<12))!=0;
  std::uint64_t xcr0=0;
  if(xsave&&osxsave){unsigned lo=0,hi=0;asm volatile("xgetbv":"=a"(lo),"=d"(hi):"c"(0));xcr0=(std::uint64_t(hi)<<32)|lo;}
  unsigned ebx7=0,ecx7=0,edx7=0;if(maximum>=7){__cpuid_count(7,0,a,b,c,d);ebx7=b;ecx7=c;edx7=d;}
  const bool avx2=(ebx7&(1u<<5))!=0,f512=(ebx7&(1u<<16))!=0,dq=(ebx7&(1u<<17))!=0,bw=(ebx7&(1u<<30))!=0,vl=(ebx7&(1u<<31))!=0;
  char brand[49]{};unsigned ext=__get_cpuid_max(0x80000000,nullptr);
  if(ext>=0x80000004)for(unsigned i=0;i<3;++i){__cpuid(0x80000002+i,a,b,c,d);std::memcpy(brand+i*16,&a,4);std::memcpy(brand+i*16+4,&b,4);std::memcpy(brand+i*16+8,&c,4);std::memcpy(brand+i*16+12,&d,4);}
  const bool usable_avx2=xsave&&osxsave&&avx&&avx2&&fma&&(xcr0&6)==6;
  const bool usable512=xsave&&osxsave&&avx&&f512&&(xcr0&0xe6)==0xe6;
  __builtin_cpu_init();
  std::cout<<"{\"vendor\":\""<<vendor<<"\",\"brand\":\""<<brand<<"\",\"leaf1_ecx\":"<<ecx<<",\"leaf7_ebx\":"<<ebx7<<",\"leaf7_ecx\":"<<ecx7<<",\"leaf7_edx\":"<<edx7<<",\"xcr0\":"<<xcr0
    <<",\"xsave\":"<<xsave<<",\"osxsave\":"<<osxsave<<",\"avx\":"<<avx<<",\"fma\":"<<fma<<",\"avx2\":"<<avx2<<",\"avx512f\":"<<f512<<",\"avx512dq\":"<<dq<<",\"avx512bw\":"<<bw<<",\"avx512vl\":"<<vl
    <<",\"usable_avx2_fma\":"<<usable_avx2<<",\"usable_avx512f\":"<<usable512<<",\"gcc_builtin_avx512f\":"<<bool(__builtin_cpu_supports("avx512f"))<<"}\n";
}
