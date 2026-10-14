#define main observer_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#ifdef R52_OBSERVER
#include "observer-solution.cpp"
#else
#include "solution.cpp"
#endif
int main(int argc,char** argv) {
  if(argc<3 || argc>7)return 2;
  std::ifstream file(argv[1]);std::ostringstream raw;raw<<file.rdbuf();auto data=local_json::Parser(raw.str()).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0;
  for(const auto& c:data.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto nodes=graph(c.at("nodes"));aicore_detail::Graph g(h,nodes);
#ifdef R52_OBSERVER
    aicore_detail::observer.reset();
#endif
    auto helper_cpu_before=thread_cpu_us();auto helper_wall_before=std::chrono::steady_clock::now();
    auto result=aicore_detail::macro_prefix_search(h,g,argc>=5?std::stoll(argv[4]):128000000,argc>=6?std::stoi(argv[5]):64,argc>=7?std::stoi(argv[6]):0);
    auto helper_cpu=thread_cpu_us()-helper_cpu_before;auto helper_wall=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-helper_wall_before).count();
    SchedulePlan helper_plan;SimulationResult helper_sim;
    if(result.order.size()==nodes.size()){
      helper_plan=aicore_detail::assemble(g,result.order,std::vector<int>(g.n,0),1,0);
      helper_sim=Simulate(h,nodes,helper_plan,c.at("deadline_us").integer());
      if(!helper_sim.valid || !helper_sim.meets_deadline || !equivalent(h,nodes,helper_plan,helper_sim))return 1;
    }
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"helper\":{\"work\":"<<result.work<<",\"evaluations\":"<<result.states
      <<",\"exhausted\":"<<(result.exhausted?"true":"false")<<",\"peak_lo\":"<<result.prunes<<",\"peak_hi\":"<<result.monitored_targets<<",\"cpu_us\":"<<helper_cpu<<",\"wall_us\":"<<helper_wall<<",\"memo_hits\":"<<result.memo_hits<<",\"safe_steps\":"<<result.safe_steps
      <<",\"order_ids\":[";bool first=true;for(int i:result.order){if(!first)out<<',';first=false;out<<nodes[i].id;}
    out<<"],\"plan\":"<<(helper_sim.valid?plan_json(helper_plan):"null")<<",\"valid\":"<<(helper_sim.valid?"true":"false")
      <<",\"T\":"<<helper_sim.makespan<<",\"peak\":"<<helper_sim.peak_memory<<'}';
#ifdef R52_OBSERVER
    out<<",\"helper_observer\":"<<aicore_detail::observer_json();
    aicore_detail::observer.reset();
#endif
    auto whole_cpu_before=thread_cpu_us();auto whole_wall_before=std::chrono::steady_clock::now();
    SchedulePlan whole;SimulationResult sim;bool returned=false;std::string error;
    try{if(argc>=4)throw std::runtime_error("helper-only");whole=ScheduleCvGraph(h,nodes,c.at("deadline_us").integer());returned=true;}catch(const std::exception& e){error=e.what();}
    auto whole_cpu=thread_cpu_us()-whole_cpu_before;auto whole_wall=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-whole_wall_before).count();
    if(returned){sim=Simulate(h,nodes,whole,c.at("deadline_us").integer());if(!sim.valid || !sim.meets_deadline || !equivalent(h,nodes,whole,sim))return 1;}
    out<<",\"whole\":{\"returned\":"<<(returned?"true":"false")<<",\"error\":"<<local_json::quote(error)<<",\"valid\":"<<(sim.valid?"true":"false")
      <<",\"T\":"<<sim.makespan<<",\"peak\":"<<sim.peak_memory<<",\"cpu_us\":"<<whole_cpu<<",\"wall_us\":"<<whole_wall<<",\"plan\":"<<(returned?plan_json(whole):"null")<<",\"metrics\":{ ";
    first=true;for(int k=0;k<=11;++k)if(k!=4){if(!first)out<<',';first=false;out<<'"'<<k<<"\":"<<AicoreLastMetric(k);}out<<"}}";
#ifdef R52_OBSERVER
    out<<",\"whole_observer\":"<<aicore_detail::observer_json();
#endif
    out<<'}';
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" complete original graphs diagnostic terminal\n";
}
