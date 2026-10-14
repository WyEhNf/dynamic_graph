#include "solution.cpp"
#include "local_json.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace aicore_detail;
ProfileInteger decimal(const std::string& s) {
  ProfileInteger r;for(char c:s){ProfileInteger doubled=r;doubled+=r;ProfileInteger eight=doubled;eight+=eight;eight+=eight;r=doubled;r+=eight;r+=ProfileInteger(c-'0');}return r;
}
int main(int argc,char** argv) {
  if(argc!=2)return 2;std::ifstream f(argv[1]);std::ostringstream raw;raw<<f.rdbuf();auto doc=local_json::Parser(raw.str()).parse();
  int count=0,searches=0;std::set<std::vector<int>> searched_graphs;
  for(const auto& c:doc.at("cases").list()) {
    const auto& x=c.at("hardware");HardwareInfo h{static_cast<int>(x.at("aic_core_num").integer()),static_cast<int>(x.at("aiv_core_num").integer()),static_cast<int>(x.at("stream_num").integer()),x.at("memory_limit").integer(),x.at("event_record_time").integer(),x.at("event_wait_time").integer()};
    std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(std::move(n));
    }
    Graph g(h,nodes);auto shape=shallow_shape(g);if(shape.consumers.empty()){std::cerr<<"Recognition rejected "<<c.at("name").text()<<'\n';return 1;}
    std::vector<int> perm;for(const auto& id:c.at("permutation").list())perm.push_back(g.index.at(static_cast<int>(id.integer())));
    auto actual=shallow_profile(h,g,shape,perm);const auto& gold=c.at("gold");
    std::vector<int> order;for(const auto& id:gold.at("order").list())order.push_back(g.index.at(static_cast<int>(id.integer())));
    if(actual.order!=order || !(actual.peak==decimal(gold.at("peak").text())) || !(actual.area==decimal(gold.at("area").text())) || !(actual.excess==decimal(gold.at("excess").text())) || actual.critical!=gold.at("critical").integer()) {std::cerr<<"Profile mismatch "<<c.at("name").text()<<'\n';return 1;}
    auto exact=serial_evaluate(h,g,actual.order);if(exact.valid!=(actual.excess==ProfileInteger())){std::cerr<<"Capacity mismatch\n";return 1;}
    std::vector<int> ids;for(const auto& node:nodes)ids.push_back(node.id);
    if(searched_graphs.insert(ids).second) {
      auto searched=shallow_memory_search(h,g,100000);
      if(!searched.order.empty() && !serial_evaluate(h,g,searched.order).valid){std::cerr<<"Search returned invalid memory traversal\n";return 1;}
      ++searches;
    }
    ++count;
  }
  std::cout<<count<<" independent Python-bigint profiles/order/capacity controls and "<<searches<<" bounded search validity checks passed\n";
}
