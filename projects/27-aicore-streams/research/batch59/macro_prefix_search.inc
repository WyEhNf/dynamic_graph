// Input-only beam over workspace-target completions. The original graph is
// never contracted: every BEGIN, output and direct-user release is replayed.
// Beam truncation and greedy closure order are heuristic, never certificates.
struct MacroPrefixResult {
  std::vector<int> order; I work=0,prunes=0,states=0,memo_hits=0,safe_steps=0;
  bool exhausted=false,intrinsic_blocked=false; int monitored_targets=0;
};
MacroPrefixResult macro_prefix_search(const HardwareInfo& h,const Graph& g,I limit=32000000,int width=32) {
  MacroPrefixResult result;if(g.n>4096 || limit<1 || width<1)return result;
  auto charge=[&](I amount=1){if(amount>limit-result.work){result.exhausted=true;return false;}result.work+=amount;return true;};
  auto projection=workspace_projection(g);auto& targets=projection.targets;
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
    if(!charge(1+static_cast<I>(g.in[node].size())))return false;
    for(int p:g.in[node])if(!s.done[p])return false;
    const auto& v=g.v[node];
    if(!memory_fits(h.memory_limit,s.live,v.workspace_memory,v.output_memory)){++result.prunes;return false;}
    I allocation=s.live+v.workspace_memory+v.output_memory;s.peak=std::max(s.peak,allocation);s.area=positive_add(s.area,allocation);
    s.live+=v.output_memory;s.done[node]=1;s.mask[node/64]|=1ull<<(node%64);s.order.push_back(node);
    for(int p:g.in[node])if(!--s.users[p])s.live-=g.v[p].output_memory;
    return true;
  };
  std::vector<State> beam;beam.push_back(std::move(initial));
  for(int depth=0;depth<k;++depth) {
    std::vector<State> next;std::set<std::vector<unsigned long long>> seen;
    for(const auto& state:beam)for(int q=0;q<k;++q) {
      if(!charge(1+static_cast<I>(projection.predecessors[q].size())))return result;
      if(state.done[targets[q]])continue;
      bool ready=true;for(int p:projection.predecessors[q])if(!state.done[targets[p]])ready=false;if(!ready)continue;
      if(!charge(2*static_cast<I>(g.n)+static_cast<I>(state.order.size()+state.mask.size())))return result;
      State candidate=state;++result.states;
      for(int i:projection.closures[q])if(!append(candidate,i)){ready=false;break;}
      if(result.exhausted)return result;if(!ready)continue;
      if(!seen.insert(candidate.mask).second){++result.memo_hits;continue;}
      next.push_back(std::move(candidate));
    }
    if(next.empty())return result;
    auto less=[](const State& a,const State& b){return std::tie(a.live,a.peak,a.area,a.mask)<std::tie(b.live,b.peak,b.area,b.mask);};
    std::stable_sort(next.begin(),next.end(),less);if(next.size()>static_cast<size_t>(width))next.resize(width);
    beam=std::move(next);
  }
  for(auto& state:beam) {
    bool fits=true;for(int i:g.topo)if(!append(state,i)){fits=false;break;}
    if(fits && state.order.size()==static_cast<size_t>(g.n)){result.order=std::move(state.order);return result;}
    if(result.exhausted)return result;
  }
  return result;
}
