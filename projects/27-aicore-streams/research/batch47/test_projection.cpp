#include "solution.cpp"
#include "local_json.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace aicore_detail;
ProfileInteger decimal45(const std::string& s) {
  ProfileInteger r;for(char c:s){auto doubled=r;doubled+=r;auto eight=doubled;eight+=eight;eight+=eight;r=doubled;r+=eight;r+=ProfileInteger(c-'0');}return r;
}
int main(int argc,char** argv) {
  if(argc!=2)return 2;std::ifstream f(argv[1]);std::ostringstream raw;raw<<f.rdbuf();auto doc=local_json::Parser(raw.str()).parse();int count=0,search_count=0;std::ofstream search_output("reports/projection-search-orders-batch47.json");search_output<<"{\"cases\":[";
  for(const auto& c:doc.at("cases").list()) {
    const auto& x=c.at("hardware");HardwareInfo h{8,8,4,x.at("memory_limit").integer(),0,0};std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(std::move(n));
    }
    Graph g(h,nodes);auto shape=workspace_projection(g);std::vector<int> desired,order,normalized,targets;
    const auto& gold=c.at("gold");for(const auto& id:c.at("desired").list())desired.push_back(g.index.at(static_cast<int>(id.integer())));
    for(const auto& id:gold.at("order").list())order.push_back(g.index.at(static_cast<int>(id.integer())));
    for(const auto& id:gold.at("permutation").list())normalized.push_back(g.index.at(static_cast<int>(id.integer())));
    for(const auto& id:gold.at("targets").list())targets.push_back(g.index.at(static_cast<int>(id.integer())));
    if(shape.targets!=targets){std::cerr<<"Recognition mismatch\n";return 1;}
    auto actual=projection_profile(h,g,shape,desired);
    if(actual.order!=order || actual.permutation!=normalized || !(actual.peak==decimal45(gold.at("peak").text())) || !(actual.area==decimal45(gold.at("area").text())) || !(actual.excess==decimal45(gold.at("excess").text())) || actual.critical!=gold.at("critical").integer()) {std::cerr<<"Profile mismatch "<<c.at("name").text()<<'\n';return 1;}
    auto exact=serial_evaluate(h,g,actual.order);if(exact.valid!=(actual.excess==ProfileInteger())){std::cerr<<"Capacity mismatch\n";return 1;}++count;
    auto searched=projection_memory_search(h,g,100000);
    if(!searched.order.empty()) {
      if(!serial_evaluate(h,g,searched.order).valid){std::cerr<<"Invalid bounded search order\n";return 1;}
      if(search_count++)search_output<<',';
      search_output<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"order\":[";
      for(size_t q=0;q<searched.order.size();++q){if(q)search_output<<',';search_output<<g.v[searched.order[q]].id;}
      search_output<<"]}";
    }
  }
  search_output<<"]}";std::cout<<search_count<<" bounded-search orders saved; ";
  std::cout<<count<<" independent full-ancestor/live-set bigint controls passed\n";
}
