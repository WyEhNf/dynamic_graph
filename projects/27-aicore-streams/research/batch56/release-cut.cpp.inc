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
// One diagnostic pair, selected only from an actual failed original prefix.
// Original graph reachability and ORIGINAL direct users are never rewritten.
struct CausalDeferralPair {
  int producer=-1,target=-1;
  bool complete=false,exhausted=false;
};
CausalDeferralPair causal_deferral_pair(const HardwareInfo& h,const Graph& g,
 const std::vector<unsigned char>& done,const std::vector<int>& users,
 const std::vector<int>& prefix,const std::vector<int>& held,I& work,I limit) {
  CausalDeferralPair r;
  auto charge=[&](I amount) {
    if(cut_charge(work,limit,amount))return true;
    r.producer=r.target=-1;r.complete=false;r.exhausted=true;return false;
  };
  if(!charge(4))return r; // entry/result fields, including invalid-on-exhaustion
  if(!charge(g.n))return r;
  std::vector<unsigned char> eligible(g.n);
  for(int p:held){if(!charge(1))return r;eligible[p]=1;}
  std::tuple<I,I,I> best;
  for(int j:g.topo) {
    if(!charge(1))return r;
    if(done[j])continue; // Unfinished targets include targets not yet ready.
    if(!charge(3*static_cast<I>(g.n)))return r;
    std::vector<unsigned char> ancestor(g.n),descendant(g.n),pinned(g.n);
    std::vector<int> stack;
    if(!charge(4))return r;ancestor[j]=1;stack.push_back(j);
    while(!stack.empty()) {
      if(!charge(1))return r;int i=stack.back();stack.pop_back();
      for(int p:g.in[i]) {
        if(!charge(1))return r;
        if(!ancestor[p]){if(!charge(2))return r;ancestor[p]=1;stack.push_back(p);}
      }
    }
    if(!charge(4))return r;descendant[j]=1;stack.push_back(j);
    while(!stack.empty()) {
      if(!charge(1))return r;int i=stack.back();stack.pop_back();
      for(int c:g.out[i]) {
        if(!charge(1))return r;
        if(!descendant[c]){if(!charge(2))return r;descendant[c]=1;stack.push_back(c);}
      }
    }
    if(!charge(3))return r;
    ProfileInteger forced(g.v[j].workspace_memory);forced+=ProfileInteger(g.v[j].output_memory);
    for(int p=0;p<g.n;++p) {
      if(!charge(1))return r;
      if(p==j || !g.v[p].output_memory)continue;
      bool retain=g.out[p].empty(); // Original sink O retained until graph T.
      for(int c:g.out[p]) {
        if(!charge(1))return r;
        if(descendant[c]){retain=true;break;}
      }
      if(retain) {
        if(!charge(1))return r;pinned[p]=1;
        if(ancestor[p]){if(!charge(2))return r;forced+=ProfileInteger(g.v[p].output_memory);}
      }
    }
    if(!charge(1))return r;
    if(ProfileInteger(h.memory_limit)<forced)continue; // No first prefix crossing.
    bool crossed=false;I step=0;
    for(int p:prefix) {
      if(!charge(1))return r;
      if(pinned[p] && !ancestor[p]) {
        if(!charge(2))return r;forced+=ProfileInteger(g.v[p].output_memory);
        if(!charge(1))return r;
        if(!crossed && ProfileInteger(h.memory_limit)<forced) {
          if(!charge(6))return r;crossed=true;
          // Only existing held top24; original positive-output/user eligibility.
          // Both directions of original reachability must exclude the pair.
          if(eligible[p] && done[p] && g.v[p].output_memory && users[p] &&
             !ancestor[p] && !descendant[p]) {
            if(!charge(3))return r;
            auto score=std::make_tuple(step,static_cast<I>(g.v[j].id),static_cast<I>(g.v[p].id));
            if(r.producer<0 || score<best) {
              if(!charge(5))return r;best=score;r.producer=p;r.target=j;
            }
          }
        }
      }
      ++step;
    }
    // No early best-pair return: all targets/prefixes must finish paid scanning.
  }
  if(!charge(1))return r;r.complete=true;return r;
}

ReleaseCut release_cut_probe_guarded(const HardwareInfo& h,const Graph& g,int producer,
 const std::vector<unsigned char>& completed,const std::vector<int>& remaining_users,
 const std::vector<int>& remaining_degree,I live,I& work,I limit,int delayed,int target) {
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
      if(!charge(2))return r;if(i==delayed && !done[target])continue;
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

ShallowResult release_cut_order_guarded(const HardwareInfo& h,const Graph& g,I limit,int delayed,int target) {
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
    if(!charge(2))return false;if(i==delayed && !done[target])return false;
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
      if(!charge(2))return r;if(i==delayed && !done[target])continue;
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
      auto candidate=release_cut_probe_guarded(h,g,p,done,users,degree,live,r.work,limit,delayed,target);++r.evaluations;
      if(candidate.exhausted){r.exhausted=true;return r;}
      if(candidate.valid && (!have || std::tie(candidate.final_live,candidate.peak)<std::tie(selected.final_live,selected.peak))) {selected=std::move(candidate);have=true;}
    }
    if(have){for(int i:selected.order)if(!apply(i))return r;}
    else {if(single<0 || !apply(single))return r;}
  }
  r.order=std::move(prefix);r.best_peak=ProfileInteger(peak);return r;
}

// Retry at most once. This function is never called by the guarded copy.
ShallowResult causal_deferral_restart(const HardwareInfo& h,const Graph& g,
 const std::vector<unsigned char>& done,const std::vector<int>& users,
 const std::vector<int>& prefix,const std::vector<int>& held,I& work,I limit,int evaluations) {
  ShallowResult answer;answer.evaluations=evaluations;
  auto charge=[&](I amount){if(cut_charge(work,limit,amount))return true;answer.order.clear();answer.exhausted=true;answer.work=work;return false;};
  if(!charge(3))return answer;
  auto pair=causal_deferral_pair(h,g,done,users,prefix,held,work,limit);
  if(!charge(2))return answer;
  if(!pair.complete || pair.producer<0){answer.exhausted=pair.exhausted;answer.work=work;return answer;}
  if(!charge(2))return answer;
  I remaining=limit-work;
  auto retry=release_cut_order_guarded(h,g,remaining,pair.producer,pair.target);
  work+=retry.work; // retry.work<=remaining, no signed overflow, same2M account.
  if(!charge(4))return answer; // Merge/result status and evaluations before use.
  retry.evaluations+=evaluations;retry.work=work;return retry;
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
    else {
      if(single<0)return causal_deferral_restart(h,g,done,users,prefix,held,r.work,limit,r.evaluations);
      if(!apply(single))return r;
    }
  }
  r.order=std::move(prefix);r.best_peak=ProfileInteger(peak);return r;
}
