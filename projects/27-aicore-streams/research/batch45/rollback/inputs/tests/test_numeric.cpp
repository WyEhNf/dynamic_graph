#define main numeric_unused_benchmark_main
#include "../src/benchmark.cpp"
#undef main
#include "../solution/solution.cpp"
static int64_t gold(const Value& v){return v.kind==Value::String?std::stoll(v.text()):v.integer();}
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  std::ifstream input(argv[1]);std::ostringstream text;text<<input.rdbuf();auto raw=text.str();auto data=local_json::Parser(raw).parse();
  std::ofstream out(argv[2]);out<<"{\"cases\":[";int count=0,passed=0;
  for(const auto& c:data.at("cases").list()) {
    auto h=hardware(c.at("hardware"));auto v=graph(c.at("nodes"));auto p=parse_plan(c.at("fixed_plan"));
    auto r=Simulate(h,v,p,INT64_MAX);bool expected=c.object.count("gold_valid")?c.at("gold_valid").boolean:true;
    auto direct=AicoreEvaluateMetric(h,v,p,0);bool match=(r.valid==expected && (direct==1)==expected);
    if(expected)match=match && r.makespan==gold(c.at("gold_T")) && r.peak_memory==gold(c.at("gold_peak")) && AicoreEvaluateMetric(h,v,p,1)==r.makespan && AicoreEvaluateMetric(h,v,p,2)==r.peak_memory;
    bool called=c.object.count("expected_feasible"),returned=false,solver_valid=false;
    if(called) {
      try{auto chosen=ScheduleCvGraph(h,v,INT64_MAX);returned=true;auto check=Simulate(h,v,chosen,INT64_MAX);solver_valid=check.valid && check.meets_deadline;}catch(const std::exception&){}
      if(!c.object.count("witness_plan"))match=match && (c.at("expected_feasible").boolean?(returned && solver_valid):!returned);
      // Probe score-heavy private paths even if normal solver certifies early.
      aicore_detail::Graph g(h,v);
      for(int mode=0;mode<6;++mode)aicore_detail::ordering(g,mode);
      for(int mode=0;mode<6;++mode)aicore_detail::memory_ordering(h,g,mode);
      for(int mode=0;mode<2;++mode)aicore_detail::beam_ordering(h,g,8,6,mode);
      for(int mode:{0,1,2,24,27,33})aicore_detail::bundle_ordering(h,g,mode);
      aicore_detail::sink_projection_order(h,g);
      auto optimal=aicore_detail::serial_oracle(g);
      if(!c.object.count("witness_plan"))match=match && aicore_detail::serial_evaluate(h,g,optimal).valid==c.at("expected_feasible").boolean;
      for(bool paired:{false,true})for(bool normalize:{false,true}) {
        auto searched=aicore_detail::serial_frontier_search(h,g,100000,paired,false,normalize);
        if(!c.object.count("witness_plan"))match=match && (searched.order.size()==v.size())==c.at("expected_feasible").boolean;
      }
      aicore_detail::resource_list(h,g,2,0,true);aicore_detail::resource_delayed(h,g,2,0,true);
    }
    if(count++)out<<',';
    out<<"{\"name\":"<<local_json::quote(c.at("name").text())<<",\"pass\":"<<(match?"true":"false")<<",\"valid\":"<<(r.valid?"true":"false")<<",\"production_valid\":"<<(direct==1?"true":"false")<<",\"T\":"<<r.makespan<<",\"peak\":"<<r.peak_memory<<",\"solver_called\":"<<(called?"true":"false")<<",\"solver_returned\":"<<(returned?"true":"false")<<",\"solver_valid\":"<<(solver_valid?"true":"false")<<",\"error\":"<<local_json::quote(r.error)<<"}";
    if(match)++passed;else std::cerr<<c.at("name").text()<<" failed\n";
  }
  out<<"],\"total\":"<<count<<",\"passed\":"<<passed<<"}\n";std::cout<<passed<<"/"<<count<<" fixed-plan bigint gold checks\n";return passed==count?0:1;
}

