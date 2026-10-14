#define main repair_gold_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "solution.cpp"
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream input(argv[1]);std::ostringstream raw;raw<<input.rdbuf();auto root=local_json::Parser(raw.str()).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0;
  for(const auto& c:root.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto nodes=graph(c.at("nodes"));aicore_detail::Graph g(h,nodes);
    std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n);int64_t live=0;
    for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
    for(const auto& value:c.at("prefix").list()) {
      int i=g.index.at(static_cast<int>(value.integer()));const auto& v=nodes[i];
      if(done[i] || degree[i] || !aicore_detail::memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory))return 3;
      live+=v.output_memory;done[i]=1;
      for(int p:g.in[i])if(!--users[p])live-=nodes[p].output_memory;
      for(int j:g.out[i])--degree[j];
    }
    int p=g.index.at(static_cast<int>(c.at("producer").integer()));int64_t work=0;
    auto r=aicore_detail::release_cut_probe(h,g,p,done,users,degree,live,work,c.at("limit").integer());
    // The supplied order is read only by the independent fixed-plan simulator,
    // AFTER candidate call. It never enters cut selection or production input.
    SchedulePlan fixed;fixed.streams.resize(1);
    for(const auto& id:c.at("supplied_whole_order").list())fixed.streams[0].tasks.push_back({static_cast<int>(id.integer()),{},-1});
    auto physical=Simulate(h,nodes,fixed,c.at("deadline_us").integer());
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"valid\":"<<(r.valid?"true":"false")
      <<",\"exhausted\":"<<(r.exhausted?"true":"false")<<",\"work\":"<<work<<",\"peak\":"<<r.peak<<",\"final_live\":"<<r.final_live<<",\"pending\":[";
    bool first=true;for(int i:r.pending){if(!first)out<<',';first=false;out<<nodes[i].id;}out<<"],\"order\":[";
    first=true;for(int i:r.order){if(!first)out<<',';first=false;out<<nodes[i].id;}
    out<<"],\"fixed_physics\":{\"valid\":"<<(physical.valid?"true":"false")<<",\"T\":"<<physical.makespan<<",\"peak\":"<<physical.peak_memory<<"},\"direct_repair_check\":";
    if(c.at("direct_repair_check").kind!=Value::Null) {
      const auto& req=c.at("direct_repair_check");std::vector<int> pending;
      for(const auto& id:req.at("pending").list())pending.push_back(g.index.at(static_cast<int>(id.integer())));
      int64_t directwork=0;auto direct=aicore_detail::failed_cut_beam_repair(h,g,p,pending,users,degree,live,directwork,req.at("limit").integer());
      out<<"{\"valid\":"<<(direct.valid?"true":"false")<<",\"exhausted\":"<<(direct.exhausted?"true":"false")<<",\"work\":"<<directwork<<",\"peak\":"<<direct.peak<<",\"final_live\":"<<direct.final_live<<",\"order\":[";
      first=true;for(int i:direct.order){if(!first)out<<',';first=false;out<<nodes[i].id;}out<<"]}";
    }else out<<"null";
    out<<'}';
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" original-DAG repair controls actual terminal\n";
}
