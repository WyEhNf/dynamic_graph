"""Isolated macro normalization candidate, no fixture/witness changes."""
from pathlib import Path

base=Path('research/batch37');base.mkdir(parents=True,exist_ok=True)
s=Path('research/batch36/solution.cpp').read_text()
s=s.replace('bool paired=false,bool greedy=false) {','bool paired=false,bool greedy=false,bool inside_normalize=false) {',1)
old='''      for(int i:closure)if(!done[i]) {
        if(!charge(1+static_cast<I>(g.in[i].size()))){fit=false;break;}
        if(!fits(i)){fit=false;break;}
        peak=std::max(peak,live+g.v[i].workspace_memory+g.v[i].output_memory);apply(i);
        if(result.exhausted){fit=false;break;}
      }'''
new='''      for(int i:closure) {
        // A safe ready consumer outside this closure may free an opened
        // producer before the next allocation. Record every actual action
        // for exact rollback, without adding dependencies or release credit.
        if(inside_normalize)while(true) {
          int safe=-1;
          for(int j:ready) {
            if(!charge(1+static_cast<I>(g.in[j].size()))){fit=false;break;}
            if(fits(j) && impact(j)<=0){safe=j;break;}
          }
          if(!fit || safe<0)break;
          peak=std::max(peak,live+g.v[safe].workspace_memory+g.v[safe].output_memory);
          apply(safe);
          if(result.exhausted){fit=false;break;}
        }
        if(!fit)break;
        if(done[i])continue;
        if(!charge(1+static_cast<I>(g.in[i].size()))){fit=false;break;}
        if(!fits(i)){fit=false;break;}
        peak=std::max(peak,live+g.v[i].workspace_memory+g.v[i].output_memory);apply(i);
        if(result.exhausted){fit=false;break;}
      }'''
assert old in s;s=s.replace(old,new,1)
old='''    if(static_cast<int>(searched.order.size())!=graph.n)searched=serial_frontier_search(hw,graph,8000000,true,true);'''
new=old+'''
    if(static_cast<int>(searched.order.size())!=graph.n)searched=serial_frontier_search(hw,graph,8000000,true,true,true);'''
assert old in s;s=s.replace(old,new,1)
(base/'solution.cpp').write_text(s)
probe=Path('src/frontier_probe.cpp').read_text().replace('#include "../solution/solution.cpp"','#include "solution.cpp"').replace('serial_frontier_search(h,g,limit,true,true)','serial_frontier_search(h,g,limit,true,true,true)')
(base/'frontier_probe.cpp').write_text(probe)
test=Path('tests/test_serial_frontier.cpp').read_text().replace('#include "../solution/solution.cpp"','#include "solution.cpp"').replace('serial_frontier_search(h,g,20000000,true)','serial_frontier_search(h,g,20000000,true,false,true)')
(base/'serial_frontier_tests.cpp').write_text(test)
print('Created isolated batch37 candidate and independent test/probe entrypoints')
