WorkspaceProjection macro_workspace_projection(const Graph& g) {
  WorkspaceProjection s;if(g.n>4096)return s;
  std::vector<I> positive;
  for(const auto& v:g.v)if(v.workspace_memory)positive.push_back(v.workspace_memory);
  if(positive.empty())return s;
  std::sort(positive.begin(),positive.end());
  I threshold=std::max<I>(1,positive.back()/4);
  s.position.assign(g.n,-1);
  for(int i:g.topo)if(g.in[i].size()>=2 && g.v[i].workspace_memory>=threshold) {
    I previous=0;for(int p:g.in[i])previous=std::max(previous,g.v[p].workspace_memory);
    if(g.v[i].workspace_memory>previous){s.position[i]=static_cast<int>(s.targets.size());s.targets.push_back(i);}
  }
  if(s.targets.size()<2 || s.targets.size()>1024)return {};
  int k=static_cast<int>(s.targets.size());s.closures.resize(k);s.predecessors.resize(k);s.successors.resize(k);
  s.unit=g.n+static_cast<I>(k)*k;
  for(const auto& x:g.in)s.unit+=static_cast<I>(x.size());
  for(int q=0;q<k;++q) {
    std::vector<unsigned char> seen(g.n);std::vector<int> stack{s.targets[q]};
    std::set<int> parents;
    while(!stack.empty()) {
      int i=stack.back();stack.pop_back();if(seen[i])continue;seen[i]=1;
      if(s.position[i]>=0 && s.position[i]!=q){parents.insert(s.position[i]);continue;}
      for(int p:g.in[i])stack.push_back(p);
    }
    for(int i:g.topo)if(seen[i] && (s.position[i]<0 || s.position[i]==q))s.closures[q].push_back(i);
    s.unit+=static_cast<I>(s.closures[q].size());
    s.predecessors[q].assign(parents.begin(),parents.end());for(int p:parents)s.successors[p].push_back(q);
  }
  return s;
}
// Input-only beam over workspace-target completions. The original graph is
// never contracted: every BEGIN, output and direct-user release is replayed.
// Beam truncation and greedy closure order are heuristic, never certificates.
struct MacroPrefixResult {
  std::vector<int> order; I work=0,prunes=0,states=0,memo_hits=0,safe_steps=0;
  bool exhausted=false,intrinsic_blocked=false; int monitored_targets=0;
};
MacroPrefixResult macro_prefix_search(const HardwareInfo& h,const Graph& g,I limit=128000000,int width=64,int style=0) {
  MacroPrefixResult result;if(g.n>4096 || limit<1 || width<1)return result;
  auto charge=[&](I amount=1){if(amount>limit-result.work){result.exhausted=true;return false;}result.work+=amount;return true;};
  auto projection=macro_workspace_projection(g);auto& targets=projection.targets;
  const int k=static_cast<int>(targets.size());if(!k)return result;
  if(!charge(projection.unit))return result;
  result.monitored_targets=k;
  struct State {
    std::vector<unsigned char> done;std::vector<int> users,order;
    std::vector<unsigned long long> mask;I live=0,peak=0,area=0;
  };
  State initial;initial.done.resize(g.n);initial.users.resize(g.n);initial.mask.resize((g.n+63)/64);
  for(int i=0;i<g.n;++i)initial.users[i]=static_cast<int>(g.out[i].size());
  auto append=[&](State& s,int node) {
    if(s.done[node])return true;
    if(!charge(2*(1+static_cast<I>(g.in[node].size()))))return false;
    for(int p:g.in[node])if(!s.done[p])return false;
    const auto& v=g.v[node];
    if(!memory_fits(h.memory_limit,s.live,v.workspace_memory,v.output_memory)){++result.prunes;return false;}
    I allocation=s.live+v.workspace_memory+v.output_memory;s.peak=std::max(s.peak,allocation);s.area=positive_add(s.area,allocation);
    s.live+=v.output_memory;s.done[node]=1;s.mask[node/64]|=1ull<<(node%64);s.order.push_back(node);
    for(int p:g.in[node])if(!--s.users[p])s.live-=g.v[p].output_memory;
    return true;
  };
  auto less=[&](const State& a,const State& b){
    if(style==1)return std::tie(a.peak,a.live,a.area,a.mask)<std::tie(b.peak,b.live,b.area,b.mask);
    if(style==2)return std::tie(a.area,a.live,a.peak,a.mask)<std::tie(b.area,b.live,b.peak,b.mask);
    if(style==3){
      I av=priority_mul_div(a.live,static_cast<I>(g.n),std::max<size_t>(1,a.order.size()));
      I bv=priority_mul_div(b.live,static_cast<I>(g.n),std::max<size_t>(1,b.order.size()));
      if(av!=bv)return av<bv;
    }
    return std::tie(a.live,a.peak,a.area,a.mask)<std::tie(b.live,b.peak,b.area,b.mask);
  };
  auto rollback=[&](State& s,size_t length,I live,I peak,I area) {
    while(s.order.size()>length) {
      int i=s.order.back();s.order.pop_back();s.done[i]=0;s.mask[i/64]&=~(1ull<<(i%64));
      for(int p:g.in[i])++s.users[p];
    }
    s.live=live;s.peak=peak;s.area=area;
  };
  std::vector<State> beam;beam.push_back(std::move(initial));
  for(int depth=0;depth<k;++depth) {
    std::vector<State> next;std::set<std::vector<unsigned long long>> seen;
    for(auto& state:beam)for(int q=0;q<k;++q) {
      if(!charge(1+static_cast<I>(projection.predecessors[q].size())))return result;
      if(state.done[targets[q]])continue;
      bool ready=true;for(int p:projection.predecessors[q])if(!state.done[targets[p]])ready=false;if(!ready)continue;
      const size_t length=state.order.size();const I live=state.live,peak=state.peak,area=state.area;++result.states;
      for(int i:projection.closures[q])if(!append(state,i)){ready=false;break;}
      if(result.exhausted)return result;
      // Reserve rollback cost; even rejected partial closures restore all users.
      if(!charge(static_cast<I>(state.order.size()-length))){rollback(state,length,live,peak,area);return result;}
      if(ready) {
        if(!charge(static_cast<I>(state.mask.size()))){rollback(state,length,live,peak,area);return result;}
        if(!seen.insert(state.mask).second)++result.memo_hits;
        else if(next.size()<static_cast<size_t>(width) || less(state,next.front())) {
          if(!charge(2*static_cast<I>(g.n)+static_cast<I>(state.order.size()+state.mask.size()))){rollback(state,length,live,peak,area);return result;}
          if(next.size()==static_cast<size_t>(width)){std::pop_heap(next.begin(),next.end(),less);next.pop_back();}
          next.push_back(state);std::push_heap(next.begin(),next.end(),less);
        }
      }
      rollback(state,length,live,peak,area);
    }
    if(next.empty())return result;
    std::sort(next.begin(),next.end(),less);beam=std::move(next);
  }
  for(auto& state:beam) {
    bool fits=true;for(int i:g.topo)if(!append(state,i)){fits=false;break;}
    if(fits && state.order.size()==static_cast<size_t>(g.n)){result.order=std::move(state.order);return result;}
    if(result.exhausted)return result;
  }
  return result;
}
