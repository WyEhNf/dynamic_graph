// Analysis only. No Matrix instance, read_matrix, execute or VM instruction execution.
#include "cholesky/vm_nested_step_bound.hpp"
#include <algorithm>
#include <charconv>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point start) {return std::chrono::duration<double,std::milli>(Clock::now()-start).count();}
unsigned number(const char* value) {
  std::string_view text(value);unsigned result=0;
  const auto parsed=std::from_chars(text.data(),text.data()+text.size(),result);
  if(parsed.ec!=std::errc{}||parsed.ptr!=text.data()+text.size())throw std::runtime_error("invalid unsigned argument");
  return result;
}
}
int main(int argc,char**argv) {
  try {
    if(argc!=4)throw std::runtime_error("usage: probe metadata N block");
    const auto n=number(argv[2]),block=number(argv[3]);
    if(n<3||n>10000||!block)throw std::runtime_error("probe shape/block out of range");
    const auto read_start=Clock::now();const auto metadata=chol::read_metadata(argv[1]);
    const double read_ms=ms(read_start);
    constexpr std::uint64_t work_limit=250000,fixed_cap=1000000000;
    const auto proof_start=Clock::now();
    const auto first=chol::prove_vm_step_bound(metadata,n,block,work_limit);
    const double first_ms=ms(proof_start);
    auto selected=first;std::uint64_t total_work=first.work;
    const char*selected_stage=first.proved?"first":"none";
    const char*nested_status="first-proved-skip";
    chol::StepBoundProof nested{false,0,0,0,"not-called"};double nested_ms=0;
    bool nested_called=false;
    if(first.work>work_limit) {
      selected={false,0,0,0,"analysis-contract"};total_work=std::min(first.work,work_limit);
      selected_stage="none";nested_status="contract-skip";
    }else if(!first.proved) {
      const auto remaining=work_limit-first.work;
      if(!remaining)nested_status="work-exhausted-skip";
      else {
        nested_called=true;const auto nested_start=Clock::now();
        nested=chol::prove_vm_nested_step_bound(metadata,n,block,remaining);nested_ms=ms(nested_start);
        if(nested.work>remaining) {nested={false,0,0,0,"analysis-contract"};nested_status="unknown";}
        else {
          total_work+=nested.work;nested_status=nested.proved?"proved":"unknown";
          if(nested.proved){selected=nested;selected_stage="nested";}
        }
      }
    }
    const auto effective_cap=selected.proved?std::max(fixed_cap,selected.bound):fixed_cap;
    const double proof_ms=ms(proof_start);
    std::cout<<std::setprecision(17)<<"{\"N\":"<<n<<",\"block\":"<<block
      <<",\"program_instructions\":"<<metadata.program.size()<<",\"metadata_read_ms\":"<<read_ms
      <<",\"proof_ms\":"<<proof_ms<<",\"first_ms\":"<<first_ms<<",\"nested_ms\":"<<nested_ms
      <<",\"dispatch_and_metric_ms\":"<<std::max(0.0,proof_ms-first_ms-nested_ms)
      <<",\"first_proved\":"<<(first.proved?"true":"false")<<",\"first_bound\":"<<first.bound
      <<",\"first_work\":"<<first.work<<",\"first_loops\":"<<first.loops<<",\"first_reason\":"<<std::quoted(first.reason)
      <<",\"nested_called\":"<<(nested_called?"true":"false")<<",\"nested_status\":"<<std::quoted(nested_status)
      <<",\"nested_proved\":"<<(nested.proved?"true":"false")<<",\"nested_bound\":"<<nested.bound
      <<",\"nested_work\":"<<nested.work<<",\"nested_loops\":"<<nested.loops<<",\"nested_reason\":"<<std::quoted(nested.reason)
      <<",\"selected_stage\":"<<std::quoted(selected_stage)<<",\"proved\":"<<(selected.proved?"true":"false")
      <<",\"bound\":"<<selected.bound<<",\"reason\":"<<std::quoted(selected.reason)<<",\"shared_work\":"<<total_work
      <<",\"work_limit\":"<<work_limit<<",\"remaining_after_first\":"<<(first.work<=work_limit?work_limit-first.work:0)
      <<",\"effective_cap\":"<<effective_cap<<",\"matrix_allocations\":0,\"VM_executions\":0,\"native_executions\":0}\n";
    return 0;
  }catch(const std::exception&error){std::cerr<<error.what()<<'\n';return 1;}
}
