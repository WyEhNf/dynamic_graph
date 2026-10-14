#include "samples.h"
#include "candidate_search.h"
#include "simulator.h"
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  bool reference=argc>1 && std::string(argv[1])=="--reference";
  auto hw=SampleHardware(); auto nodes=SampleGraph();
  auto searched=SelectFeasibleCandidate(hw,nodes,400);
  if(!reference && !searched.plan) {
    std::cerr<<searched.simulation.error<<'\n'; return 1;
  }
  auto plan=reference?SamplePlan():*searched.plan;
  auto r=Simulate(hw,nodes,plan,400);
  std::cout << "{\"sample\":1,\"mode\":\""<<(reference?"official_reference":"baseline")
            <<"\",\"valid\":"<<(r.valid?"true":"false")
            <<",\"meets_deadline\":"<<(r.meets_deadline?"true":"false")
            <<",\"makespan\":"<<r.makespan<<",\"peak_memory\":"<<r.peak_memory
            <<",\"error\":\""<<r.error<<"\"}\n";
  for(size_t s=0;s<plan.streams.size();++s) {
    std::cout << "stream "<<s<<":";
    for(const auto& t:plan.streams[s].tasks) std::cout <<' '<<t.op_id;
    std::cout<<'\n';
  }
  return r.valid && r.meets_deadline ? 0:1;
}
