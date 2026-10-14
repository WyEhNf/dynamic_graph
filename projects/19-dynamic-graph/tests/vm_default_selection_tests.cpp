#include "cholesky/runtime.hpp"
#include <bit>
#include <iostream>
#include <stdexcept>
namespace {
void require(bool good,const char* text){if(!good)throw std::runtime_error(text);}
const char* effective_default(){
#ifdef CHOL_HAVE_THREADED_DISPATCH
  return "decoded-threaded";
#elif defined(CHOL_THREADED_VM)
  return "decoded-fallback";
#elif defined(CHOL_PREPARED_VM)
  return "decoded";
#else
  return "legacy";
#endif
}
}
int main(){try {
  using O=chol::Opcode;
  chol::Metadata m;m.algorithm="ast_vm_v2";m.arithmetic="fp64_source_order_no_implicit_fma";m.dependencies="source_control_flow";m.slots=2;
  m.program={{O::Const,0},{O::Const,-0.0},{O::Write,1},{O::Const,0},{O::Return,0},{O::Load,-1}};
  chol::Matrix input{3,std::vector<double>(9,1.0)};
  chol::Options options;require(options.vm_backend=="auto"&&options.vm_step_limit==1000000000ull,"default backend/budget contract changed");options.simd="portable";
  const char* modes[]={"auto","legacy"
#ifdef CHOL_PREPARED_VM
    ,"decoded","decoded-tos2"
#endif
#ifdef CHOL_THREADED_VM
    ,"decoded-threaded"
#endif
  };
  unsigned tested=0;
  for(const auto* mode:modes) {
    options.vm_backend=mode;chol::RunMetrics metrics;options.metrics=&metrics;options.vm_step_limit=1000000000ull;
    const auto result=chol::execute(input,m,options);
    const std::string expected=std::string(mode)=="auto"?effective_default():std::string(mode)=="decoded-threaded"?effective_default():mode;
    require(metrics.vm_backend==expected&&metrics.engine=="vm","default/override/fallback engine differs");
    require(metrics.vm_steps==5&&metrics.vm_last_pc==4,"steps/PC changed");
    require(std::bit_cast<std::uint64_t>(result.values[0])==UINT64_C(0x8000000000000000),"negative zero changed");
    options.vm_step_limit=3;std::string error;
    try{(void)chol::execute(input,m,options);}catch(const std::exception& e){error=e.what();}
    require(error=="VM instruction limit exceeded"&&metrics.vm_steps==4&&metrics.vm_last_pc==3&&metrics.vm_backend==expected,"per-op limit/effective error backend changed");
    ++tested;
  }
  std::cout<<"{\"passed\":true,\"default\":\""<<effective_default()<<"\",\"override_modes\":"<<tested<<",\"default_step_limit\":1000000000}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
