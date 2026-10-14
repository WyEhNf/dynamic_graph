#include "../../include/simulator.h"
#include "../batch39/solution.cpp"
#include <iostream>
int main(int argc,char**) {
  HardwareInfo h{8,8,4,INT64_MAX,0,0};
  std::vector<OperatorNode> v{{0,CoreType::AIC,1,1,6000000000000000000LL,6000000000000000000LL,{}}};
  SchedulePlan p{{StreamPlan{{StreamTask{0,{},-1}}}}};
  if(argc>1){aicore_detail::Graph g(h,v);auto r=aicore_detail::evaluate(h,g,p);std::cout<<r.valid<<" "<<r.peak<<"\n";}
  else{auto r=Simulate(h,v,p,INT64_MAX);std::cout<<r.valid<<" "<<r.peak_memory<<"\n";}
}
