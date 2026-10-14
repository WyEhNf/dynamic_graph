// Research-only diagnostics; never reads witness_plan and never submitted.
#include "../solution/solution.cpp"
#include "local_json.h"
#include "simulator.h"
#include <fstream>
#include <iostream>
#include <sstream>
int main(int argc,char** argv) {
  if(argc!=4)return 2;
  std::ifstream file(argv[1]);std::ostringstream raw;raw<<file.rdbuf();
  auto doc=local_json::Parser(raw.str()).parse();std::ofstream out(argv[2]);
  int64_t limit=std::stoll(argv[3]);out<<"{\"cases\":[";bool first=true;
  for(const auto& c:doc.at("cases").list()) {
    const auto& x=c.at("hardware");HardwareInfo h{static_cast<int>(x.at("aic_core_num").integer()),static_cast<int>(x.at("aiv_core_num").integer()),static_cast<int>(x.at("stream_num").integer()),x.at("memory_limit").integer(),x.at("event_record_time").integer(),x.at("event_wait_time").integer()};
    std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(std::move(n));
    }
    aicore_detail::Graph g(h,nodes);auto begin=std::chrono::steady_clock::now();
    auto r=aicore_detail::serial_frontier_search(h,g,limit,true,true);
    auto us=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count();
    SimulationResult sim;if(r.order.size()==nodes.size())sim=Simulate(h,nodes,aicore_detail::assemble(g,r.order,std::vector<int>(g.n,0),1,0),c.at("deadline_us").integer());
    if(!first)out<<',';first=false;
    out<<"{\"name\":\""<<c.at("name").text()<<"\",\"n\":"<<g.n<<",\"work\":"<<r.work<<",\"failed_states\":"<<r.failed_states<<",\"exhausted\":"<<(r.exhausted?"true":"false")<<",\"found\":"<<(r.order.size()==nodes.size()?"true":"false")<<",\"valid\":"<<(sim.valid?"true":"false")<<",\"deadline\":"<<(sim.meets_deadline?"true":"false")<<",\"peak\":"<<sim.peak_memory<<",\"micros\":"<<us<<'}';
  }
  out<<"]}\n";
}
