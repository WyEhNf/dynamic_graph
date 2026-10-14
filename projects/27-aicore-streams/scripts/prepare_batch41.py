"""Resource-only candidate. Remove unproductive large-graph search, keep paths."""
from pathlib import Path
base=Path('research/batch41');base.mkdir(parents=True,exist_ok=True)
s=Path('research/batch40/solution.cpp').read_text(encoding='utf-8')
s=s.replace('bool inside_normalize=false,int node_limit=768)','bool inside_normalize=false)',1).replace('if(g.n>node_limit)return result;','if(g.n>768)return result;',1)
old='''  int search_depth=0;
  struct DepthGuard {int& depth;explicit DepthGuard(int& d):depth(d){++depth;}~DepthGuard(){--depth;}};
  std::function<bool()> search;
  search=[&]() {
    // Larger graphs must not grow the native recursion stack without bound.
    // Hitting this cap is policy truncation, never an infeasibility proof.
    if(g.n>768 && search_depth>=384 && order.size()!=static_cast<size_t>(g.n)) {result.exhausted=true;return false;}
    DepthGuard depth_guard(search_depth);
    const size_t prefix=order.size();'''
new='''  std::function<bool()> search;
  search=[&]() {
    const size_t prefix=order.size();'''
assert old in s;s=s.replace(old,new,1)
start=s.rindex('  if(!found && graph.n>768 && graph.n<=2048) {')
end=s.index('  metrics.micros=',start);s=s[:start]+s[end:]
start=s.index('std::vector<int> strict_fork_join_order(');end=s.index('struct SerialFrontierResult',start)
h=s[start:end]
h=h.replace('I peak=0,output=0;std::vector<int> order;','I peak=0,output=0;',1)
h=h.replace('  std::vector<unsigned char> visited(g.n);','  std::vector<unsigned char> visited(g.n);\n  std::vector<int> first_root(g.n,-1),second_root(g.n,-1),join_node(g.n,-1);',1)
h=h.replace('g.v[root].output_memory,{root}};','g.v[root].output_memory};',1)
old='''    if(ba<ab || (ba==ab && g.v[children[1]].id<g.v[children[0]].id))std::swap(a,b);
    Block r{true,join,std::min(ab,ba),g.v[join].output_memory,{root}};
    r.order.insert(r.order.end(),a.order.begin(),a.order.end());
    r.order.insert(r.order.end(),b.order.begin(),b.order.end());r.order.push_back(join);return r;'''
new='''    first_root[root]=children[0];second_root[root]=children[1];join_node[root]=join;
    if(ba<ab || (ba==ab && g.v[children[1]].id<g.v[children[0]].id))std::swap(first_root[root],second_root[root]);
    return {true,join,std::min(ab,ba),g.v[join].output_memory};'''
assert old in h;h=h.replace(old,new,1)
old='''  if(!result.valid || result.order.size()!=static_cast<size_t>(g.n))return {};
  return result.order;'''
new='''  if(!result.valid || std::count(visited.begin(),visited.end(),static_cast<unsigned char>(1))!=g.n)return {};
  // Emit the selected profile in one explicit traversal. No subtree order
  // vector is repeatedly copied through its ancestors. Negative markers are
  // complements of valid node indices and emit only the original join node.
  std::vector<int> order,stack{roots[0]};order.reserve(g.n);
  while(!stack.empty()) {
    int i=stack.back();stack.pop_back();
    if(i<0){order.push_back(~i);continue;}
    order.push_back(i);
    if(join_node[i]>=0) {stack.push_back(~join_node[i]);stack.push_back(second_root[i]);stack.push_back(first_root[i]);}
  }
  if(order.size()!=static_cast<size_t>(g.n))return {};
  return order;'''
assert old in h;h=h.replace(old,new,1)
s=s[:start]+h+s[end:]
(base/'solution.cpp').write_text(s,encoding='utf-8')
test=Path('tests/test_serial_frontier.cpp').read_text(encoding='utf-8').replace('#include "../solution/solution.cpp"','#include "solution.cpp"')
(base/'serial_frontier_tests.cpp').write_text(test,encoding='utf-8')
dual=Path('research/batch40/streaming_equivalence.cpp').read_text(encoding='utf-8')
dual=dual.replace('int checked=0;','int checked=0,structural=0;',1)
dual=dual.replace('''    if(nodes.size()>768)continue;
    old_detail::Graph old_g(h,nodes);aicore_detail::Graph g(h,nodes);''','''    old_detail::Graph old_g(h,nodes);aicore_detail::Graph g(h,nodes);
    if(old_detail::strict_fork_join_order(old_g)!=aicore_detail::strict_fork_join_order(g)) {std::cerr<<"Structure emit mismatch: "<<c.at("name").text()<<'\\n';return 1;}
    ++structural;
    if(nodes.size()>768)continue;''',1)
dual=dual.replace('exact greedy path/work/state/truncation comparisons\\n','exact greedy path/work/state/truncation comparisons; structural orders="<<structural<<"\\n',1)
(base/'streaming_equivalence.cpp').write_text(dual,encoding='utf-8')
print('Created isolated batch41 resource-only candidate; no default changes')
