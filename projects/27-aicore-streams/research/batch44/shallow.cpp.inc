// Diagnostic scores may exceed int64 even when a valid traversal exists.
// Two words are sufficient: n<=4096 and each memory field<=INT64_MAX imply
// instantaneous memory<2^76 and summed per-node allocation profile<2^88.
struct ProfileInteger {
  uint64_t hi=0,lo=0;
  ProfileInteger()=default;
  explicit ProfileInteger(I x):lo(static_cast<uint64_t>(x)) {}
  bool operator<(const ProfileInteger& b)const{return std::tie(hi,lo)<std::tie(b.hi,b.lo);}
  bool operator==(const ProfileInteger& b)const{return hi==b.hi && lo==b.lo;}
  ProfileInteger& operator+=(const ProfileInteger& b){uint64_t old=lo;lo+=b.lo;hi+=b.hi+(lo<old);return *this;}
  ProfileInteger& operator-=(const ProfileInteger& b){uint64_t old=lo;lo-=b.lo;hi-=b.hi+(old<b.lo);return *this;}
};
struct ShallowShape {std::vector<int> prefixes,producers,consumers,tails;std::vector<unsigned char> role;};
ShallowShape shallow_shape(const Graph& g) {
  if(g.n>4096)return {};
  std::vector<int> roots;for(int i:g.topo)if(g.in[i].empty())roots.push_back(i);
  auto recognize=[&](bool prefix) {
    ShallowShape s;s.role.resize(g.n);
    for(int i:roots)if(prefix){s.prefixes.push_back(i);s.role[i]=1;}else{s.producers.push_back(i);s.role[i]=2;}
    if(prefix)for(int i:g.topo)if(!s.role[i] && !g.in[i].empty()) {
      bool all=true;for(int p:g.in[i])if(s.role[p]!=1)all=false;
      if(all){s.producers.push_back(i);s.role[i]=2;}
    }
    for(int i:g.topo)if(!s.role[i] && !g.in[i].empty()) {
      bool all=true;for(int p:g.in[i])if(s.role[p]!=2)all=false;
      if(all){s.consumers.push_back(i);s.role[i]=3;}
    }
    for(int i:g.topo)if(!s.role[i]) {
      bool all=!g.in[i].empty() && g.out[i].empty();for(int p:g.in[i])if(s.role[p]!=3)all=false;
      if(!all)return ShallowShape();
      s.tails.push_back(i);s.role[i]=4;
    }
    if(s.producers.empty() || s.consumers.size()<2 || s.consumers.size()>512)return ShallowShape();
    return s;
  };
  auto preferred=recognize(true);return preferred.consumers.empty()?recognize(false):preferred;
}
struct ShallowProfile {
  ProfileInteger excess,peak,area;
  int critical=-1;
  std::vector<int> order;
  bool operator<(const ShallowProfile& b)const{return std::tie(excess,peak,area)<std::tie(b.excess,b.peak,b.area);}
};
ShallowProfile shallow_profile(const HardwareInfo& h,const Graph& g,const ShallowShape& s,const std::vector<int>& permutation) {
  ShallowProfile r;std::vector<unsigned char> done(g.n);std::vector<int> users(g.n);
  for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  ProfileInteger live,capacity(h.memory_limit);
  auto execute=[&](int i,int slot) {
    ProfileInteger allocation=live;allocation+=ProfileInteger(g.v[i].workspace_memory);allocation+=ProfileInteger(g.v[i].output_memory);
    if(r.peak<allocation){r.peak=allocation;r.critical=slot;}
    r.area+=allocation;if(capacity<allocation){auto excess=allocation;excess-=capacity;r.excess+=excess;}
    live+=ProfileInteger(g.v[i].output_memory);
    for(int p:g.in[i])if(!--users[p])live-=ProfileInteger(g.v[p].output_memory);
    done[i]=1;r.order.push_back(i);
  };
  for(int p:s.prefixes)execute(p,-1);
  for(size_t k=0;k<permutation.size();++k) {
    int c=permutation[k];std::vector<int> fresh;for(int p:g.in[c])if(!done[p])fresh.push_back(p);
    // Adjacent exchange (constant pre-existing input lifetime): W_a>=W_b implies max(O_a+W_a,
    // O_a+O_b+W_b)<=O_a+O_b+W_a, a lower bound on the reverse order.
    // These producers are independent and their outputs remain live through c.
    bool constant_prefix=true;
    for(int prefix:s.prefixes)if(g.v[prefix].output_memory) {
      int fresh_users=0;for(int p:fresh)if(std::find(g.in[p].begin(),g.in[p].end(),prefix)!=g.in[p].end())++fresh_users;
      if(fresh_users && users[prefix]<=fresh_users && static_cast<size_t>(fresh_users)<fresh.size())constant_prefix=false;
    }
    if(constant_prefix)std::stable_sort(fresh.begin(),fresh.end(),[&](int a,int b){return g.v[a].workspace_memory>g.v[b].workspace_memory;});
    for(int p:fresh)execute(p,static_cast<int>(k));
    execute(c,static_cast<int>(k));
  }
  for(int p:s.producers)if(!done[p])execute(p,-1);
  for(int t:s.tails)execute(t,-1);
  return r;
}
struct ShallowResult {std::vector<int> order;I work=0;int evaluations=0;bool exhausted=false;ProfileInteger best_peak;};
ShallowResult shallow_memory_search(const HardwareInfo& h,const Graph& g,I work_limit=12000000) {
  ShallowResult result;auto shape=shallow_shape(g);if(shape.consumers.empty())return result;
  I unit=g.n;for(const auto& x:g.in)unit+=static_cast<I>(x.size());
  std::vector<std::vector<int>> seeds;
  for(int mode=0;mode<6;++mode) {
    auto order=ordering(g,mode);std::vector<int> perm;for(int i:order)if(shape.role[i]==3)perm.push_back(i);
    if(std::find(seeds.begin(),seeds.end(),perm)==seeds.end())seeds.push_back(std::move(perm));
  }
  // Consumer affinity uses actual shared producers, weighted by output size.
  // Common high-fanout producers contribute less and cannot dominate a local
  // neighborhood. Pair construction is bounded; skipped scoring pairs do not
  // remove any dependency from profiles or submitted plans.
  const int count=static_cast<int>(shape.consumers.size());
  std::vector<int> position(g.n,-1);for(int q=0;q<count;++q)position[shape.consumers[q]]=q;
  std::vector<std::vector<I>> affinity(count,std::vector<I>(count));I pair_work=0;
  for(int p:shape.producers) {
    std::vector<int> targets;for(int c:g.out[p])if(position[c]>=0)targets.push_back(position[c]);
    I pairs=static_cast<I>(targets.size())*static_cast<I>(targets.size());
    if(targets.size()>64 || pair_work+pairs>1000000)continue;
    pair_work+=pairs;result.work+=pairs;
    if(result.work>work_limit){result.exhausted=true;return result;}
    I weight=priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(std::max<size_t>(1,targets.size())));
    for(size_t a=0;a<targets.size();++a)for(size_t b=a+1;b<targets.size();++b) {
      int i=targets[a],j=targets[b];affinity[i][j]=positive_add(affinity[i][j],weight);affinity[j][i]=affinity[i][j];
    }
  }
  for(int window:{1,4})for(int start=0;start<6;++start) {
    std::vector<int> indices{start*count/6};std::vector<unsigned char> seen(count);seen[indices[0]]=1;
    while(static_cast<int>(indices.size())<count) {
      int best=-1;I best_score=-1;
      for(int q=0;q<count;++q)if(!seen[q]) {
        I score=0;for(size_t recent=indices.size()>static_cast<size_t>(window)?indices.size()-window:0;recent<indices.size();++recent) {
          if(++result.work>work_limit){result.exhausted=true;return result;}
          score=positive_add(score,affinity[indices[recent]][q]);
        }
        if(score>best_score){best=q;best_score=score;}
      }
      seen[best]=1;indices.push_back(best);
    }
    std::vector<int> perm;for(int q:indices)perm.push_back(shape.consumers[q]);
    if(std::find(seeds.begin(),seeds.end(),perm)==seeds.end())seeds.push_back(std::move(perm));
  }
  // An output lifetime locality seed uses only actual direct co-consumers.
  for(int mode:{0,6,12,18,24,27,30}) {
    auto order=bundle_ordering(h,g,mode);std::vector<int> perm;std::vector<unsigned char> seen(g.n);
    for(int i:order)if(shape.role[i]==3){perm.push_back(i);seen[i]=1;}
    for(int i:shape.consumers)if(!seen[i])perm.push_back(i);
    if(std::find(seeds.begin(),seeds.end(),perm)==seeds.end())seeds.push_back(std::move(perm));
  }
  for(int mode=0;mode<6;++mode) {
    auto order=memory_ordering(h,g,mode);std::vector<int> perm;std::vector<unsigned char> seen(g.n);
    for(int i:order)if(shape.role[i]==3){perm.push_back(i);seen[i]=1;}
    for(int i:shape.consumers)if(!seen[i])perm.push_back(i);
    if(std::find(seeds.begin(),seeds.end(),perm)==seeds.end())seeds.push_back(std::move(perm));
  }
  bool have_peak=false;
  auto evaluate=[&](const std::vector<int>& perm) {
    result.work+=unit;++result.evaluations;auto p=shallow_profile(h,g,shape,perm);
    if(!have_peak || p.peak<result.best_peak){result.best_peak=p.peak;have_peak=true;}
    return p;
  };
  auto feasible=[&](const ShallowProfile& p){return p.excess==ProfileInteger();};
  std::vector<ShallowProfile> starts;for(const auto& perm:seeds) {
    if(result.work+unit>work_limit){result.exhausted=true;return result;}
    auto p=evaluate(perm);if(feasible(p)){result.order=std::move(p.order);return result;}starts.push_back(std::move(p));
  }
  std::vector<size_t> ranked;for(size_t i=0;i<seeds.size();++i)ranked.push_back(i);
  std::stable_sort(ranked.begin(),ranked.end(),[&](size_t a,size_t b){return starts[a]<starts[b];});
  if(ranked.size()>2)ranked.resize(2);
  uint32_t rng=static_cast<uint32_t>(g.n)*2654435761u+17u;
  for(size_t seed=0;seed<ranked.size();++seed) {
    auto perm=seeds[ranked[seed]];
    if(result.work+unit>work_limit){result.exhausted=true;break;}
    auto current=starts[ranked[seed]];
    I local_limit=seed+1==ranked.size()?work_limit:result.work+(work_limit-result.work)/static_cast<I>(ranked.size()-seed);
    for(int iteration=0;iteration<64;++iteration) {
      if(feasible(current)){result.order=std::move(current.order);return result;}
      const int k=static_cast<int>(perm.size()),critical=current.critical;
      if(critical<0)break;
      std::vector<std::pair<int,int>> moves;
      // Delay the critical consumer, or bring the last user of a held output
      // before it. This changes only order, never edges or lifetime accounting.
      int stride=std::max(1,k/48);
      for(int q=0;q<k;q+=stride)if(q!=critical)moves.emplace_back(critical,q);
      std::vector<int> first(g.n,k),last(g.n,-1);
      for(int q=0;q<k;++q)for(int p:g.in[perm[q]]){first[p]=std::min(first[p],q);last[p]=q;}
      std::vector<int> held;for(int p:shape.producers)if(first[p]<=critical && last[p]>critical)held.push_back(p);
      std::stable_sort(held.begin(),held.end(),[&](int a,int b){return g.v[a].output_memory>g.v[b].output_memory;});
      if(held.size()>48)held.resize(48);
      for(int p:held){moves.emplace_back(last[p],critical);if(critical)moves.emplace_back(last[p],critical-1);}
      for(int q=0;q<32;++q){rng=rng*1664525u+1013904223u;int a=static_cast<int>(rng%static_cast<uint32_t>(k));rng=rng*1664525u+1013904223u;int b=static_cast<int>(rng%static_cast<uint32_t>(k));if(a!=b)moves.emplace_back(a,b);}
      std::set<std::pair<int,int>> seen_moves;auto best=current;std::vector<int> best_perm=perm;bool improved=false;
      for(auto move:moves)if(seen_moves.insert(move).second) {
        if(result.work+unit>local_limit)break;
        auto candidate=perm;int v=candidate[move.first];candidate.erase(candidate.begin()+move.first);candidate.insert(candidate.begin()+move.second,v);
        auto tested=evaluate(candidate);
        if(tested<best){best=std::move(tested);best_perm=std::move(candidate);improved=true;}
        if(feasible(best)){result.order=std::move(best.order);return result;}
      }
      if(!improved || result.work+unit>local_limit)break;
      current=std::move(best);perm=std::move(best_perm);
    }
    if(result.work+unit>work_limit){result.exhausted=true;break;}
  }
  return result;
}
