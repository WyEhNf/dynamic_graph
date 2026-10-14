#include "local_json.h"
#include "simulator.h"
#include "solver_metrics.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

static int64_t thread_cpu_us(){
#ifdef _WIN32
  FILETIME creation,exit,kernel,user;
  if(!GetThreadTimes(GetCurrentThread(),&creation,&exit,&kernel,&user))return -1;
  auto ticks=[](const FILETIME& x){return (static_cast<uint64_t>(x.dwHighDateTime)<<32)|x.dwLowDateTime;};
  return static_cast<int64_t>((ticks(kernel)+ticks(user))/10);
#else
  return -1; // Unavailable, never presented as zero execution cost.
#endif
}

using local_json::Value;
static int integer(const Value& x){auto n=x.integer();if(n<std::numeric_limits<int>::min() || n>std::numeric_limits<int>::max())throw std::runtime_error("Integer outside int range");return static_cast<int>(n);}
static HardwareInfo hardware(const Value& x){return {integer(x.at("aic_core_num")),integer(x.at("aiv_core_num")),integer(x.at("stream_num")),x.at("memory_limit").integer(),x.at("event_record_time").integer(),x.at("event_wait_time").integer()};}
static std::vector<OperatorNode> graph(const Value& input){
  std::vector<OperatorNode> result;
  for(const auto& x:input.list()) {
    auto type=x.at("core_type").text();if(type!="AIC" && type!="AIV")throw std::runtime_error("core_type must be AIC or AIV");
    OperatorNode n{integer(x.at("id")),type=="AIC"?CoreType::AIC:CoreType::AIV,integer(x.at("core_num")),x.at("exec_time").integer(),x.at("workspace_memory").integer(),x.at("output_memory").integer(),{}};
    for(const auto& p:x.at("inputs").list())n.inputs.push_back(integer(p));result.push_back(std::move(n));
  }return result;
}
static SchedulePlan parse_plan(const Value& x){
  SchedulePlan p;for(const auto& s:x.at("streams").list()){
    StreamPlan stream;for(const auto& t:s.at("tasks").list()){
      StreamTask task{integer(t.at("op_id")),{},integer(t.at("record_after"))};
      for(const auto& e:t.at("wait_before").list())task.wait_before.push_back(integer(e));stream.tasks.push_back(std::move(task));
    }p.streams.push_back(std::move(stream));
  }return p;
}
static std::string plan_json(const SchedulePlan& p){
  std::ostringstream out;out<<"{\"streams\":[";
  for(size_t s=0;s<p.streams.size();++s){if(s)out<<',';out<<"{\"tasks\":[";
    for(size_t k=0;k<p.streams[s].tasks.size();++k){if(k)out<<',';const auto& t=p.streams[s].tasks[k];out<<"{\"op_id\":"<<t.op_id<<",\"wait_before\":[";for(size_t j=0;j<t.wait_before.size();++j){if(j)out<<',';out<<t.wait_before[j];}out<<"],\"record_after\":"<<t.record_after<<'}';}out<<"]}";
  }out<<"]}";return out.str();
}
static bool equivalent(const HardwareInfo& hw,const std::vector<OperatorNode>& nodes,const SchedulePlan& plan,const SimulationResult& r){
  if((AicoreEvaluateMetric(hw,nodes,plan,0)==1)!=r.valid)return false;
  return !r.valid || (AicoreEvaluateMetric(hw,nodes,plan,1)==r.makespan && AicoreEvaluateMetric(hw,nodes,plan,2)==r.peak_memory);
}
static std::string csv_string(const std::string& s){std::string out="\"";for(char c:s){if(c=='"')out+='"';out+=c;}return out+'"';}
int main(int argc,char** argv){
  std::string input,output,csv,failures;
  for(int i=1;i<argc;++i){std::string arg=argv[i];if(i+1>=argc){std::cerr<<"Expected --input suite.json --output results.json [--csv metrics.csv] [--failures failed.json]\n";return 2;}if(arg=="--input")input=argv[++i];else if(arg=="--output")output=argv[++i];else if(arg=="--csv")csv=argv[++i];else if(arg=="--failures")failures=argv[++i];else {std::cerr<<"Unknown option "<<arg<<'\n';return 2;}}
  if(input.empty() || output.empty()){std::cerr<<"--input and --output are required\n";return 2;}
  if(failures.empty())failures=output+".failures.json";
  try {
    std::ifstream file(input,std::ios::binary);if(!file)throw std::runtime_error("Cannot open input");
    std::ostringstream source;source<<file.rdbuf();auto raw=source.str();auto root=local_json::Parser(raw).parse();
    if(root.at("format").text()!="aicore-local-v1")throw std::runtime_error("Unsupported local adapter format");
    std::ofstream out(output),bad(failures),table;
    if(!csv.empty())table.open(csv);
    if(!out || !bad || (!csv.empty() && !table))throw std::runtime_error("Cannot open result files; create output directory first");
    out<<"{\"format\":\"aicore-results-v1\",\"input_format\":\"local adapter, not official case format\",\"timing_scope\":\"solve_us is ScheduleCvGraph elapsed wall time; solve_thread_cpu_us is Win32 kernel+user thread CPU, -1 unavailable, potentially quantized\",\"cases\":[\n";
    bad<<"{\"format\":\"aicore-local-v1\",\"cases\":[";
    if(table)table<<"name,n,pass,valid,deadline,T,peak,solve_us,solve_thread_cpu_us,candidates,feasible_candidates,models_equal,duplicate_candidates,attempts,beam_expansions,beam_width,optimal_certificate,time_lower_bound,memory_lower_bound,error\n";
    int total=0,passed=0,failed=0;bool first=true;
    for(const auto& x:root.at("cases").list()) {
      ++total;std::string name="case_"+std::to_string(total),error;SchedulePlan plan;SimulationResult r;
      size_t n=0;int64_t deadline=0,elapsed=0,cpu_elapsed=-1,candidates=0,feasible=0,duplicates=0,attempts=0,beam_expansions=0,beam_width=0,certificate=0,time_bound=0,memory_bound=0;bool expected=true,models=true,returned=false;
      try {
        name=x.at("name").text();auto hw=hardware(x.at("hardware"));auto nodes=graph(x.at("nodes"));n=nodes.size();deadline=x.at("deadline_us").integer();
        if(x.object.count("expected_feasible")){if(x.at("expected_feasible").kind!=Value::Boolean)throw std::runtime_error("expected_feasible must be boolean");expected=x.at("expected_feasible").boolean;}
        if(x.object.count("witness_plan")) {
          auto witness=parse_plan(x.at("witness_plan"));auto wr=Simulate(hw,nodes,witness,deadline);
          if(!wr.valid || !wr.meets_deadline)throw std::runtime_error("Provided feasibility witness failed: "+wr.error);
          if(!equivalent(hw,nodes,witness,wr))throw std::runtime_error("Model disagreement on witness plan");
          if(x.object.count("generation")) {
            const auto& meta=x.at("generation");
            if(meta.object.count("witness_T") && meta.at("witness_T").integer()!=wr.makespan)throw std::runtime_error("Analytic witness time disagreement");
            if(meta.object.count("witness_peak") && meta.at("witness_peak").integer()!=wr.peak_memory)throw std::runtime_error("Analytic witness memory disagreement");
          }
        }
        auto cpu_start=thread_cpu_us();auto start=std::chrono::steady_clock::now();
        try {plan=ScheduleCvGraph(hw,nodes,deadline);returned=true;}catch(const std::exception& e){error=e.what();}
        elapsed=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
        auto cpu_end=thread_cpu_us();if(cpu_start>=0 && cpu_end>=cpu_start)cpu_elapsed=cpu_end-cpu_start;
        candidates=AicoreLastMetric(0);feasible=AicoreLastMetric(1);duplicates=AicoreLastMetric(5);attempts=AicoreLastMetric(6);
        beam_expansions=AicoreLastMetric(7);beam_width=AicoreLastMetric(8);
        certificate=AicoreLastMetric(9);time_bound=AicoreLastMetric(10);memory_bound=AicoreLastMetric(11);
        if(returned) {
          r=Simulate(hw,nodes,plan,deadline);models=equivalent(hw,nodes,plan,r);
          if(!models)error="Model disagreement on returned plan";
          else if(!r.valid || !r.meets_deadline)error="Returned infeasible plan: "+r.error;
        }
      } catch(const std::exception& e){error=e.what();models=false;}
      bool pass=models && (expected?(returned && r.valid && r.meets_deadline):!returned);
      if(pass)++passed;else {++failed;if(!first)bad<<',';first=false;bad<<local_json::dump(x);}
      if(total>1)out<<",\n";
      out<<"{\"name\":"<<local_json::quote(name)<<",\"n\":"<<n<<",\"pass\":"<<(pass?"true":"false")<<",\"expected_feasible\":"<<(expected?"true":"false")
         <<",\"valid\":"<<(r.valid?"true":"false")<<",\"deadline_us\":"<<deadline<<",\"T\":"<<r.makespan<<",\"peak_memory\":"<<r.peak_memory
         <<",\"solve_us\":"<<elapsed<<",\"solve_thread_cpu_us\":"<<cpu_elapsed<<",\"candidates\":"<<candidates<<",\"feasible_candidates\":"<<feasible<<",\"models_equal\":"<<(models?"true":"false")
         <<",\"duplicate_candidates\":"<<duplicates<<",\"attempts\":"<<attempts<<",\"beam_expansions\":"<<beam_expansions<<",\"beam_width\":"<<beam_width<<",\"optimal_certificate\":"<<(certificate?"true":"false")<<",\"time_lower_bound\":"<<time_bound<<",\"memory_lower_bound\":"<<memory_bound<<",\"error\":"<<local_json::quote(error)<<",\"plan\":"<<(returned?plan_json(plan):"null")<<'}';
      if(table)table<<csv_string(name)<<','<<n<<','<<pass<<','<<r.valid<<','<<deadline<<','<<r.makespan<<','<<r.peak_memory<<','<<elapsed<<','<<cpu_elapsed<<','<<candidates<<','<<feasible<<','<<models<<','<<duplicates<<','<<attempts<<','<<beam_expansions<<','<<beam_width<<','<<certificate<<','<<time_bound<<','<<memory_bound<<','<<csv_string(error)<<'\n';
    }
    bad<<"]}\n";out<<"\n],\"summary\":{\"total\":"<<total<<",\"passed\":"<<passed<<",\"failed\":"<<failed<<"}}\n";
    std::cout<<"cases="<<total<<" passed="<<passed<<" failed="<<failed<<"\n";
    return failed?1:0;
  } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
