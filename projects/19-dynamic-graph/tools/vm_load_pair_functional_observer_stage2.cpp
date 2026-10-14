// Functional observation only. Exact accepted core produces every output value.
// No expected output/oracle is read here; later performance uses actual a95 CLI.
#include "cholesky/runtime.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <utility>
namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point start){return std::chrono::duration<double,std::milli>(Clock::now()-start).count();}
std::string quote(const std::string& text){
  std::ostringstream out;out<<'"';
  for(unsigned char c:text){if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<32)out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c)<<std::dec;else out<<c;}
  out<<'"';return out.str();
}
void row(unsigned index,unsigned n,const chol::RunMetrics& m,double compute_ms,const std::string& error){
  std::cout<<std::setprecision(17)<<"{\"kind\":\"matrix\",\"index\":"<<index<<",\"n\":"<<n
    <<",\"error\":"<<quote(error)<<",\"engine\":"<<quote(m.engine)<<",\"backend\":"<<quote(m.vm_backend)
    <<",\"vm_steps\":"<<m.vm_steps<<",\"vm_last_pc\":"<<m.vm_last_pc<<",\"lastpc_applicable\":"<<(m.engine=="vm"?"true":"false")
    <<",\"compute_ms_functional_only\":"<<compute_ms<<",\"vm_prepare_ms\":"<<m.vm_prepare_ms
    <<",\"vm_plan_bytes\":"<<m.vm_plan_bytes<<",\"vm_fusion_plan_ms\":"<<m.vm_fusion_plan_ms
    <<",\"vm_fusion_plan_bytes\":"<<m.vm_fusion_plan_bytes<<",\"vm_fusion_pairs_discovered\":"<<m.vm_fusion_pairs_discovered
    <<",\"vm_fusion_pairs_executed\":"<<m.vm_fusion_pairs_executed<<",\"vm_fusion_status\":"<<quote(m.vm_fusion_status)
    <<",\"vm_budget_work\":"<<m.vm_budget_work<<",\"vm_budget_proof_ms\":"<<m.vm_budget_proof_ms
    <<",\"vm_effective_step_limit\":"<<m.vm_effective_step_limit<<",\"input_validation_ms\":"<<m.input_validation_ms<<"}\n";
}
}
int main(int argc,char** argv){try {
  if(argc!=9)throw std::runtime_error("observer requires metadata input output backend engine block threads scheduler");
  const std::string output_path=argv[3],partial=output_path+".partial";
  if(std::filesystem::exists(output_path)||std::filesystem::exists(partial))throw std::runtime_error("observer refuses to overwrite evidence");
  if(std::filesystem::weakly_canonical(argv[2])==std::filesystem::weakly_canonical(output_path))throw std::runtime_error("input and output paths must differ");
  chol::Options options;options.vm_backend=argv[4];options.engine=argv[5];options.block_size=std::stoul(argv[6]);
  options.threads=std::stoul(argv[7]);options.parallel=std::string(argv[8])=="parallel";
  if(options.vm_backend!="decoded-threaded"&&options.vm_backend!="decoded-threaded-load-pair")throw std::runtime_error("observer backend outside fixed scope");
  if(options.engine!="auto"&&options.engine!="vm")throw std::runtime_error("observer engine outside fixed scope");
  if(!options.block_size||!options.threads||options.threads>256)throw std::runtime_error("invalid observer options");
  if(std::string(argv[8])!="parallel"&&std::string(argv[8])!="serial")throw std::runtime_error("invalid observer scheduler");
  if(options.vm_step_limit!=1000000000ull||options.vm_budget_mode!="fixed"||options.vm_step_limit_explicit)throw std::runtime_error("observer default budget contract changed");
  const auto metadata=chol::read_metadata(argv[1]);
  std::ifstream input(argv[2],std::ios::binary);if(!input)throw std::runtime_error("cannot open input");
  const auto count=chol::read_count(input);
  std::ofstream output(partial,std::ios::binary);if(!output)throw std::runtime_error("cannot open output");
  chol::write_count(output,count);std::uint64_t steps=0;double compute=0;
  for(unsigned index=0;index<count;++index){
    auto matrix=chol::read_matrix(input);const auto n=matrix.n;chol::RunMetrics metrics;options.metrics=&metrics;
    const auto start=Clock::now();
    try {
      auto result=chol::execute_owned(std::move(matrix),metadata,options);const double elapsed=ms(start);
      compute+=elapsed;steps+=metrics.vm_steps;row(index,n,metrics,elapsed,"");
      chol::write_matrix(output,result);
    }catch(const std::exception& e){row(index,n,metrics,ms(start),e.what());throw;}
  }
  chol::ensure_eof(input);output.flush();if(!output)throw std::runtime_error("binary output write failed");output.close();
  std::filesystem::rename(partial,output_path);
  std::cout<<std::setprecision(17)<<"{\"kind\":\"summary\",\"matrices\":"<<count<<",\"vm_steps\":"<<steps
           <<",\"compute_ms_functional_only\":"<<compute<<",\"step_limit_default\":"<<options.vm_step_limit
           <<",\"vm_budget_mode\":"<<quote(options.vm_budget_mode)<<",\"step_limit_explicit\":false}\n";
  return 0;
}catch(const std::exception& e){std::cerr<<"error: "<<e.what()<<'\n';return 1;}}
