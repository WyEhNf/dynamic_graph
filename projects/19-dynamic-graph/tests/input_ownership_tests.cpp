#include "cholesky/runtime.hpp"
#include <algorithm>
#include <bit>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <utility>
extern "C" int cholesky_reference(const double*,double*,int);
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main(){try{
  // This API test supplies the trusted native contract directly. The real
  // frontend's independent source proof is covered by source_pipeline suites.
  chol::Metadata metadata;metadata.algorithm="ast_vm_v2";metadata.slots=1;
  metadata.optimized="scalar_cholesky_column_dag";metadata.program.push_back({chol::Opcode::Return,0});
  for(unsigned n:{3u,67u,193u}){
    chol::Matrix input{n,std::vector<double>(n*n)};
    for(unsigned i=0;i<n;++i)for(unsigned j=0;j<n;++j)input.values[i*n+j]=i==j?n+2.0:(i>j?0.125:((i+j)%2?-0.0:-17.5));
    const auto original=input.values;
    std::vector<double> reference(n*n,0.0);require(cholesky_reference(input.values.data(),reference.data(),n)==0,"C reference failed");
    for(unsigned threads:{1u,4u}){
      chol::RunMetrics metrics;chol::Options options;options.engine="tiled";options.structure="dense";options.parallel=true;options.threads=threads;options.tile_size=31;options.metrics=&metrics;
      auto read_only=chol::execute(input,metadata,options);
      require(std::memcmp(input.values.data(),original.data(),n*n*sizeof(double))==0,"const API modified input");
      require(!metrics.input_buffer_reused,"const API claimed ownership");
      require(std::memcmp(read_only.values.data(),reference.data(),n*n*sizeof(double))==0,"const API changed local strict C fixture bytes");
      auto owned=input;auto* allocation=owned.values.data();auto result=chol::execute_owned(std::move(owned),metadata,options);
      require(owned.values.empty(),"moved caller retained values");
      require(std::memcmp(result.values.data(),reference.data(),n*n*sizeof(double))==0,"owned API changed local strict C fixture bytes");
#ifdef CHOL_REUSE_INPUT_BUFFER
      require(metrics.input_buffer_reused&&result.values.data()==allocation,"owned allocation was not recycled");
#else
      (void)allocation;require(!metrics.input_buffer_reused,"disabled build recycled input");
#endif
      for(unsigned i=0;i<n;++i)for(unsigned j=i+1;j<n;++j)require(std::bit_cast<std::uint64_t>(result.values[i*n+j])==0,"upper result was not positive zero");
    }
  }
  // Separate structured regression uses the local strict C fixture as an
  // independent arithmetic reference; it is not the official transcribed C.
  for(unsigned n:{3u,129u,193u})for(unsigned width:{0u,1u,7u,32u}) {
    if(width>=n)continue;
    chol::Matrix input{n,std::vector<double>(n*n)};
    for(unsigned i=0;i<n;++i)for(unsigned j=0;j<n;++j)
      input.values[i*n+j]=i==j?n+2.0:(j>i?-17.5:(i-j<=width?0.125:((i+j)%2?-0.0:0.0)));
    const auto original=input.values;
    std::vector<double> reference(n*n,0.0);
    require(cholesky_reference(input.values.data(),reference.data(),n)==0,"structured local C fixture failed");
    chol::RunMetrics metrics;chol::Options options;options.engine="tiled";options.band_limit=width;options.metrics=&metrics;
    auto borrowed=chol::execute(input,metadata,options);
    require(input.values==original&&std::memcmp(input.values.data(),original.data(),n*n*sizeof(double))==0,"structured borrowed input changed");
    require(!metrics.input_buffer_reused,"structured borrowed API claimed ownership");
    require(std::memcmp(borrowed.values.data(),reference.data(),n*n*sizeof(double))==0,"structured borrowed local C bytes changed");
    auto owner=input;auto* allocation=owner.values.data();
    auto result=chol::execute_owned(std::move(owner),metadata,options);
    require(std::memcmp(result.values.data(),reference.data(),n*n*sizeof(double))==0,"structured owned local C bytes changed");
    const bool structured=width<=std::min(width,(n-1)/4)&&(width==0||4*width<n);
    bool expected_reuse=false;
#ifdef CHOL_REUSE_INPUT_BUFFER
    expected_reuse=!structured;
#ifdef CHOL_REUSE_STRUCTURED_INPUT
    expected_reuse=true;
#endif
#endif
    require(metrics.input_buffer_reused==expected_reuse,"structured reuse metric mismatch");
    if(expected_reuse)require(result.values.data()==allocation,"structured allocation identity changed");
    require(metrics.engine==(structured?(width?"banded":"diagonal"):"tiled"),"structured route mismatch");
    for(unsigned i=0;i<n;++i)for(unsigned j=i+1;j<n;++j)
      require(std::bit_cast<std::uint64_t>(result.values[i*n+j])==0,"structured upper result was not positive zero");
  }
  std::cout<<"borrowed bytes immutable; dense/structured ownership identity, local strict C fixture and upper +0 passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
