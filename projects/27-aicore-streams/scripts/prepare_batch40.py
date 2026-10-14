"""Next isolated candidate: retain only greedy best macro, bounded larger graphs.

Streaming keeps tie order and all evaluations unchanged. Exact diagnostic mode
continues to retain all alternatives. The original <=768 path is preserved;
larger graph recovery is an extra late, explicit-work-budget heuristic.
"""
from pathlib import Path
base=Path('research/batch40');base.mkdir(parents=True,exist_ok=True)
s=Path('research/batch39/solution.cpp').read_text(encoding='utf-8')
s=s.replace('bool inside_normalize=false) {','bool inside_normalize=false,int node_limit=768) {',1)
s=s.replace('if(g.n>768)return result;','if(g.n>node_limit)return result;',1)
s=s.replace('''  std::function<bool()> search;
  search=[&]() {
    const size_t prefix=order.size();''','''  int search_depth=0;
  struct DepthGuard {int& depth;explicit DepthGuard(int& d):depth(d){++depth;}~DepthGuard(){--depth;}};
  std::function<bool()> search;
  search=[&]() {
    // Larger graphs must not grow the native recursion stack without bound.
    // Hitting this cap is policy truncation, never an infeasibility proof.
    if(g.n>768 && search_depth>=384 && order.size()!=static_cast<size_t>(g.n)) {result.exhausted=true;return false;}
    DepthGuard depth_guard(search_depth);
    const size_t prefix=order.size();''',1)
s=s.replace('std::set<std::vector<int>> seen_macro;','std::set<std::vector<unsigned long long>> seen_macro;',1)
old='''      std::vector<int> pending;for(int i:closure)if(!done[i])pending.push_back(i);
      if(pending.size()<2 || !seen_macro.insert(pending).second)continue;'''
new='''      std::vector<unsigned long long> pending(words);size_t pending_count=0;
      for(int i:closure)if(!done[i]){pending[i/64]|=1ull<<(i%64);++pending_count;}
      if(pending_count<2 || !seen_macro.insert(pending).second)continue;'''
assert old in s;s=s.replace(old,new,1)
old='''      if(fit && order.size()>begin+1)macros.push_back({std::vector<int>(order.begin()+begin,order.end()),live,peak});'''
new='''      if(fit && order.size()>begin+1) {
        // In greedy mode only the first stable-sorted macro can be used;
        // streaming the minimum avoids storing every candidate at each depth.
        if(!greedy)macros.push_back({std::vector<int>(order.begin()+begin,order.end()),live,peak});
        else if(macros.empty() || std::tie(live,peak)<std::tie(macros[0].final_live,macros[0].peak)) {
          Macro best{std::vector<int>(order.begin()+begin,order.end()),live,peak};
          if(macros.empty())macros.push_back(std::move(best));else macros[0]=std::move(best);
        }
      }'''
assert old in s;s=s.replace(old,new,1)
needle='''  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
  if(!found) throw std::runtime_error'''
new='''  if(!found && graph.n>768 && graph.n<=2048) {
    // No co-consumer pair construction at this scale: high fanout makes its
    // quadratic affinity enumeration an unsuitable default preprocessing cost.
    auto searched=serial_frontier_search(hw,graph,8000000,false,true,false,2048);
    if(static_cast<int>(searched.order.size())!=graph.n)searched=serial_frontier_search(hw,graph,8000000,false,true,true,2048);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
'''+needle
assert needle in s;s=s.replace(needle,new,1)
(base/'solution.cpp').write_text(s,encoding='utf-8')
test=Path('tests/test_serial_frontier.cpp').read_text(encoding='utf-8').replace('#include "../solution/solution.cpp"','#include "solution.cpp"')
(base/'serial_frontier_tests.cpp').write_text(test,encoding='utf-8')
print('Created isolated batch40; no default changes')
