from pathlib import Path
import hashlib
p=Path('research/batch44');p.mkdir(exist_ok=True)
s=Path('research/batch43/solution.cpp').read_text(encoding='utf-8')
code=(p/'shallow.cpp.inc').read_text(encoding='utf-8')
s=s.replace('std::vector<int> sink_projection_order(',code+'\nstd::vector<int> sink_projection_order(',1)
marker='  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();\n  if(!found) throw'
replacement='''  if(!found && graph.n<=4096) {
    auto searched=shallow_memory_search(hw,graph);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
'''+marker
assert marker in s;s=s.replace(marker,replacement)
(p/'solution.cpp').write_text(s,encoding='utf-8')
print(hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest())
