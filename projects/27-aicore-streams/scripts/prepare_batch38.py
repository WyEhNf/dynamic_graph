"""Strict fork/join structure candidate; derives all boundaries from input."""
from pathlib import Path

base=Path('research/batch38');base.mkdir(parents=True,exist_ok=True)
s=Path('research/batch37/solution.cpp').read_text(encoding='utf-8')
helper=r'''
// Recognize a complete nested fork/join component. Every fork keeps its own
// original direct edge to the join; a branch has no boundary-crossing users.
// Optimize ONLY the two contiguous branch orders, not arbitrary interleavings
// or dominant profiles. A final evaluator remains the feasibility authority.
std::vector<int> strict_fork_join_order(const Graph& g) {
  if(g.n>4096)return {};
  std::vector<int> roots;for(int i=0;i<g.n;++i)if(g.in[i].empty())roots.push_back(i);
  if(roots.size()!=1)return {};
  struct Block {bool valid=false;int terminal=-1;I peak=0,output=0;std::vector<int> order;};
  std::vector<unsigned char> visited(g.n);
  std::function<Block(int,int,int,int)> parse;
  parse=[&](int root,int parent,int consumer,int depth)->Block {
    if(depth>512 || visited[root])return {};
    if(parent<0 ? !g.in[root].empty() : (g.in[root].size()!=1 || g.in[root][0]!=parent))return {};
    visited[root]=1;
    if(g.out[root].size()<=1) {
      if(consumer<0 ? !g.out[root].empty() : (g.out[root].size()!=1 || g.out[root][0]!=consumer))return {};
      return {true,root,positive_add(g.v[root].workspace_memory,g.v[root].output_memory),g.v[root].output_memory,{root}};
    }
    if(g.out[root].size()!=3)return {};
    int join=-1;std::vector<int> children;
    for(int c:g.out[root]) {
      if(g.in[c].size()==3) {if(join>=0)return {};join=c;}
      else children.push_back(c);
    }
    if(join<0 || children.size()!=2 || visited[join])return {};
    if(consumer<0 ? !g.out[join].empty() : (g.out[join].size()!=1 || g.out[join][0]!=consumer))return {};
    auto a=parse(children[0],root,join,depth+1);if(!a.valid)return {};
    auto b=parse(children[1],root,join,depth+1);if(!b.valid)return {};
    std::vector<int> actual=g.in[join],expected{root,a.terminal,b.terminal};
    std::sort(actual.begin(),actual.end());std::sort(expected.begin(),expected.end());if(actual!=expected)return {};
    visited[join]=1;
    I fork_output=g.v[root].output_memory;
    auto peak_order=[&](const Block& first,const Block& second) {
      I p=positive_add(g.v[root].workspace_memory,fork_output);
      p=std::max(p,positive_add(fork_output,first.peak));
      p=std::max(p,positive_add(fork_output,positive_add(first.output,second.peak)));
      I at_join=positive_add(fork_output,positive_add(a.output,b.output));
      at_join=positive_add(at_join,positive_add(g.v[join].workspace_memory,g.v[join].output_memory));
      return std::max(p,at_join);
    };
    I ab=peak_order(a,b),ba=peak_order(b,a);
    if(ba<ab || (ba==ab && g.v[children[1]].id<g.v[children[0]].id))std::swap(a,b);
    Block r{true,join,std::min(ab,ba),g.v[join].output_memory,{root}};
    r.order.insert(r.order.end(),a.order.begin(),a.order.end());
    r.order.insert(r.order.end(),b.order.begin(),b.order.end());r.order.push_back(join);return r;
  };
  auto result=parse(roots[0],-1,-1,0);
  if(!result.valid || result.order.size()!=static_cast<size_t>(g.n))return {};
  return result.order;
}

'''
assert 'struct SerialFrontierResult {' in s
s=s.replace('struct SerialFrontierResult {',helper+'struct SerialFrontierResult {',1)
needle='''  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
  if(!found) throw std::runtime_error'''
new='''  if(!found && graph.n<=4096) {
    auto order=strict_fork_join_order(graph);
    if(static_cast<int>(order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,order,s,0);
        consider(order,assignment,s);consider(order,assignment,s,2);
      }
    }
  }
'''+needle
assert needle in s;s=s.replace(needle,new,1)
(base/'solution.cpp').write_text(s,encoding='utf-8')
print('Created isolated batch38 strict fork/join candidate')
