#include "samples.h"
#include "simulator.h"
#include "solver_metrics.h"
#include "local_json.h"
#include <iostream>
#include <algorithm>
#include <random>
#include <stdexcept>
#include <limits>
#include <tuple>
namespace aicore_detail { int64_t scaled_priority(int64_t,int,int); }
static int checks=0;
static void compare(const HardwareInfo& h,const std::vector<OperatorNode>& n,const SchedulePlan& p,int64_t deadline=1000000){
  auto r=Simulate(h,n,p,deadline);
  if((AicoreEvaluateMetric(h,n,p,0)==1)!=r.valid)throw std::runtime_error("validity disagreement "+std::to_string(checks));
  if(r.valid && (AicoreEvaluateMetric(h,n,p,1)!=r.makespan || AicoreEvaluateMetric(h,n,p,2)!=r.peak_memory))throw std::runtime_error("metric disagreement");
  ++checks;
}
int main(){
  try {
    const auto maximum=std::numeric_limits<int64_t>::max();
    for(const auto& c:std::vector<std::tuple<int64_t,int,int,int64_t>>{{1000000000000LL,128,3,42666666666666LL},{maximum-1,2,2,maximum-1},{maximum,2147483647,128,maximum},{maximum,2,3,6148914691236517204LL}}) {
      if(aicore_detail::scaled_priority(std::get<0>(c),std::get<1>(c),std::get<2>(c))!=std::get<3>(c))throw std::runtime_error("Priority integer overflow/rounding boundary");
      ++checks;
    }
    auto h=SampleHardware();auto n=SampleGraph();auto p=SamplePlan();compare(h,n,p);
    auto x=p;x.streams[0].tasks.back().wait_before={};compare(h,n,x);
    x=p;x.streams[0].tasks.back().wait_before={1,1};compare(h,n,x);
    x=p;x.streams[0].tasks.back().wait_before={-1};compare(h,n,x);
    x=p;x.streams[0].tasks[0].record_after=0;compare(h,n,x);
    x=p;x.streams[0].tasks[0].record_after=-2;compare(h,n,x);
    x=p;x.streams[0].tasks[0].record_after=99;compare(h,n,x);
    x=p;x.streams[0].tasks[1].wait_before={0};compare(h,n,x);
    x=p;x.streams[0].tasks.push_back({0,{},-1});compare(h,n,x);
    x=p;x.streams[0].tasks.erase(x.streams[0].tasks.begin());compare(h,n,x);
    x=p;x.streams[0].tasks[0].op_id=999;compare(h,n,x);
    x=p;std::swap(x.streams[0].tasks[0],x.streams[0].tasks[1]);compare(h,n,x);
    x=p;for(auto& s:x.streams)for(auto& t:s.tasks){if(t.record_after>=0)t.record_after+=1000000000;for(auto& e:t.wait_before)e+=1000000000;}
    x.streams.insert(x.streams.begin(),StreamPlan{});x.streams.push_back(StreamPlan{});compare(h,n,x);
    auto zero=h;zero.event_wait_time=zero.event_record_time=0;compare(zero,n,p);
    auto narrow=h;narrow.memory_limit=1;compare(narrow,n,p);
    auto nodes=n;nodes[0].inputs={5};compare(h,nodes,p);
    nodes=n;nodes[0].core_num=129;compare(h,nodes,p);
    nodes=n;nodes[1].inputs={0,0};compare(h,nodes,p);
    HardwareInfo tiny{1,1,2,100,0,0};
    std::vector<OperatorNode> empty;
    SchedulePlan empties;empties.streams.resize(8);compare(tiny,empty,empties);
    std::vector<OperatorNode> cycle{{10,CoreType::AIC,1,1,0,0,{}},{20,CoreType::AIV,1,1,0,0,{}}};
    SchedulePlan dead{{{{{10,{2},1}}},{{{20,{1},2}}}}};compare(tiny,cycle,dead);
    // Metamorphic checks exercise dense submission events, arbitrary external
    // events, compressed stream IDs, row order, and identifier independence.
    std::mt19937 rng(20261011);
    for(int round=0;round<80;++round) {
      int size=1+static_cast<int>(rng()%50);std::vector<OperatorNode> graph;
      for(int i=0;i<size;++i) {
        OperatorNode v{1000000+i*53,(rng()%2)?CoreType::AIC:CoreType::AIV,1+static_cast<int>(rng()%8),1+static_cast<int64_t>(rng()%100),static_cast<int64_t>(rng()%51),static_cast<int64_t>(rng()%21),{}};
        for(int j=0;j<i;++j)if(rng()%11==0)v.inputs.push_back(graph[j].id);graph.push_back(v);
      }
      HardwareInfo hw{128,128,1+static_cast<int>(rng()%8),1000000,static_cast<int64_t>(rng()%4),static_cast<int64_t>(rng()%4)};
      auto schedule=ScheduleCvGraph(hw,graph,1000000);auto original=Simulate(hw,graph,schedule,1000000);
      if(!original.valid || !original.meets_deadline || AicoreLastMetric(2)!=original.makespan || AicoreLastMetric(3)!=original.peak_memory)throw std::runtime_error("Dense fast-path solver disagreement");
      compare(hw,graph,schedule);
      for(auto& stream:schedule.streams)for(auto& t:stream.tasks){t.op_id=2000000000-(t.op_id-1000000)/53*37;
        if(t.record_after>=0)t.record_after=1900000000-t.record_after*31;
        for(auto& w:t.wait_before)w=1900000000-w*31;std::reverse(t.wait_before.begin(),t.wait_before.end());}
      for(auto& v:graph){v.id=2000000000-(v.id-1000000)/53*37;for(auto& input:v.inputs)input=2000000000-(input-1000000)/53*37;std::reverse(v.inputs.begin(),v.inputs.end());}
      std::reverse(graph.begin(),graph.end());schedule.streams.insert(schedule.streams.begin(),StreamPlan{});schedule.streams.push_back(StreamPlan{});
      auto changed=Simulate(hw,graph,schedule,1000000);compare(hw,graph,schedule);
      if(!changed.valid || changed.makespan!=original.makespan || changed.peak_memory!=original.peak_memory)throw std::runtime_error("Identifier/stream/event metamorphic disagreement");++checks;
    }
    // JSON parser supports int64, escaped UTF-16 pairs, rejects floats, overflow, duplicate keys.
    auto raw=std::string("{\"n\":64000000000,\"name\":\"\\ud83d\\ude80\"}");
    auto j=local_json::Parser(raw).parse();if(j.at("n").integer()!=64000000000LL || j.at("name").text().size()!=4)throw std::runtime_error("JSON unicode/int64");++checks;
    for(auto s:{"1.2","9223372036854775808","{\"a\":1,\"a\":2}","[1,]"}){bool rejected=false;try{auto t=std::string(s);local_json::Parser(t).parse();}catch(const std::exception&){rejected=true;}if(!rejected)throw std::runtime_error("JSON invalid input accepted");++checks;}
    std::cout<<"PASS "<<checks<<" model/parser/priority checks\n";
  } catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
