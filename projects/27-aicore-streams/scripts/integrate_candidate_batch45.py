from pathlib import Path
import hashlib
p=Path('research/batch45/solution.cpp');s=p.read_text(encoding='utf-8')
marker='  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();\n  if(!found) throw'
code='''  if(!found && graph.n<=4096) {
    auto searched=projection_memory_search(hw,graph);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
'''
assert marker in s and 'auto searched=projection_memory_search(hw,graph);' not in s
p.write_text(s.replace(marker,code+marker),encoding='utf-8');print(hashlib.sha256(p.read_bytes()).hexdigest())
