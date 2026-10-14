#define main observer_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "observer-solution.cpp"
static const std::array<const char*,107> r56_stage_labels={"causal_deferral_pair:return-1:line-758","causal_deferral_pair:return-2:line-760","causal_deferral_pair:return-3:line-761","causal_deferral_pair:return-4:line-763","causal_deferral_pair:return-5:line-766","causal_deferral_pair:return-6:line-768","causal_deferral_pair:return-7:line-771","causal_deferral_pair:return-8:line-773","causal_deferral_pair:return-9:line-775","causal_deferral_pair:return-10:line-776","causal_deferral_pair:return-11:line-779","causal_deferral_pair:return-12:line-781","causal_deferral_pair:return-13:line-783","causal_deferral_pair:return-14:line-784","causal_deferral_pair:return-15:line-787","causal_deferral_pair:return-16:line-790","causal_deferral_pair:return-17:line-794","causal_deferral_pair:return-18:line-798","causal_deferral_pair:return-19:line-799","causal_deferral_pair:return-20:line-802","causal_deferral_pair:return-21:line-806","causal_deferral_pair:return-22:line-808","causal_deferral_pair:return-23:line-809","causal_deferral_pair:return-24:line-811","causal_deferral_pair:return-25:line-816","causal_deferral_pair:return-26:line-819","causal_deferral_pair:return-27:line-828","causal_deferral_pair:return-28:line-828","release_cut_probe_guarded:return-0:line-835","release_cut_probe_guarded:return-2:line-836","release_cut_probe_guarded:return-3:line-837","release_cut_probe_guarded:return-4:line-838","release_cut_probe_guarded:return-5:line-841","release_cut_probe_guarded:return-6:line-844","release_cut_probe_guarded:return-7:line-846","release_cut_probe_guarded:return-8:line-847","release_cut_probe_guarded:return-9:line-849","release_cut_probe_guarded:return-10:line-853","release_cut_probe_guarded:return-11:line-855","release_cut_probe_guarded:return-12:line-858","release_cut_probe_guarded:return-13:line-863","release_cut_probe_guarded:return-14:line-867","release_cut_probe_guarded:return-15:line-868","release_cut_probe_guarded:return-16:line-872","release_cut_probe_guarded:return-17:line-873","release_cut_order_guarded:return-0:line-877","release_cut_order_guarded:return-1:line-878","release_cut_order_guarded:return-2:line-882","release_cut_order_guarded:return-4:line-884","release_cut_order_guarded:return-6:line-888","release_cut_order_guarded:return-7:line-889","release_cut_order_guarded:return-8:line-889","release_cut_order_guarded:return-9:line-890","release_cut_order_guarded:return-11:line-900","release_cut_order_guarded:return-12:line-902","release_cut_order_guarded:return-13:line-904","release_cut_order_guarded:return-14:line-909","release_cut_order_guarded:return-16:line-912","release_cut_order_guarded:return-17:line-916","release_cut_order_guarded:return-18:line-919","release_cut_order_guarded:return-19:line-920","release_cut_order_guarded:return-20:line-922","causal_deferral_restart:return-1:line-930","causal_deferral_restart:return-2:line-931","causal_deferral_restart:return-3:line-933","causal_deferral_restart:return-4:line-934","causal_deferral_restart:return-5:line-935","causal_deferral_restart:return-6:line-939","causal_deferral_restart:return-7:line-940","restart-before-entry-charge","restart-detector-return-before-status-charge","restart-status-dispatch-paid-before-guard","restart-guard-return-before-merge-charge","release_cut_probe:return-0:line-947","release_cut_probe:return-2:line-948","release_cut_probe:return-3:line-949","release_cut_probe:return-4:line-950","release_cut_probe:return-5:line-953","release_cut_probe:return-6:line-956","release_cut_probe:return-7:line-958","release_cut_probe:return-8:line-959","release_cut_probe:return-9:line-961","release_cut_probe:return-10:line-965","release_cut_probe:return-11:line-969","release_cut_probe:return-12:line-974","release_cut_probe:return-13:line-978","release_cut_probe:return-14:line-979","release_cut_probe:return-15:line-983","release_cut_probe:return-16:line-984","release_cut_order:return-0:line-987","release_cut_order:return-1:line-988","release_cut_order:return-2:line-992","release_cut_order:return-4:line-994","release_cut_order:return-6:line-998","release_cut_order:return-7:line-999","release_cut_order:return-9:line-1009","release_cut_order:return-10:line-1012","release_cut_order:return-11:line-1017","release_cut_order:return-13:line-1020","release_cut_order:return-14:line-1024","release_cut_order:return-15:line-1027","release_cut_order:return-16:line-1029","release_cut_order:return-17:line-1030","release_cut_order:return-18:line-1033","projection_memory_search:return-0:line-1223","projection_memory_search:return-1:line-1226","wrapper-cut-return-before-projection"};
static std::string r56_observer_json(){
  const auto& o=aicore_detail::r56_observer;std::ostringstream s;
  s<<"{\"metadata_limit\":16,\"state_limit\":2,\"array_limit\":4096,\"selection\":\"first15_and_last_metadata_first2_states\",\"metadata_seen\":"<<o.metadata_seen<<",\"metadata_dropped\":"<<o.metadata_dropped<<",\"states_seen\":"<<o.states_seen<<",\"states_dropped\":"<<o.states_dropped<<",\"counter_overflow\":"<<(o.counter_overflow?"true":"false")<<",\"state_shape_error\":"<<(o.state_shape_error?"true":"false")<<",\"stage_counts\":[";
  for(size_t k=0;k<r56_stage_labels.size();++k){if(k)s<<',';s<<"{\"id\":"<<k<<",\"label\":"<<local_json::quote(r56_stage_labels[k])<<",\"count\":"<<o.stage_counts[k]<<'}';}
  s<<"],\"metadata\":[";for(int k=0;k<o.metadata_count;++k){if(k)s<<',';const auto& x=o.metadata[k];s<<"{\"stage\":"<<x.stage<<",\"producer_id\":"<<x.producer_id<<",\"target_id\":"<<x.target_id<<",\"work\":"<<x.work<<",\"limit\":"<<x.limit<<",\"flags\":"<<x.flags<<",\"order_size\":"<<x.order_size<<",\"peak_lo\":"<<x.peak_lo<<",\"peak_hi\":"<<x.peak_hi<<'}';}
  s<<"],\"states\":[";
  auto ints=[&](const char* label,const auto& a,int n){s<<",\""<<label<<"\":[";for(int j=0;j<n;++j){if(j)s<<',';s<<static_cast<int64_t>(a[j]);}s<<']';};
  for(int k=0;k<o.state_count;++k){if(k)s<<',';const auto& x=o.states[k];s<<"{\"stage\":"<<x.stage<<",\"n\":"<<x.n<<",\"live\":"<<x.live<<",\"pending_provided\":"<<(x.pending_provided?"true":"false")<<",\"held_provided\":"<<(x.held_provided?"true":"false");ints("original_ids",x.original_ids,x.n);ints("prefix_ids",x.prefix_ids,x.prefix_size);ints("done",x.done,x.n);ints("users",x.users,x.n);ints("degree",x.degree,x.n);ints("held_ids",x.held_ids,x.held_size);ints("pending_ids",x.pending_ids,x.pending_size);s<<'}';}
  s<<"]}";return s.str();
}

