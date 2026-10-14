// Research-only direct old/new path comparison. Neither copy reads witnesses.
#define aicore_detail old_detail
#define ScheduleCvGraph OldScheduleCvGraph
#define AicoreEvaluateMetric OldAicoreEvaluateMetric
#define AicoreLastMetric OldAicoreLastMetric
#include "../batch42/solution.cpp"
#undef aicore_detail
#undef ScheduleCvGraph
#undef AicoreEvaluateMetric
#undef AicoreLastMetric
#include "solution.cpp"
#include "local_json.h"
#include <fstream>
#include <iostream>
#include <sstream>
int main(int argc,char** argv) {
  if(argc!=2)return 2;
  std::ifstream f(argv[1]);std::ostringstream raw;raw<<f.rdbuf();auto doc=local_json::Parser(raw.str()).parse();
  int checked=0,structural=0;
  for(const auto& c:doc.at("cases").list()) {
    const auto& x=c.at("hardware");HardwareInfo h{static_cast<int>(x.at("aic_core_num").integer()),static_cast<int>(x.at("aiv_core_num").integer()),static_cast<int>(x.at("stream_num").integer()),x.at("memory_limit").integer(),x.at("event_record_time").integer(),x.at("event_wait_time").integer()};
    std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(std::move(n));
    }
    old_detail::Graph old_g(h,nodes);aicore_detail::Graph g(h,nodes);
    if(old_detail::strict_fork_join_order(old_g)!=aicore_detail::strict_fork_join_order(g)) {std::cerr<<"Structure emit mismatch: "<<c.at("name").text()<<'\n';return 1;}
    ++structural;
    if(nodes.size()>768)continue;
    for(bool paired:{false,true})for(bool inner:{false,true}) {
      auto before=old_detail::serial_frontier_search(h,old_g,8000000,paired,true,inner);
      auto after=aicore_detail::serial_frontier_search(h,g,8000000,paired,true,inner);
      if(before.order!=after.order || before.work!=after.work || before.failed_states!=after.failed_states || before.exhausted!=after.exhausted) {
        std::cerr<<"Streaming path mismatch: "<<c.at("name").text()<<" paired="<<paired<<" inner="<<inner<<'\n';return 1;
      }
      ++checked;
    }
  }
  std::cout<<checked<<" exact greedy path/work/state/truncation comparisons; structural orders="<<structural<<"\n";
}
