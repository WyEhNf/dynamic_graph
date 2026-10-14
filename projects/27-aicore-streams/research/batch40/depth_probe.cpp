#include "solution.cpp"
#include <iostream>
int main() {
  // Feasible original graph: 1000 independent sinks, sum output1000 <=1001.
  // The direct research helper must truncate its large-graph native stack
  // safely, not mistake truncation for proven infeasibility or overflow.
  std::vector<OperatorNode> nodes;
  for(int i=0;i<1000;++i)nodes.push_back({100003+i*37,CoreType::AIC,1,1,0,1,{}});
  HardwareInfo h{8,8,8,1001,0,0};aicore_detail::Graph g(h,nodes);
  auto r=aicore_detail::serial_frontier_search(h,g,8000000,false,true,false,2048);
  if(!r.order.empty() || !r.exhausted || r.failed_states || r.work>=8000000)return 1;
  std::cout<<"Large-graph depth cap truncates safely at work="<<r.work<<", feasible witness remains possible\n";
}