int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream file(argv[1]);std::ostringstream raw;raw<<file.rdbuf();auto data=local_json::Parser(raw.str()).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0;
  for(const auto& c:data.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto nodes=graph(c.at("nodes"));aicore_detail::Graph g(h,nodes);
aicore_detail::r56_observer.reset();
    auto result=aicore_detail::projection_memory_search(h,g);
    SchedulePlan helper_plan;SimulationResult helper_sim;
    if(result.order.size()==nodes.size()){
      helper_plan=aicore_detail::assemble(g,result.order,std::vector<int>(g.n,0),1,0);
      helper_sim=Simulate(h,nodes,helper_plan,c.at("deadline_us").integer());
      if(!helper_sim.valid || !helper_sim.meets_deadline || !equivalent(h,nodes,helper_plan,helper_sim))return 1;
    }
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"helper\":{\"work\":"<<result.work<<",\"evaluations\":"<<result.evaluations
      <<",\"exhausted\":"<<(result.exhausted?"true":"false")<<",\"peak_lo\":"<<result.best_peak.lo<<",\"peak_hi\":"<<result.best_peak.hi
      <<",\"order_ids\":[";bool first=true;for(int i:result.order){if(!first)out<<',';first=false;out<<nodes[i].id;}
    out<<"],\"plan\":"<<(helper_sim.valid?plan_json(helper_plan):"null")<<",\"valid\":"<<(helper_sim.valid?"true":"false")
      <<",\"T\":"<<helper_sim.makespan<<",\"peak\":"<<helper_sim.peak_memory<<'}';
out<<",\"helper_observer\":"<<r56_observer_json();
    aicore_detail::r56_observer.reset();
    SchedulePlan whole;SimulationResult sim;bool returned=false;std::string error;
    try{whole=ScheduleCvGraph(h,nodes,c.at("deadline_us").integer());returned=true;}catch(const std::exception& e){error=e.what();}
    if(returned){sim=Simulate(h,nodes,whole,c.at("deadline_us").integer());if(!sim.valid || !sim.meets_deadline || !equivalent(h,nodes,whole,sim))return 1;}
    out<<",\"whole\":{\"returned\":"<<(returned?"true":"false")<<",\"error\":"<<local_json::quote(error)<<",\"valid\":"<<(sim.valid?"true":"false")
      <<",\"T\":"<<sim.makespan<<",\"peak\":"<<sim.peak_memory<<",\"plan\":"<<(returned?plan_json(whole):"null")<<",\"metrics\":{ ";
    first=true;for(int k=0;k<=11;++k)if(k!=4){if(!first)out<<',';first=false;out<<'"'<<k<<"\":"<<AicoreLastMetric(k);}out<<"}}";
out<<",\"whole_observer\":"<<r56_observer_json();
    out<<'}';
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" complete original graphs diagnostic terminal\n";
}
