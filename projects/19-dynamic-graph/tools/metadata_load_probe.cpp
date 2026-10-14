#include "cholesky/runtime.hpp"
#include <bit>
#include <chrono>
#include <iomanip>
#include <iostream>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 const auto count=std::stoull(argv[2]);
 std::uint64_t hash=14695981039346656037ull;
 auto mix=[&](std::uint64_t x){for(int i=0;i<8;++i){hash^=x&255;hash*=1099511628211ull;x>>=8;}};
 const auto first=chol::read_metadata(argv[1]);
 for(const auto* s:{&first.algorithm,&first.arithmetic,&first.dependencies,&first.optimized})for(unsigned char c:*s)mix(c);
 mix(first.slots);mix(first.shape_slot);mix(first.block_slot);mix(first.program.size());
 for(auto x:first.program){mix(static_cast<unsigned>(x.opcode));mix(std::bit_cast<std::uint64_t>(x.argument));}
 std::size_t observed=0;const auto start=std::chrono::steady_clock::now();
 for(std::uint64_t i=0;i<count;++i){const auto m=chol::read_metadata(argv[1]);observed+=m.program.size();}
 const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
 std::cout<<std::setprecision(12)<<"{\"iterations\":"<<count<<",\"milliseconds\":"<<ms<<",\"parsed_hash\":"<<hash<<",\"observed\":"<<observed<<"}\n";
}
