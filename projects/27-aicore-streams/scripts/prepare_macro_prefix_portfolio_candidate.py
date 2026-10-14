"""R62 ranking/beam ablation with process-independent per-call CPU timing."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/batch62';OUT.mkdir(exist_ok=True)
source=(ROOT/'research/batch61/macro_prefix_search.inc').read_text()
source=source.replace('I limit=128000000,int width=64)', 'I limit=128000000,int width=64,int style=0)')
source=source.replace('auto less=[](const State& a,const State& b){return std::tie(a.live,a.peak,a.area,a.mask)<std::tie(b.live,b.peak,b.area,b.mask);};', '''auto less=[&](const State& a,const State& b){
    if(style==1)return std::tie(a.peak,a.live,a.area,a.mask)<std::tie(b.peak,b.live,b.area,b.mask);
    if(style==2)return std::tie(a.area,a.live,a.peak,a.mask)<std::tie(b.area,b.live,b.peak,b.mask);
    if(style==3){
      I av=priority_mul_div(a.live,static_cast<I>(g.n),std::max<size_t>(1,a.order.size()));
      I bv=priority_mul_div(b.live,static_cast<I>(g.n),std::max<size_t>(1,b.order.size()));
      if(av!=bv)return av<bv;
    }
    return std::tie(a.live,a.peak,a.area,a.mask)<std::tie(b.live,b.peak,b.area,b.mask);
  };''')
# Mutation and rollback are reserved together before mutating a candidate.
source=source.replace('charge(1+static_cast<I>(g.in[node].size()))', 'charge(2*(1+static_cast<I>(g.in[node].size())))')
(OUT/'macro_prefix_search.inc').write_text(source)
(OUT/'solution.cpp').write_text((ROOT/'research/batch61/solution.cpp').read_text())
driver=(ROOT/'research/batch61/selected-driver.cpp').read_text().replace('argc>6','argc>7')
driver=driver.replace('argc>=6?std::stoi(argv[5]):64)', 'argc>=6?std::stoi(argv[5]):64,argc>=7?std::stoi(argv[6]):0)')
driver=driver.replace('    auto result=aicore_detail::macro_prefix_search', '    auto helper_cpu_before=thread_cpu_us();auto helper_wall_before=std::chrono::steady_clock::now();\n    auto result=aicore_detail::macro_prefix_search')
driver=driver.replace('    SchedulePlan helper_plan;', '    auto helper_cpu=thread_cpu_us()-helper_cpu_before;auto helper_wall=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-helper_wall_before).count();\n    SchedulePlan helper_plan;')
driver=driver.replace('<<result.monitored_targets', '<<result.monitored_targets<<",\\\"cpu_us\\\":"<<helper_cpu<<",\\\"wall_us\\\":"<<helper_wall')
driver=driver.replace('    SchedulePlan whole;', '    auto whole_cpu_before=thread_cpu_us();auto whole_wall_before=std::chrono::steady_clock::now();\n    SchedulePlan whole;')
driver=driver.replace('    if(returned){sim=', '    auto whole_cpu=thread_cpu_us()-whole_cpu_before;auto whole_wall=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-whole_wall_before).count();\n    if(returned){sim=')
driver=driver.replace('<<sim.peak_memory<<",\\\"plan\\\":"', '<<sim.peak_memory<<",\\\"cpu_us\\\":"<<whole_cpu<<",\\\"wall_us\\\":"<<whole_wall<<",\\\"plan\\\":"')
(OUT/'selected-driver.cpp').write_text(driver)
manifest={'candidate':'R62','default_changed':False,'work_limit':128000000,'beam_width':64,'ranking_styles':['live_peak_area','peak_live_area','area_live_peak','live_per_completed_node'],
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
