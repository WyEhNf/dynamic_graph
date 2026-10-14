#define main causal_caller_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "solution.cpp"
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream input(argv[1]);std::ostringstream raw;raw<<input.rdbuf();auto root=local_json::Parser(raw.str()).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0;
  for(const auto& c:root.at("cases").list()) {
    // Fixture/routine select diagnostic API calls only; production source sees
    // original hardware/nodes/state, never name, fixture or expected values.
    const auto& f=root.at("fixtures").at(c.at("fixture").text());auto h=hardware(f.at("hardware"));auto nodes=graph(f.at("nodes"));aicore_detail::Graph g(h,nodes);
    std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n),prefix,held;int64_t live=0;
    for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
    for(const auto& id:f.at("prefix").list()) {
      int i=g.index.at(static_cast<int>(id.integer()));const auto& v=nodes[i];
      if(done[i] || degree[i] || !aicore_detail::memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory))return 3;
      live+=v.output_memory;done[i]=1;prefix.push_back(i);
      for(int p:g.in[i])if(!--users[p])live-=nodes[p].output_memory;
      for(int j:g.out[i])--degree[j];
    }
    for(int i=0;i<g.n;++i)if(done[i] && users[i] && nodes[i].output_memory)held.push_back(i);
    std::stable_sort(held.begin(),held.end(),[&](int a,int b){return nodes[a].output_memory!=nodes[b].output_memory?nodes[a].output_memory>nodes[b].output_memory:nodes[a].id<nodes[b].id;});if(held.size()>24)held.resize(24);
    int64_t work=c.at("initial_work").integer(),limit=c.at("limit").integer(),peak=0,final_live=0;bool valid=false,exhausted=false;
    std::vector<int> order;
    if(c.at("routine").text()=="restart") {
      auto r=aicore_detail::causal_deferral_restart(h,g,done,users,prefix,held,work,limit,0);
      valid=r.order.size()==static_cast<size_t>(g.n);exhausted=r.exhausted;order=r.order;peak=static_cast<int64_t>(r.best_peak.lo);
    }else {
      int p=g.index.at(static_cast<int>(f.at("producer").integer())),delayed=g.index.at(static_cast<int>(f.at("delayed").integer())),target=g.index.at(static_cast<int>(f.at("target").integer()));
      auto r=aicore_detail::release_cut_probe_guarded(h,g,p,done,users,degree,live,work,limit,delayed,target);
      valid=r.valid;exhausted=r.exhausted;order=r.order;peak=r.peak;final_live=r.final_live;
    }
    // Read only after diagnostic call, for independent original fullplan physics.
    SchedulePlan fixed;fixed.streams.resize(1);for(const auto& id:f.at("fixed_order").list())fixed.streams[0].tasks.push_back({static_cast<int>(id.integer()),{},-1});
    auto physical=Simulate(h,nodes,fixed,f.at("deadline_us").integer());
    SchedulePlan returned;SimulationResult returned_physical;std::vector<int> returned_ids;
    if(valid) {
      returned.streams.resize(1);std::vector<unsigned char> included(g.n);
      auto append=[&](int i){included[i]=1;returned_ids.push_back(nodes[i].id);returned.streams[0].tasks.push_back({nodes[i].id,{},-1});};
      if(c.at("routine").text()!="restart")for(int i:prefix)append(i);
      for(int i:order)append(i);
      // Diagnostic guarded-probe continuation uses ORIGINAL topo outside C.
      // No fixture/fixed order is supplied to the candidate routine.
      if(c.at("routine").text()!="restart")for(int i:g.topo)if(!included[i])append(i);
      returned_physical=Simulate(h,nodes,returned,f.at("deadline_us").integer());
      if(!returned_physical.valid || !returned_physical.meets_deadline)return 4;
    }
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"valid\":"<<(valid?"true":"false")<<",\"exhausted\":"<<(exhausted?"true":"false")<<",\"work\":"<<work<<",\"peak\":"<<peak<<",\"final_live\":"<<final_live<<",\"order\":[";
    bool first=true;for(int i:order){if(!first)out<<',';first=false;out<<nodes[i].id;}
    out<<"],\"returned_whole_ids\":[";first=true;for(int id:returned_ids){if(!first)out<<',';first=false;out<<id;}
    out<<"],\"returned_physics\":{\"valid\":"<<(returned_physical.valid?"true":"false")<<",\"T\":"<<returned_physical.makespan<<",\"peak\":"<<returned_physical.peak_memory<<"},\"fixed_physics\":{\"valid\":"<<(physical.valid?"true":"false")<<",\"T\":"<<physical.makespan<<",\"peak\":"<<physical.peak_memory<<"}}";
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" predeclared caller/guard controls terminal\n";
}
