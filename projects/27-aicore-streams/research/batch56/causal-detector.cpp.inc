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
