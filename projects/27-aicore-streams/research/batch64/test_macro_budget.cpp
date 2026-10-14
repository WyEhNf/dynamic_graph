#include "solution.cpp"
#include "simulator.h"
#include <iostream>
int main() {
  HardwareInfo h{};h.aic_core_num=h.aiv_core_num=h.stream_num=1;h.memory_limit=25;
  std::vector<OperatorNode> nodes(5);
  for(int i=0;i<5;++i){nodes[i].id=100+i*13;nodes[i].core_type=CoreType::AIC;nodes[i].core_num=1;nodes[i].exec_time=1;}
  for(int i=0;i<3;++i)nodes[i].output_memory=6;
  nodes[3].inputs={100,113};nodes[3].workspace_memory=10;
  nodes[4].inputs={113,126};nodes[4].workspace_memory=12;
  aicore_detail::Graph graph(h,nodes);int tests=0,successes=0;
  for(int64_t limit:{0LL,1LL,2LL,10LL,64LL,100LL,256LL,1024LL,16000000LL,160000000LL}) {
    auto result=aicore_detail::macro_prefix_search(h,graph,limit);
    if(result.work<0 || result.work>limit)return 1;
    if(!result.order.empty()) {
      auto plan=aicore_detail::assemble(graph,result.order,std::vector<int>(nodes.size(),0),1,0);
      auto sim=Simulate(h,nodes,plan,100);if(!sim.valid || !sim.meets_deadline)return 2;++successes;
    }
    ++tests;
  }
  if(successes<3)return 3;
  auto no_work=aicore_detail::macro_prefix_search(h,graph,0);if(no_work.work || !no_work.order.empty())return 4;
  std::cout<<tests<<" budget bounds, zero budget, and independent simulator pass; valid "<<successes<<"\n";
}
