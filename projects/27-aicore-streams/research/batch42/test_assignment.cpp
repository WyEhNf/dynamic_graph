// Standalone translation unit also checks that the submission remains usable
// with only problem.h and the standard library. The reference is the frozen
// original per-parent recurrence, independent of grouped maxima/counts.
#include "solution.cpp"
#include <iostream>
#include <random>
static std::vector<int> reference(const HardwareInfo& h,const aicore_detail::Graph& g,const std::vector<int>& order,int streams,int affinity) {
  using I=int64_t;std::vector<I> available(streams),finish(g.n);std::vector<int> owner(g.n,-1),type(streams,-1);
  for(int i:order) {
    I least=std::numeric_limits<I>::max();int choice=0;
    for(int s=0;s<streams;++s) {
      I start=available[s],waits=0;
      for(int p:g.in[i]){start=std::max(start,finish[p]+(owner[p]==s?0:h.event_record_time));waits+=(owner[p]!=s);}
      I end=start+waits*h.event_wait_time+g.v[i].exec_time;
      if(affinity && type[s]>=0 && type[s]!=static_cast<int>(g.v[i].core_type))end+=h.event_record_time+h.event_wait_time;
      if(end<least){least=end;choice=s;}
    }
    owner[i]=choice;available[choice]=finish[i]=least;type[choice]=static_cast<int>(g.v[i].core_type);
  }
  return owner;
}
int main() {
  int checks=0;
  for(unsigned seed:{11u,17u,23u,20261023u})for(int n:{32,64,128})for(int event:{0,1,1000000}) {
    std::mt19937 rng(seed+n);std::vector<OperatorNode> nodes;std::vector<int> ids(n);for(int i=0;i<n;++i)ids[i]=1000000000+37*i;std::shuffle(ids.begin(),ids.end(),rng);
    for(int i=0;i<n;++i){std::vector<int> candidates;for(int p=0;p<i;++p)candidates.push_back(p);std::shuffle(candidates.begin(),candidates.end(),rng);candidates.resize(std::min<int>(i,1+rng()%24));std::vector<int> parents;for(int p:candidates)parents.push_back(ids[p]);nodes.push_back({ids[i],rng()%2?CoreType::AIC:CoreType::AIV,1,seed==11?7:1+static_cast<int64_t>(rng()%1000000000),3,2,parents});}
    std::shuffle(nodes.begin(),nodes.end(),rng);HardwareInfo h{8,8,16,1000000,event,event};aicore_detail::Graph g(h,nodes);std::vector<int> order;for(int id:ids)order.push_back(g.index.at(id));
    for(int streams:{1,4,8,16})for(int affinity:{0,1}){if(aicore_detail::assign(h,g,order,streams,affinity)!=reference(h,g,order,streams,affinity)){std::cerr<<"Assignment mismatch seed="<<seed<<" n="<<n<<" event="<<event<<" streams="<<streams<<'\n';return 1;}++checks;}
  }
  int owner_checks=0;
  for(int width:{2,8})for(bool cycle:{false,true}) {
    HardwareInfo h{8,8,4,1000,3,3};
    std::vector<OperatorNode> nodes{{700,CoreType::AIC,1,1000,0,10,{}},
      {901,CoreType::AIV,1,100,100,0,{700}},
      {101,CoreType::AIC,1,1,0,10,cycle?std::vector<int>{901}:std::vector<int>{}},
      {503,CoreType::AIV,1,100,100,0,{700,101}},
      {307,CoreType::AIV,1,100,100,0,{101,700}}};
    for(int k=2;k<width;++k)nodes.push_back({1100+k*17,CoreType::AIV,1,100,100,0,{101,700}});
    aicore_detail::Graph g(h,nodes);
    if(width==2 && !cycle)for(int mode:{30,31,32}) {
      if(!aicore_detail::bundle_ordering(h,g,mode).empty()){std::cerr<<"Redundant narrow grouping was retried\n";return 1;}
      ++owner_checks;
    }
    for(int score=0;score<3;++score) {
      int mode=(width==2?27:30)+score;
      auto order=aicore_detail::bundle_ordering(h,g,mode);
      if(cycle){if(!order.empty()){std::cerr<<"Cyclic ordering preference was retained\n";return 1;}}
      else {
        if(order.size()!=nodes.size()){std::cerr<<"Acyclic owner fixture failed\n";return 1;}
        std::vector<int> position(g.n);for(int k=0;k<g.n;++k)position[order[k]]=k;
        for(int i=0;i<g.n;++i)for(int p:g.in[i])if(position[p]>=position[i]){std::cerr<<"Original precedence violated\n";return 1;}
        if(position[g.index.at(503)]>=position[g.index.at(901)] || position[g.index.at(307)]>=position[g.index.at(901)]){std::cerr<<"Shared owner was not completed first\n";return 1;}
      }
      ++owner_checks;
    }
    if(width==8) {
      if(!cycle)for(int mode:{33,34,35}) {
        if(!aicore_detail::bundle_ordering(h,g,mode).empty()){std::cerr<<"Never-changing shortlist was retried\n";return 1;}
        ++owner_checks;
      }
      while(nodes.size()<513){int k=static_cast<int>(nodes.size());nodes.push_back({1000000+k*23,CoreType::AIC,1,1,0,0,{}});}
      aicore_detail::Graph large(h,nodes);
      for(int mode:{33,34,35}) {
        auto order=aicore_detail::bundle_ordering(h,large,mode);
        if(cycle){if(!order.empty()){std::cerr<<"Large cyclic ordering preference was retained\n";return 1;}}
        else {
          if(order.size()!=nodes.size()){std::cerr<<"Aggregate large fixture failed\n";return 1;}
          std::vector<int> position(large.n,-1);
          for(int k=0;k<large.n;++k){if(order[k]<0 || order[k]>=large.n || position[order[k]]>=0){std::cerr<<"Large order is not a permutation\n";return 1;}position[order[k]]=k;}
          for(int i=0;i<large.n;++i)for(int p:large.in[i])if(position[p]>=position[i]){std::cerr<<"Aggregate order violates original precedence\n";return 1;}
        }
        ++owner_checks;
      }
    }
  }
  int projection_checks=0;
  for(int sinks:{73,80,144}) {
    HardwareInfo h{8,8,4,110,1000000,1000000};std::vector<OperatorNode> nodes;
    for(int first=0;first<sinks;first+=8) {
      int source=10000+first*31;nodes.push_back({source,CoreType::AIC,1,1,0,10,{}});
      for(int k=first;k<std::min(first+8,sinks);++k)nodes.push_back({200000+k*29,CoreType::AIV,1,100,100,0,{source}});
    }
    aicore_detail::Graph g(h,nodes);
    if(!aicore_detail::sink_projection_order(h,g,true).empty()){std::cerr<<"Legacy projection unexpectedly accepted >72 sinks\n";return 1;}
    auto order=aicore_detail::sink_projection_order(h,g,true,true);
    if(order.size()!=nodes.size()){std::cerr<<"Wide closure fixture failed\n";return 1;}
    auto e=aicore_detail::serial_evaluate(h,g,order);
    if(!e.valid || e.peak!=110 || e.time!=100*sinks+(sinks+7)/8){std::cerr<<"Wide projection violates analytic T/peak\n";return 1;}
    ++projection_checks;
  }
  int resource_checks=0;
  auto bound_check=[&](HardwareInfo h,std::vector<OperatorNode> nodes,int64_t time,int64_t peak=-1) {
    aicore_detail::Graph g(h,nodes);auto b=aicore_detail::lower_bounds(h,g);
    if(b.time!=time || (peak>=0 && b.memory!=peak)){std::cerr<<"Necessary resource bound differs from literal expectation\n";return false;}
    ++resource_checks;return true;
  };
  HardwareInfo core_h{8,8,4,100,0,0};
  if(!bound_check(core_h,{{17,CoreType::AIC,5,3,0,0,{}},{93,CoreType::AIC,5,7,0,0,{}},{41,CoreType::AIC,5,11,0,0,{}}},21,0))return 1;
  if(!bound_check(core_h,{{17,CoreType::AIC,5,3,0,0,{}},{93,CoreType::AIC,5,7,0,0,{}},{41,CoreType::AIV,5,11,0,0,{}},{29,CoreType::AIV,5,13,0,0,{}}},24,0))return 1;
  if(!bound_check(core_h,{{17,CoreType::AIC,4,3,50,0,{}},{93,CoreType::AIC,4,7,50,0,{}}},7,50))return 1;
  HardwareInfo memory_h{128,0,4,100,0,0};
  if(!bound_check(memory_h,{{17,CoreType::AIC,1,3,60,0,{}},{93,CoreType::AIC,1,7,60,0,{}},{41,CoreType::AIC,1,11,60,0,{}}},21,60))return 1;
  std::vector<OperatorNode> output_heavy{{17,CoreType::AIC,1,3,40,20,{}},{93,CoreType::AIC,1,7,40,20,{}},{41,CoreType::AIC,1,11,40,20,{}}};
  if(!bound_check(memory_h,output_heavy,21,100))return 1;
  ScheduleCvGraph(memory_h,output_heavy,21);
  if(AicoreLastMetric(9)!=1 || AicoreLastMetric(2)!=21 || AicoreLastMetric(3)!=100){std::cerr<<"Output-heavy analytic certificate invalid\n";return 1;}
  memory_h.memory_limit=1000000000;
  if(!bound_check(memory_h,{{17,CoreType::AIC,1,1000000000,600000000,0,{}},{93,CoreType::AIC,1,1000000000,600000000,0,{}},{41,CoreType::AIC,1,1000000000,600000000,0,{}}},3000000000LL,600000000))return 1;
  std::cout<<checks<<" frozen-recurrence comparisons, "<<owner_checks<<" ordering checks, "<<projection_checks<<" wide closure checks, and "<<resource_checks<<" resource bound cases passed\n";return 0;
}
