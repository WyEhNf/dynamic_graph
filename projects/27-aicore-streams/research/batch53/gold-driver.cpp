#define main final_gold_unused_benchmark_main
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
    bool have=false;int64_t incumbent=0;std::pair<int64_t,int64_t> selected;
    if(count++)out<<',';out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"requests\":[";
    int requestno=0;
    for(const auto& req:c.at("requests").list()) {
      int p=g.index.at(static_cast<int>(req.at("producer").integer()));int64_t work=0;
      auto r=aicore_detail::release_cut_probe(h,g,p,done,users,degree,live,work,2000000,have?&incumbent:nullptr);
      if(requestno++)out<<',';
      out<<"{\"producer\":"<<nodes[p].id<<",\"valid\":"<<(r.valid?"true":"false")<<",\"exhausted\":"<<(r.exhausted?"true":"false")
        <<",\"pruned\":"<<(r.pruned?"true":"false")<<",\"work\":"<<work<<",\"peak\":"<<r.peak<<",\"final_live\":"<<r.final_live<<",\"pending\":[";
      bool first=true;for(int i:r.pending){if(!first)out<<',';first=false;out<<nodes[i].id;}out<<"],\"order\":[";
      first=true;for(int i:r.order){if(!first)out<<',';first=false;out<<nodes[i].id;}out<<']';
      // Formula-only diagnostic: use a real already validated same-prefix cut.
      // On the first valid candidate it may use that just validated cut for
      // equality/value gold; first actual production probe ABOVE still had null.
      bool canbound=have || r.valid;
      if(canbound && !r.pending.empty()) {
        std::vector<unsigned char> included(g.n);for(int i:r.pending)included[i]=1;
        aicore_detail::ProfileInteger final;bool dominated=false;int64_t boundwork=0;
        bool complete=aicore_detail::release_cut_final_dominated(g,r.pending,included,done,users,live,have?incumbent:r.final_live,boundwork,2000000,final,dominated);
        if(!complete)return 4;
        out<<",\"bound\":{\"hi\":"<<final.hi<<",\"lo\":"<<final.lo<<",\"work\":"<<boundwork<<",\"dominated\":"<<(dominated?"true":"false")<<'}';
        if(c.at("bound_budget").kind!=Value::Null && c.at("bound_budget").at("request").integer()==requestno-1) {
          auto limit=c.at("bound_budget").at("limit").integer();boundwork=0;final={};dominated=false;
          complete=aicore_detail::release_cut_final_dominated(g,r.pending,included,done,users,live,incumbent,boundwork,limit,final,dominated);
          out<<",\"budget\":{\"complete\":"<<(complete?"true":"false")<<",\"work\":"<<boundwork<<'}';
        }
      }else out<<",\"bound\":null";
      if(r.valid && (!have || std::make_pair(r.final_live,r.peak)<selected)){selected={r.final_live,r.peak};incumbent=r.final_live;have=true;}
      out<<'}';
    }
    out<<"],\"have\":"<<(have?"true":"false")<<'}';
  }
  out<<"],\"count\":"<<count<<"}\n";std::cout<<count<<" complete original-DAG gold controls actual terminal\n";
}
