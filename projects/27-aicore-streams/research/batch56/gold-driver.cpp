#define main causal_gold_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "solution.cpp"
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream input(argv[1]);std::ostringstream raw;raw<<input.rdbuf();auto root=local_json::Parser(raw.str()).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0;
  for(const auto& c:root.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto nodes=graph(c.at("nodes"));aicore_detail::Graph g(h,nodes);
    std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n),prefix,held;int64_t live=0;
    for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
    for(const auto& value:c.at("prefix").list()) {
      int i=g.index.at(static_cast<int>(value.integer()));const auto& v=nodes[i];
      if(done[i] || degree[i] || !aicore_detail::memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory))return 3;
      live+=v.output_memory;done[i]=1;prefix.push_back(i);
      for(int p:g.in[i])if(!--users[p])live-=nodes[p].output_memory;
      for(int j:g.out[i])--degree[j];
    }
    for(int i=0;i<g.n;++i)if(done[i] && users[i] && nodes[i].output_memory)held.push_back(i);
    std::stable_sort(held.begin(),held.end(),[&](int a,int b){return nodes[a].output_memory!=nodes[b].output_memory?nodes[a].output_memory>nodes[b].output_memory:nodes[a].id<nodes[b].id;});
    if(held.size()>24)held.resize(24);
    int64_t work=0;auto pair=aicore_detail::causal_deferral_pair(h,g,done,users,prefix,held,work,c.at("limit").integer());
    auto order=aicore_detail::release_cut_order(h,g,2000000);
    SchedulePlan actual;actual.streams.resize(1);for(int i:order.order)actual.streams[0].tasks.push_back({nodes[i].id,{},-1});
    auto actual_physical=Simulate(h,nodes,actual,c.at("deadline_us").integer());
    // Fixed-plan reference order is read only AFTER candidate calls, not supplied
    // to pairing, restarting, priority or search. Names are output labels only.
    SchedulePlan fixed;fixed.streams.resize(1);for(const auto& id:c.at("supplied_whole_order").list())fixed.streams[0].tasks.push_back({static_cast<int>(id.integer()),{},-1});
    auto physical=Simulate(h,nodes,fixed,c.at("deadline_us").integer());
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"producer\":";
    if(pair.producer<0)out<<"null";else out<<nodes[pair.producer].id;
    out<<",\"target\":";if(pair.target<0)out<<"null";else out<<nodes[pair.target].id;
    out<<",\"complete\":"<<(pair.complete?"true":"false")<<",\"exhausted\":"<<(pair.exhausted?"true":"false")<<",\"work\":"<<work
       <<",\"whole_order\":[";bool first=true;for(int i:order.order){if(!first)out<<',';first=false;out<<nodes[i].id;}
    out<<"],\"whole_work\":"<<order.work<<",\"whole_exhausted\":"<<(order.exhausted?"true":"false")
       <<",\"whole_physics\":{\"valid\":"<<(actual_physical.valid?"true":"false")<<",\"T\":"<<actual_physical.makespan<<",\"peak\":"<<actual_physical.peak_memory<<"}"
       <<",\"fixed_physics\":{\"valid\":"<<(physical.valid?"true":"false")<<",\"T\":"<<physical.makespan<<",\"peak\":"<<physical.peak_memory<<"}}";
    if(order.order.size()==static_cast<size_t>(g.n) && !actual_physical.valid)return 4;
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" original causal deferral controls terminal\n";
}
