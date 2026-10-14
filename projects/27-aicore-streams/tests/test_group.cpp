#include "../solution/solution.cpp"
#include "local_json.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace aicore_detail;
ProfileInteger decimal48(const std::string& s) {
  ProfileInteger r;for(char c:s){auto doubled=r;doubled+=r;auto eight=doubled;eight+=eight;eight+=eight;r=doubled;r+=eight;r+=ProfileInteger(c-'0');}return r;
}
int main(int argc,char** argv) {
  if(argc!=2)return 2;std::ifstream f(argv[1]);std::ostringstream raw;raw<<f.rdbuf();auto doc=local_json::Parser(raw.str()).parse();int cases=0,requests=0;
  for(const auto& c:doc.at("cases").list()) {
    HardwareInfo h{8,8,4,c.at("hardware").at("memory_limit").integer(),0,0};std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(std::move(n));
    }
    Graph g(h,nodes);auto shape=workspace_projection(g);
    auto ids=[&](const local_json::Value& a){std::vector<int> r;for(const auto& id:a.list())r.push_back(g.index.at(static_cast<int>(id.integer())));return r;};
    I work=0;bool exhausted=false;auto groups=direct_consumer_groups(g,shape,work,16000000,exhausted);
    const auto& gold_groups=c.at("groups").list();
    if(exhausted || groups.size()!=gold_groups.size()){std::cerr<<"Group count "<<c.at("name").text()<<'\n';return 1;}
    for(size_t q=0;q<groups.size();++q)if(groups[q].first!=ids(gold_groups[q].at("members")) || !(ProfileInteger(groups[q].second)==decimal48(gold_groups[q].at("weight").text()))){std::cerr<<"Group recognition\n";return 1;}
    // Charged-work boundary must abort, never return a partial group set as
    // if it were complete. No assumption about cost-free preprocessing.
    if(work){I limited=0;bool stopped=false;auto truncated=direct_consumer_groups(g,shape,limited,0,stopped);if(!stopped || !truncated.empty())return 1;}
    for(const auto& request:c.at("requests").list()) {
      auto moved=move_consumer_group(ids(request.at("permutation")),ids(request.at("members")),static_cast<int>(request.at("pivot").integer()));
      if(moved!=ids(request.at("moved"))){std::cerr<<"Stable boundary insertion\n";return 1;}
      auto actual=projection_profile(h,g,shape,moved);const auto& gold=request.at("gold");
      if(actual.order!=ids(gold.at("order")) || actual.permutation!=ids(gold.at("permutation")) || !(actual.peak==decimal48(gold.at("peak").text())) || !(actual.area==decimal48(gold.at("area").text())) || !(actual.excess==decimal48(gold.at("excess").text())) || actual.critical!=gold.at("critical").integer()){std::cerr<<"Normalized profile "<<c.at("name").text()<<'\n';return 1;}
      auto exact=serial_evaluate(h,g,actual.order);if(exact.valid!=(actual.excess==ProfileInteger()))return 1;++requests;
    }
    ++cases;
  }
  std::cout<<cases<<" recognition controls / "<<requests<<" group moves: independent bigint passed\n";
}
