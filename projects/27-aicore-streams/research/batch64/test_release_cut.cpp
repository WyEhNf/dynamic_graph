#define main cut_unused_benchmark_main
#include "../../src/benchmark.cpp"
#undef main
#include "solution.cpp"
int main(int argc,char** argv) {
  if(argc!=2)return 2;std::ifstream file(argv[1]);std::ostringstream raw;raw<<file.rdbuf();auto data=local_json::Parser(raw.str()).parse();int count=0;
  for(const auto& c:data.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto nodes=graph(c.at("nodes"));aicore_detail::Graph g(h,nodes);
    std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n);int64_t live=0;
    for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
    for(const auto& id:c.at("prefix").list()) {
      int i=g.index.at(static_cast<int>(id.integer()));if(done[i] || degree[i] || !aicore_detail::memory_fits(h.memory_limit,live,nodes[i].workspace_memory,nodes[i].output_memory))return 1;
      live+=nodes[i].output_memory;done[i]=1;for(int p:g.in[i])if(!--users[p])live-=nodes[p].output_memory;for(int ch:g.out[i])--degree[ch];
    }
    const auto& gold=c.at("gold");if(live!=std::stoll(gold.at("initial_live").text()))return 1;
    int64_t work=0;auto r=aicore_detail::release_cut_probe(h,g,g.index.at(static_cast<int>(c.at("producer").integer())),done,users,degree,live,work,16000000);
    std::vector<int> pending,order;for(const auto& id:gold.at("pending").list())pending.push_back(g.index.at(static_cast<int>(id.integer())));for(const auto& id:gold.at("order").list())order.push_back(g.index.at(static_cast<int>(id.integer())));
    if(r.exhausted || r.valid!=gold.at("valid").boolean || r.pending!=pending || r.order!=order || r.peak!=std::stoll(gold.at("peak").text()) || (r.valid && r.final_live!=std::stoll(gold.at("final_live").text()))) {std::cerr<<"Cut mismatch "<<c.at("name").text()<<'\n';return 1;}
    ++count;
  }
  std::cout<<count<<" original remaining-DIRECT/ancestor cut bigint controls passed\n";
}
