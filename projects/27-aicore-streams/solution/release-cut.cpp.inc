// Current-frontier release cut. The producer is already completed; every
// remaining ORIGINAL DIRECT user and its unfinished ancestors are included.
// No dependency rewriting, consumer fusion, workspace thresholds or seeds.
struct ReleaseCut {
  std::vector<int> pending,order;
  I peak=0,final_live=0;
  bool valid=false,exhausted=false;
};
bool cut_charge(I& work,I limit,I amount) {
  if(amount>limit-work){work=limit;return false;}
  work+=amount;return true;
}
ReleaseCut release_cut_probe(const HardwareInfo& h,const Graph& g,int producer,
 const std::vector<unsigned char>& completed,const std::vector<int>& remaining_users,
 const std::vector<int>& remaining_degree,I live,I& work,I limit) {
  ReleaseCut r;r.peak=r.final_live=live;
  auto charge=[&](I amount){if(!cut_charge(work,limit,amount)){r.exhausted=true;return false;}return true;};
  if(!charge(1))return r;
  if(!completed[producer] || !g.v[producer].output_memory || g.out[producer].empty() || !remaining_users[producer])return r;
  if(!charge(4*static_cast<I>(g.n)))return r;
  std::vector<unsigned char> included(g.n),done=completed;
  std::vector<int> stack,users=remaining_users,degree=remaining_degree;
  for(int c:g.out[producer]){if(!charge(1))return r;if(!done[c])stack.push_back(c);}
  int count=0;
  while(!stack.empty()) {
    int i=stack.back();stack.pop_back();if(!charge(1))return r;
    if(done[i] || included[i])continue;included[i]=1;
    if(++count>128)return r; // Optional ordering accelerator, not a certificate.
    for(int p:g.in[i]){if(!charge(1))return r;if(!done[p])stack.push_back(p);}
  }
  for(int i:g.topo){if(!charge(1))return r;if(included[i])r.pending.push_back(i);}
  while(r.order.size()<r.pending.size()) {
    int selected=-1;std::tuple<I,I,I> best;
    for(int i:r.pending) {
      if(!charge(1))return r;
      if(done[i] || degree[i])continue;
      const auto& v=g.v[i];if(!memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory))continue;
      I freed=0;
      for(int p:g.in[i]){if(!charge(1))return r;if(users[p]==1)freed+=g.v[p].output_memory;}
      // freed is a subset of physically held live outputs, so is <=live.
      auto score=std::make_tuple(v.output_memory-freed,positive_add(v.workspace_memory,v.output_memory),static_cast<I>(v.id));
      if(selected<0 || score<best){selected=i;best=score;}
    }
    if(selected<0)return r;
    int i=selected;const auto& v=g.v[i];
    r.peak=std::max(r.peak,live+v.workspace_memory+v.output_memory);
    live+=v.output_memory;done[i]=1;r.order.push_back(i);
    for(int p:g.in[i]){if(!charge(1))return r;if(!--users[p])live-=g.v[p].output_memory;}
    for(int c:g.out[i]){if(!charge(1))return r;--degree[c];}
  }
  // All original remaining direct users must have completed. In particular,
  // an outside/non-interface user is not silently omitted from this check.
  if(users[producer])return r;
  r.final_live=live;r.valid=true;return r;
}
ShallowResult release_cut_order(const HardwareInfo& h,const Graph& g,I limit) {
  ShallowResult r;if(g.n>4096)return r;
  if(!cut_charge(r.work,limit,3*static_cast<I>(g.n))){r.exhausted=true;return r;}
  std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n);
  for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
  I live=0,peak=0;std::vector<int> prefix;
  auto charge=[&](I amount){if(!cut_charge(r.work,limit,amount)){r.exhausted=true;return false;}return true;};
  auto impact=[&](int i,I& net) {
    I freed=0;for(int p:g.in[i]){if(!charge(1))return false;if(users[p]==1)freed+=g.v[p].output_memory;}
    net=g.v[i].output_memory-freed;return true;
  };
  auto apply=[&](int i) {
    if(!charge(1+static_cast<I>(g.in[i].size()+g.out[i].size())))return false;
    if(done[i] || degree[i] || !memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory))return false;
    peak=std::max(peak,live+g.v[i].workspace_memory+g.v[i].output_memory);
    live+=g.v[i].output_memory;done[i]=1;prefix.push_back(i);
    for(int p:g.in[i])if(!--users[p])live-=g.v[p].output_memory;
    for(int c:g.out[i])--degree[c];return true;
  };
  while(prefix.size()<static_cast<size_t>(g.n)) {
    int safe=-1,single=-1;std::tuple<I,I,I> best;
    std::vector<int> held;
    for(int i=0;i<g.n;++i) {
      if(!charge(1))return r;
      if(done[i]){if(users[i] && g.v[i].output_memory)held.push_back(i);continue;}
      if(degree[i] || !memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory))continue;
      I net;if(!impact(i,net))return r;
      auto score=std::make_tuple(net,positive_add(g.v[i].workspace_memory,g.v[i].output_memory),static_cast<I>(g.v[i].id));
      if(single<0 || score<best){single=i;best=score;}
      if(net<=0 && (safe<0 || g.v[i].id<g.v[safe].id))safe=i;
    }
    if(safe>=0){if(!apply(safe))return r;continue;}
    bool sort_budget=true;
    std::stable_sort(held.begin(),held.end(),[&](int a,int b){if(!charge(1))sort_budget=false;return g.v[a].output_memory!=g.v[b].output_memory?g.v[a].output_memory>g.v[b].output_memory:g.v[a].id<g.v[b].id;});
    if(!sort_budget)return r;if(held.size()>24)held.resize(24);
    ReleaseCut selected;bool have=false;
    for(int p:held) {
      auto candidate=release_cut_probe(h,g,p,done,users,degree,live,r.work,limit);++r.evaluations;
      if(candidate.exhausted){r.exhausted=true;return r;}
      if(candidate.valid && (!have || std::tie(candidate.final_live,candidate.peak)<std::tie(selected.final_live,selected.peak))) {selected=std::move(candidate);have=true;}
    }
    if(have){for(int i:selected.order)if(!apply(i))return r;}
    else {if(single<0 || !apply(single))return r;}
  }
  r.order=std::move(prefix);r.best_peak=ProfileInteger(peak);return r;
}
