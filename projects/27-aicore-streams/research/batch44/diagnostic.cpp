#define main unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "solution.cpp"
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream f(argv[1]);std::ostringstream raw;raw<<f.rdbuf();auto doc=local_json::Parser(raw.str()).parse();std::ofstream out(argv[2]);
  out<<"{\"recognition\":\"input-only nodes/original edges\",\"cases\":[\n";int total=0,applicable=0,legal=0;
  for(const auto& c:doc.at("cases").list()) {
    const auto& x=c.at("hardware");HardwareInfo h{static_cast<int>(x.at("aic_core_num").integer()),static_cast<int>(x.at("aiv_core_num").integer()),static_cast<int>(x.at("stream_num").integer()),x.at("memory_limit").integer(),x.at("event_record_time").integer(),x.at("event_wait_time").integer()};
    std::vector<OperatorNode> nodes;
    for(const auto& v:c.at("nodes").list()) {
      OperatorNode n{static_cast<int>(v.at("id").integer()),v.at("core_type").text()=="AIC"?CoreType::AIC:CoreType::AIV,static_cast<int>(v.at("core_num").integer()),v.at("exec_time").integer(),v.at("workspace_memory").integer(),v.at("output_memory").integer(),{}};
      for(const auto& p:v.at("inputs").list())n.inputs.push_back(static_cast<int>(p.integer()));
      nodes.push_back(std::move(n));
    }
    aicore_detail::Graph g(h,nodes);auto shape=aicore_detail::shallow_shape(g);bool app=!shape.consumers.empty();if(app)++applicable;
    auto initial=app?aicore_detail::shallow_profile(h,g,shape,shape.consumers):aicore_detail::ShallowProfile();
    auto begin=std::chrono::steady_clock::now();auto result=aicore_detail::shallow_memory_search(h,g);
    auto us=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count();
    SimulationResult sim;SchedulePlan plan;bool matches=true;
    if(result.order.size()==nodes.size()) {
      plan=aicore_detail::assemble(g,result.order,std::vector<int>(g.n,0),1,0);sim=Simulate(h,nodes,plan,c.at("deadline_us").integer());matches=equivalent(h,nodes,plan,sim);
      if(!matches || !sim.valid){std::cerr<<"Invalid candidate "<<c.at("name").text()<<'\n';return 1;}
    }
    bool pass=sim.valid && sim.meets_deadline;if(pass)++legal;
    if(total++)out<<",\n";
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"applicable\":"<<(app?"true":"false")<<",\"initial_critical\":"<<initial.critical<<",\"initial_peak_lo\":"<<initial.peak.lo<<",\"initial_peak_hi\":"<<initial.peak.hi<<",\"best_peak_lo\":"<<result.best_peak.lo<<",\"best_peak_hi\":"<<result.best_peak.hi<<",\"producers\":"<<shape.producers.size()<<",\"consumers\":"<<shape.consumers.size()<<",\"tails\":"<<shape.tails.size()<<",\"pass\":"<<(pass?"true":"false")<<",\"valid\":"<<(sim.valid?"true":"false")<<",\"T\":"<<sim.makespan<<",\"peak_memory\":"<<sim.peak_memory<<",\"evaluations\":"<<result.evaluations<<",\"work\":"<<result.work<<",\"exhausted\":"<<(result.exhausted?"true":"false")<<",\"diagnostic_wall_us\":"<<us<<",\"plan\":"<<(sim.valid?plan_json(plan):"null")<<'}';
  }
  out<<"\n],\"summary\":{\"total\":"<<total<<",\"applicable\":"<<applicable<<",\"legal\":"<<legal<<"}}\n";
  std::cout<<total<<" inputs, "<<applicable<<" shallow, "<<legal<<" independently validated deadline-legal serial orders\n";
}
