// R57 control only; compile separately, leave default test targets unchanged.
#include "simulator.h"
#include "../research/batch57/solution.cpp"
#include <iostream>
void require(bool value,const char* reason){if(!value)throw std::runtime_error(reason);}
int main(){try {
  HardwareInfo h{1,1,1,10,0,0};
  // Emitting unrelated sink 1 first would obstruct future workspace-heavy 3.
  std::vector<OperatorNode> nodes{{1,CoreType::AIC,1,1,0,6,{}},
    {2,CoreType::AIC,1,1,0,1,{}},{3,CoreType::AIC,1,1,9,0,{2}}};
  aicore_detail::Graph g(h,nodes);int controls=0;
  for(int64_t budget:{1,2,10,32,64,128,1000,2000000}) {
    auto result=aicore_detail::necessary_prefix_search(h,g,budget);
    require(result.work<=budget,"budget exceeded");
    if(result.order.size()==nodes.size()) {
      auto plan=aicore_detail::assemble(g,result.order,std::vector<int>(g.n,0),1,0);
      auto actual=Simulate(h,nodes,plan,1000);
      require(actual.valid&&actual.meets_deadline,"partial search produced invalid full plan");
      require(result.order.back()==0,"future target obstruction was not avoided");
    }else require(result.order.empty(),"incomplete prefix exposed as candidate");
    ++controls;
  }
  auto complete=aicore_detail::necessary_prefix_search(h,g);
  require(complete.order.size()==3&&complete.prunes>0,"necessary pruning positive control failed");
  for(int i=0;i<513;++i)nodes.push_back({100+i,CoreType::AIC,1,1,0,0,{}});
  aicore_detail::Graph large(h,nodes);
  auto skipped=aicore_detail::necessary_prefix_search(h,large);
  require(skipped.order.empty()&&skipped.work==0&&!skipped.intrinsic_blocked,"unsupported size is not infeasibility");
  std::cout<<"{\"passed\":true,\"budget_controls\":"<<controls<<",\"necessary_pruning_positive\":true,\"size_limit_unknown\":true}\n";
  return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
