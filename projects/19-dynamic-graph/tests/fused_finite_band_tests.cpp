#include "native_input_scan.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <immintrin.h>
#define NOMINMAX
#include <windows.h>

namespace {
std::string active;
std::size_t cases=0,calls=0,large_calls=0,match_controls=0;
std::array<std::size_t,4> round_calls{},denormal_calls{};
std::array<std::size_t,2> seed_calls{};
void require(bool ok,const char* what){if(!ok)throw std::runtime_error(active+": "+what);}
struct Environment {
  fenv_t env; unsigned mxcsr;
  Environment():mxcsr(_mm_getcsr()){require(fegetenv(&env)==0,"fegetenv failed");}
  ~Environment(){fesetenv(&env);_mm_setcsr(mxcsr);}
};
// Entire committed payload is read-only while the actual classifier runs. Its
// exact final byte abuts PAGE_NOACCESS, including 1/2/3-lane vector tails.
struct Guarded {
  unsigned char* raw=nullptr; double* data=nullptr; std::size_t n,count,committed,page; bool readonly=false;
  explicit Guarded(std::size_t dim):n(dim),count(dim*dim) {
    SYSTEM_INFO si;GetSystemInfo(&si);page=si.dwPageSize;
    committed=((count*8+page-1)/page)*page;
    raw=static_cast<unsigned char*>(VirtualAlloc(nullptr,committed+page,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    require(raw!=nullptr,"VirtualAlloc failed"); DWORD old;
    require(VirtualProtect(raw+committed,page,PAGE_NOACCESS,&old)!=0,"tail guard failed");
    data=reinterpret_cast<double*>(raw+committed-count*8);
    for(std::size_t i=0;i<count;++i)put(i,(i&1)?0x8000000000000000ULL:0ULL);
  }
  ~Guarded(){if(raw)VirtualFree(raw,0,MEM_RELEASE);}
  void protect(bool read){DWORD old;require(VirtualProtect(raw,committed,read?PAGE_READONLY:PAGE_READWRITE,&old)!=0,"payload protection failed");readonly=read;}
  void put(std::size_t at,std::uint64_t bits){require(!readonly&&at<count,"bad fixture write");std::memcpy(data+at,&bits,8);}
  void reset(std::size_t at){put(at,(at&1)?0x8000000000000000ULL:0ULL);}
};
std::uint64_t bits_at(const double* p,std::size_t index){std::uint64_t b;std::memcpy(&b,p+index,8);return b;}
struct Reference {bool finite=true;std::size_t width=0;};
Reference reference(const double* p,std::size_t n) {
  // Deliberately no first-nonzero, vector chunks, early exit or cap. Every cell
  // contributes independently; width is the maximum distance of ANY nonzero
  // lower cell. Nonfinite anywhere dominates, including after dense rejection.
  Reference r;
  for(std::size_t i=0;i<n;++i)for(std::size_t j=0;j<n;++j){
    const auto b=bits_at(p,i*n+j);
    if(((b>>52)&0x7ffULL)==0x7ffULL)r.finite=false;
    if(j<i&&(b&0x7fffffffffffffffULL))r.width=std::max(r.width,i-j);
  }
  return r;
}
void controls(const double* p,std::size_t n,std::size_t cap,chol::NativeBandFacts f){
  chol::NativeInputScan facts{p,n,cap,f};
  require(facts.matches(p,n,cap)==f.finite,"facts finite match contract");++match_controls;
  require(!facts.matches(p+1,n,cap),"facts pointer mismatch accepted");++match_controls;
  require(!facts.matches(p,n+1,cap),"facts dimension mismatch accepted");++match_controls;
  require(!facts.matches(p,n,cap+1),"facts cap mismatch accepted");++match_controls;
  // This is the scan-consumer eligibility predicate only. Actual runtime
  // fallback is separately checked by the ownership/API acceptance branch.
  const bool eligible=facts.matches(p,n,cap)&&facts.facts.band_known;
  require(eligible==(f.finite&&f.band_known),"unknown/invalid eligibility");++match_controls;
}
void check(Guarded& a,std::size_t cap,const std::string& name){
  active=name+" n="+std::to_string(a.n)+" cap="+std::to_string(cap);
  require(cap<=(a.n-1)/4,"fixture violates direct classifier cap precondition");
  const auto expected=reference(a.data,a.n);
  a.protect(true);
  Environment saved;
  constexpr std::array<int,4> rounds={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};
  chol::NativeBandFacts last;
  for(std::size_t r=0;r<rounds.size();++r)for(unsigned mode=0;mode<4;++mode)for(unsigned seed=0;seed<2;++seed){
    require(fesetenv(&saved.env)==0,"restore setup environment failed");
    require(fesetround(rounds[r])==0,"rounding setup failed");
    auto mx=_mm_getcsr();mx&=~((1u<<15)|(1u<<6));if(mode&1)mx|=1u<<15;if(mode&2)mx|=1u<<6;_mm_setcsr(mx);
    require(feclearexcept(FE_ALL_EXCEPT)==0,"clear flags failed");
    if(seed)require(feraiseexcept(FE_ALL_EXCEPT)==0,"seed flags failed");
    const auto before_mx=_mm_getcsr(); const int before_round=fegetround(), before_flags=fetestexcept(FE_ALL_EXCEPT);
    require(before_flags==(seed?FE_ALL_EXCEPT:0),"not all requested flags were seeded");
    // No clocks, floating arithmetic, comparisons, or metric conversion here.
    last=chol::fused_finite_band_avx2(a.data,a.n,cap);
    const auto after_mx=_mm_getcsr(); const int after_round=fegetround(),after_flags=fetestexcept(FE_ALL_EXCEPT);
    require(before_mx==after_mx,"MXCSR changed");
    require(before_round==after_round,"rounding mode changed");
    require(before_flags==after_flags,"FP exception flags changed");
    require(last.finite==expected.finite,"finite mismatch with independent bit reference");
    if(!expected.finite)require(!last.band_known&&last.width==0,"invalid result contract");
    else if(expected.width<=cap)require(last.band_known&&last.width==expected.width,"exact accepted band mismatch");
    else require(!last.band_known&&last.width>cap&&last.width<=expected.width,"unknown lower-bound contract");
    ++calls;++round_calls[r];++denormal_calls[mode];++seed_calls[seed];if(a.n==10000)++large_calls;
  }
  controls(a.data,a.n,cap,last); ++cases;
  a.protect(false);
}
void altered(Guarded& a,std::size_t cap,const std::string& name,std::initializer_list<std::pair<std::size_t,std::uint64_t>> writes){
  for(auto [i,b]:writes)a.put(i,b);check(a,cap,name);for(auto [i,b]:writes){(void)b;a.reset(i);}
}
void small(){
  constexpr std::array<std::uint64_t,18> patterns={0,0x8000000000000000ULL,1,0x8000000000000001ULL,
    0xfffffffffffffULL,0x800fffffffffffffULL,0x10000000000000ULL,0x8010000000000000ULL,
    0x3ff0000000000000ULL,0xbff0000000000000ULL,0x7fefffffffffffffULL,0xffefffffffffffffULL,
    0x7ff0000000000000ULL,0xfff0000000000000ULL,0x7ff8000000000001ULL,0xfff8000000000001ULL,
    0x7ff0000000000001ULL,0xfff0000000000001ULL};
  constexpr std::array<std::size_t,18> dims={3,4,5,7,8,9,15,16,17,31,32,33,127,128,129,255,256,257};
  for(auto n:dims){
    Guarded a(n);const auto bound=(n-1)/4;
    std::set<std::size_t> caps={0,std::min<std::size_t>(1,bound),std::min<std::size_t>(7,bound),std::min<std::size_t>(128,bound)};
    for(auto cap:caps){
      check(a,cap,"signed-zeros");
      if(cap)altered(a,cap,"width-at-cap",{{(n-1)*n+(n-1-cap),1ULL}});
      altered(a,cap,"width-over-cap",{{(n-1)*n+(n-2-cap),0x8000000000000001ULL}});
    }
    // Vary earliest lower nonzero through every lane and both vector chunks;
    // later entries, then an earlier entry, must not shrink the global width.
    const auto row=std::min<std::size_t>(n-1,12);
    for(std::size_t j=0;j<std::min<std::size_t>(row,8);++j){
      altered(a,bound,"first-nonzero-lane-"+std::to_string(j),{{row*n+j,1ULL}});
      if(j+1<row)altered(a,bound,"first-before-later-"+std::to_string(j),{{row*n+j,1ULL},{row*n+j+1,0xbff0000000000000ULL}});
      if(j)altered(a,bound,"earlier-before-first-"+std::to_string(j),{{row*n+j,1ULL},{row*n+j-1,0x3ff0000000000000ULL}});
    }
    if(n==3||n==7||n==9||n==33||n==257){
      std::set<std::size_t> positions={0,1,2,3,n-1,n,n+1,n+2,n*n-1,n*n-2,n*(n-1)};
      for(std::size_t lane=0;lane<4&&lane<n;++lane){positions.insert((n-1)*n+lane);positions.insert(n*n-1-lane);positions.insert(2*n+lane);}
      for(auto pos:positions)if(pos<a.count)for(std::size_t b=0;b<patterns.size();++b)
        altered(a,bound,"bitpattern-"+std::to_string(b)+"-position-"+std::to_string(pos),{{pos,patterns[b]}});
      // Earlier dense rejection must never certify a later NaN/Inf, including
      // an invalid element in the same SIMD block after the earliest nonzero.
      for(std::size_t b=12;b<patterns.size();++b){
        altered(a,0,"late-invalid-after-dense-"+std::to_string(b),{{n,1ULL},{n*n-1,patterns[b]}});
        if(n>=7)for(std::size_t lane=1;lane<4;++lane)
          altered(a,0,"same-block-invalid-lane-"+std::to_string(lane)+"-"+std::to_string(b),{{4*n,1ULL},{4*n+lane,patterns[b]}});
      }
    }
  }
}
void maximum(){
  Guarded a(10000);constexpr std::size_t n=10000;
  check(a,128,"maxN-signed-zeros");
  altered(a,128,"maxN-accepted-cap128-tail",{{(n-1)*n+n-129,1ULL},{n*n-1,0x7fefffffffffffffULL}});
  altered(a,128,"maxN-rejected-cap129-tail",{{(n-1)*n+n-130,0x8000000000000001ULL}});
  altered(a,0,"maxN-late-upper-snan-after-dense",{{n,1ULL},{n*n-1,0x7ff0000000000001ULL}});
}
}
int main(){
  if(!__builtin_cpu_supports("avx2")||!__builtin_cpu_supports("fma")){std::cerr<<"CPU AVX2/FMA unavailable\n";return 77;}
  try{
    Environment original;
    small();maximum();
    std::cout<<"{\"status\":\"PASS\",\"cases\":"<<cases<<",\"classifier_calls\":"<<calls<<",\"maxN_calls\":"<<large_calls<<",\"facts_controls\":"<<match_controls
      <<",\"rounding_modes\":4,\"FTZ_DAZ_combinations\":4,\"flag_states\":2,\"all_flags_include_inexact\":true,\"readonly_payload_guarded\":true,\"actual_runtime_fallback_executed\":false}\n";
  }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<" cases_completed="<<cases<<" calls_completed="<<calls<<'\n';return 1;}
}