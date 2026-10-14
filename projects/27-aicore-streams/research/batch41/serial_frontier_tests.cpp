#include "solution.cpp"
#include "simulator.h"
#include <iostream>
#include <random>

// Independent full subset recurrence; no normalization, transpositions or
// submitted search helper is used to establish the serial optimum.
static int64_t independent_peak(const std::vector<OperatorNode>& nodes) {
  int n=static_cast<int>(nodes.size());unsigned full=(1u<<n)-1;
  std::vector<unsigned> parents(n),children(n);
  for(int i=0;i<n;++i)for(int id:nodes[i].inputs) {
    int p=0;while(nodes[p].id!=id)++p;parents[i]|=1u<<p;children[p]|=1u<<i;
  }
  std::vector<int64_t> dp(full+1,std::numeric_limits<int64_t>::max());dp[0]=0;
  for(unsigned m=0;m<=full;++m)if(dp[m]!=std::numeric_limits<int64_t>::max()) {
    int64_t live=0;
    for(int i=0;i<n;++i)if((m&(1u<<i)) && (!children[i] || (children[i]&~m)))live+=nodes[i].output_memory;
    for(int i=0;i<n;++i)if(!(m&(1u<<i)) && !(parents[i]&~m)) {
      auto next=m|(1u<<i);auto peak=std::max(dp[m],live+nodes[i].workspace_memory+nodes[i].output_memory);
      dp[next]=std::min(dp[next],peak);
    }
  }
  return dp[full];
}
int main() {
  int cases=0;
  for(unsigned seed=0;seed<160;++seed) {
    std::mt19937 rng(20261011+seed);int n=6+seed%6;
    std::vector<OperatorNode> nodes;
    for(int i=0;i<n;++i) {
      std::vector<int> parents;
      for(int p=0;p<i;++p)if(rng()%100<10+seed%65)parents.push_back(100003+37*p);
      nodes.push_back({100003+37*i,rng()%2?CoreType::AIC:CoreType::AIV,1,1+static_cast<int64_t>(rng()%100),static_cast<int64_t>(rng()%20),seed%5==0?0:static_cast<int64_t>(rng()%25),parents});
    }
    std::shuffle(nodes.begin(),nodes.end(),rng);auto best=independent_peak(nodes);
    for(int64_t capacity:{std::max<int64_t>(0,best-1),best,best+static_cast<int64_t>(rng()%20)})for(bool inside:{false,true}) {
      HardwareInfo h{8,8,4,capacity,seed%3==0?1000000:2,seed%3==1?0:3};
      aicore_detail::Graph g(h,nodes);
      auto found=aicore_detail::serial_frontier_search(h,g,20000000,true,false,inside);
      if(found.exhausted || (found.order.size()==nodes.size())!=(capacity>=best)) {
        std::cerr<<"Feasibility mismatch seed="<<seed<<" capacity="<<capacity<<" best="<<best<<'\n';return 1;
      }
      if(!found.order.empty()) {
        std::vector<int> owner(n,0);auto plan=aicore_detail::assemble(g,found.order,owner,1,0);
        auto sim=Simulate(h,nodes,plan,1000000000);
        if(!sim.valid || !sim.meets_deadline || sim.peak_memory>capacity) {
          std::cerr<<"Independent simulation rejected seed="<<seed<<": "<<sim.error<<'\n';return 1;
        }
      }
      ++cases;
    }
    HardwareInfo h{8,8,4,best,2,3};aicore_detail::Graph g(h,nodes);
    auto stopped=aicore_detail::serial_frontier_search(h,g,0);
    if(!stopped.exhausted || !stopped.order.empty() || stopped.failed_states){std::cerr<<"Interrupted state was misclassified\n";return 1;}
    ++cases;
  }
  std::cout<<cases<<" serial-frontier checks; 960 independently optimized capacities (outer/inner normalization) plus 160 budget controls\n";
}
