// Input-only necessary future-BEGIN bound pruning with bounded backtracking.
// Serial completed prefixes only. Passing a bound is never a feasibility proof.
// Every scan/edge/state consumes the shared logical budget; no named-case rules.
struct NecessaryResult {
  std::vector<int> order; I work=0,prunes=0,states=0;
  bool exhausted=false,intrinsic_blocked=false;
  int monitored_targets=0;
};
NecessaryResult necessary_prefix_search(const HardwareInfo& h,const Graph& g,I limit=2000000,int branch_limit=8) {
  NecessaryResult result;
  if(g.n>512||limit<1||branch_limit<1)return result;
  auto charge=[&](){if(result.work>=limit){result.exhausted=true;return false;}++result.work;return true;};
  std::vector<int> targets(g.n);for(int i=0;i<g.n;++i)targets[i]=i;
  std::stable_sort(targets.begin(),targets.end(),[&](int a,int b){
    I x=positive_add(g.v[a].workspace_memory,g.v[a].output_memory),y=positive_add(g.v[b].workspace_memory,g.v[b].output_memory);
    return x!=y?x>y:a<b;
  });
  if(targets.size()>64)targets.resize(64); // Unmonitored constraints are not pruned.
  result.monitored_targets=static_cast<int>(targets.size());
  std::vector<std::vector<unsigned char>> extra(targets.size(),std::vector<unsigned char>(g.n));
  std::vector<I> slack(targets.size());
  for(size_t k=0;k<targets.size();++k) {
    int t=targets[k];std::vector<unsigned char> anc(g.n),desc(g.n);desc[t]=1;
    std::vector<int> queue{t};
    for(size_t q=0;q<queue.size();++q)for(int p:g.in[queue[q]]) {
      if(!charge())return result;if(!anc[p]){anc[p]=1;queue.push_back(p);}
    }
    queue.assign(1,t);
    for(size_t q=0;q<queue.size();++q)for(int u:g.out[queue[q]]) {
      if(!charge())return result;if(!desc[u]){desc[u]=1;queue.push_back(u);}
    }
    I remaining=h.memory_limit;
    for(I amount:{g.v[t].workspace_memory,g.v[t].output_memory}) {
      if(!charge())return result;
      if(amount>remaining){result.intrinsic_blocked=true;return result;}remaining-=amount;
    }
    for(int p=0;p<g.n;++p) {
      if(!charge())return result;if(p==t)continue;
      bool pinned=g.out[p].empty();
      for(int u:g.out[p]){if(!charge())return result;if(desc[u])pinned=true;}
      if(!pinned)continue;
      if(anc[p]) {
        if(g.v[p].output_memory>remaining){result.intrinsic_blocked=true;return result;}
        remaining-=g.v[p].output_memory;
      }else extra[k][p]=1;
    }
    slack[k]=remaining;
  }
  std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n),order;
  for(int i=0;i<g.n;++i){if(!charge())return result;users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
  I live=0;
  std::function<bool()> visit=[&]() {
    if(!charge())return false;++result.states;
    if(static_cast<int>(order.size())==g.n){result.order=order;return true;}
    struct Choice{int node;I released;};std::vector<Choice> ready;
    for(int p=0;p<g.n;++p) {
      if(!charge())return false;
      if(done[p]||degree[p]||!memory_fits(h.memory_limit,live,g.v[p].workspace_memory,g.v[p].output_memory))continue;
      bool permitted=true;
      for(size_t k=0;k<targets.size();++k) {
        if(!charge())return false;
        if(!done[targets[k]]&&p!=targets[k]&&extra[k][p]&&g.v[p].output_memory>slack[k]){permitted=false;++result.prunes;break;}
      }
      if(!permitted)continue;
      I released=0;
      for(int parent:g.in[p]){if(!charge())return false;if(users[parent]==1)released=positive_add(released,g.v[parent].output_memory);}
      ready.push_back({p,released});
    }
    std::stable_sort(ready.begin(),ready.end(),[&](const Choice& a,const Choice& b){
      I x=g.v[a.node].output_memory-a.released,y=g.v[b.node].output_memory-b.released;
      if(x!=y)return x<y;
      if(g.v[a.node].workspace_memory!=g.v[b.node].workspace_memory)return g.v[a.node].workspace_memory>g.v[b.node].workspace_memory;
      return a.node<b.node;
    });
    if(ready.size()>static_cast<size_t>(branch_limit))ready.resize(branch_limit);
    for(const auto& choice:ready) {
      int p=choice.node;
      // Reserve work for mutation+undo BEFORE touching the reversible state.
      I mutation=2*static_cast<I>(targets.size()+g.in[p].size()+g.out[p].size())+1;
      if(mutation>limit-result.work){result.exhausted=true;return false;}result.work+=mutation;
      I old_live=live;live+=g.v[p].output_memory;done[p]=1;order.push_back(p);
      for(int parent:g.in[p])if(!--users[parent])live-=g.v[parent].output_memory;
      for(int u:g.out[p])--degree[u];
      for(size_t k=0;k<targets.size();++k)if(!done[targets[k]]&&extra[k][p])slack[k]-=g.v[p].output_memory;
      bool found=visit();
      // Inactive target slack is deliberately unchanged at its own emission.
      for(size_t k=0;k<targets.size();++k)if(!done[targets[k]]&&extra[k][p])slack[k]+=g.v[p].output_memory;
      for(int u:g.out[p])++degree[u];for(int parent:g.in[p])++users[parent];
      order.pop_back();done[p]=0;live=old_live;
      if(found)return true;if(result.exhausted)return false;
    }
    return false;
  };
  visit();return result;
}
