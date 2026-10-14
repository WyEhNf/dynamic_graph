#include "local_json.h"
#include "simulator.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <tuple>

// Exhaustive for n<=6 and at most two streams, within the explicitly direct
// synchronization contract of the local verifier. No solver calls are made.
int main(int argc,char** argv) {
  if(argc!=3){std::cerr<<"Usage: aicore_oracle input.json output.json\n";return 2;}
  try {
    std::ifstream input(argv[1]);std::ostringstream raw;raw<<input.rdbuf();
    auto root=local_json::Parser(raw.str()).parse();
    for(auto& x:root.object.at("cases").array) {
      const auto& h=x.at("hardware");
      HardwareInfo hw{static_cast<int>(h.at("aic_core_num").integer()),static_cast<int>(h.at("aiv_core_num").integer()),static_cast<int>(h.at("stream_num").integer()),h.at("memory_limit").integer(),h.at("event_record_time").integer(),h.at("event_wait_time").integer()};
      std::vector<OperatorNode> nodes;
      for(const auto& v:x.at("nodes").list()) {OperatorNode o{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};for(const auto& p:v.at("inputs").list())o.inputs.push_back(static_cast<int>(p.integer()));nodes.push_back(o);}
      int n=static_cast<int>(nodes.size());if(n<1 || n>6 || hw.stream_num<1 || hw.stream_num>2)throw std::runtime_error("Oracle supports 1..6 nodes and 1..2 streams only");
      std::vector<std::vector<int>> pred(n);
      for(int i=0;i<n;++i)for(int id:nodes[i].inputs){auto p=std::find_if(nodes.begin(),nodes.end(),[&](const auto& v){return v.id==id;});if(p==nodes.end())throw std::runtime_error("Unknown predecessor");pred[i].push_back(static_cast<int>(p-nodes.begin()));}
      std::vector<int> order(n);std::iota(order.begin(),order.end(),0);
      bool found=false;SimulationResult best;SchedulePlan answer;int64_t evaluated=0;
      do {
        std::vector<int> position(n);for(int k=0;k<n;++k)position[order[k]]=k;
        bool topo=true;for(int i=0;i<n;++i)for(int p:pred[i])if(position[p]>=position[i])topo=false;if(!topo)continue;
        int assignments=1;for(int i=0;i<n;++i)assignments*=hw.stream_num;
        for(int code=0;code<assignments;++code) {
          std::vector<int> owner(n);int remainder=code;for(int i=0;i<n;++i){owner[i]=remainder%hw.stream_num;remainder/=hw.stream_num;}
          std::vector<std::pair<int,int>> optional;
          for(int a=0;a<n;++a)for(int b=a+1;b<n;++b){int p=order[a],i=order[b];if(owner[p]!=owner[i] && std::find(pred[i].begin(),pred[i].end(),p)==pred[i].end())optional.emplace_back(p,i);}
          for(unsigned mask=0;mask<(1u<<optional.size());++mask) {
            auto before=pred;for(size_t k=0;k<optional.size();++k)if(mask&(1u<<k))before[optional[k].second].push_back(optional[k].first);
            std::vector<bool> record(n);for(int i=0;i<n;++i)for(int p:before[i])if(owner[p]!=owner[i])record[p]=true;
            SchedulePlan plan;plan.streams.resize(hw.stream_num);
            for(int i:order){StreamTask t{nodes[i].id,{},record[i]?i:-1};for(int p:before[i])if(owner[p]!=owner[i])t.wait_before.push_back(p);plan.streams[owner[i]].tasks.push_back(t);}
            auto result=Simulate(hw,nodes,plan,std::numeric_limits<int64_t>::max());++evaluated;
            if(result.valid && (!found || std::tie(result.makespan,result.peak_memory)<std::tie(best.makespan,best.peak_memory))){found=true;best=result;answer=plan;}
          }
        }
      }while(std::next_permutation(order.begin(),order.end()));
      if(!found)throw std::runtime_error("Oracle found no legal schedule");
      std::ostringstream p;p<<"{\"streams\":[";
      for(size_t s=0;s<answer.streams.size();++s){if(s)p<<',';p<<"{\"tasks\":[";for(size_t k=0;k<answer.streams[s].tasks.size();++k){if(k)p<<',';const auto& t=answer.streams[s].tasks[k];p<<"{\"op_id\":"<<t.op_id<<",\"record_after\":"<<t.record_after<<",\"wait_before\":[";for(size_t j=0;j<t.wait_before.size();++j){if(j)p<<',';p<<t.wait_before[j];}p<<"]}";}p<<"]}";}p<<"]}";
      x.object["witness_plan"]=local_json::Parser(p.str()).parse();
      x.object["deadline_us"]=local_json::Parser(std::to_string(best.makespan)).parse();
      std::ostringstream meta;meta<<"{\"family\":\"parallel_exact_oracle\",\"feasibility\":\"exhaustive n<=6, <=2 streams, conservative direct synchronization model\",\"oracle_T\":"<<best.makespan<<",\"oracle_peak\":"<<best.peak_memory<<",\"witness_T\":"<<best.makespan<<",\"witness_peak\":"<<best.peak_memory<<",\"plans_evaluated\":"<<evaluated<<'}';
      x.object["generation"]=local_json::Parser(meta.str()).parse();
      std::cout<<x.at("name").text()<<" plans="<<evaluated<<" optimum="<<best.makespan<<"/"<<best.peak_memory<<'\n';
    }
    std::ofstream output(argv[2]);output<<local_json::dump(root)<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
