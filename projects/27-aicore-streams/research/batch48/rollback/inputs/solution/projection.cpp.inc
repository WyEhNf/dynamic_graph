// Input-only workspace-frontier projection. These are ordering interfaces,
// not graph contractions: all allocations and DIRECT-user releases remain
// on the original graph, including retained sink outputs.
struct WorkspaceProjection {
  std::vector<int> targets,position;
  std::vector<std::vector<int>> closures,predecessors,successors;
  I unit=0;
};
WorkspaceProjection workspace_projection(const Graph& g) {
  WorkspaceProjection s;if(g.n>4096)return s;
  std::vector<I> positive;
  for(const auto& v:g.v)if(v.workspace_memory)positive.push_back(v.workspace_memory);
  if(positive.empty())return s;
  std::sort(positive.begin(),positive.end());
  I threshold=priority_mul_div(positive[(positive.size()-1)/2],4,1);
  s.position.assign(g.n,-1);
  for(int i:g.topo)if(g.in[i].size()>=2 && g.v[i].workspace_memory>=threshold) {
    I previous=0;for(int p:g.in[i])previous=std::max(previous,g.v[p].workspace_memory);
    if(g.v[i].workspace_memory>previous){s.position[i]=static_cast<int>(s.targets.size());s.targets.push_back(i);}
  }
  if(s.targets.size()<2 || s.targets.size()>512)return {};
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
struct ProjectionProfile:ShallowProfile {std::vector<int> permutation;};
ProjectionProfile projection_profile(const HardwareInfo& h,const Graph& g,const WorkspaceProjection& s,const std::vector<int>& desired) {
  ProjectionProfile r;int k=static_cast<int>(s.targets.size());
  std::vector<int> rank(k,k),degree(k);std::vector<unsigned char> scheduled(k),done(g.n);
  for(int q=0;q<k;++q)rank[s.position[desired[q]]]=q;
  for(int q=0;q<k;++q)degree[q]=static_cast<int>(s.predecessors[q].size());
  std::vector<int> users(g.n);for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  ProfileInteger live,capacity(h.memory_limit);
  auto execute=[&](int i,int slot) {
    ProfileInteger allocation=live;allocation+=ProfileInteger(g.v[i].workspace_memory);allocation+=ProfileInteger(g.v[i].output_memory);
    if(r.peak<allocation){r.peak=allocation;r.critical=slot;}
    r.area+=allocation;if(capacity<allocation){auto excess=allocation;excess-=capacity;r.excess+=excess;}
    live+=ProfileInteger(g.v[i].output_memory);
    for(int p:g.in[i])if(!--users[p])live-=ProfileInteger(g.v[p].output_memory);
    done[i]=1;r.order.push_back(i);
  };
  for(int slot=0;slot<k;++slot) {
    int best=-1;for(int q=0;q<k;++q)if(!scheduled[q] && !degree[q] && (best<0 || rank[q]<rank[best]))best=q;
    if(best<0)return {}; // Cannot occur for a valid DAG.
    scheduled[best]=1;r.permutation.push_back(s.targets[best]);
    for(int i:s.closures[best])if(!done[i])execute(i,slot);
    for(int q:s.successors[best])--degree[q];
  }
  for(int i:g.topo)if(!done[i])execute(i,-1);
  return r;
}
std::vector<std::pair<std::vector<int>,I>> direct_consumer_groups(const Graph& g,const WorkspaceProjection& s,I& work,I limit,bool& exhausted) {
  std::map<std::vector<int>,I> grouped;
  for(int p=0;p<g.n;++p)if(s.position[p]<0 && g.v[p].output_memory && g.out[p].size()>=2 && g.out[p].size()<=4) {
    std::vector<int> members;bool all=true;
    for(int c:g.out[p]){if(++work>limit){exhausted=true;return {};}if(s.position[c]<0){all=false;break;}members.push_back(c);}
    if(!all)continue;std::sort(members.begin(),members.end());
    grouped[members]=positive_add(grouped[members],g.v[p].output_memory);
  }
  std::vector<std::pair<std::vector<int>,I>> groups(grouped.begin(),grouped.end());
  std::stable_sort(groups.begin(),groups.end(),[](const auto& a,const auto& b){return a.second>b.second;});return groups;
}
std::vector<int> move_consumer_group(const std::vector<int>& permutation,const std::vector<int>& group,int pivot) {
  std::vector<int> block,remaining;int removed_before=0;
  for(size_t q=0;q<permutation.size();++q) {
    int v=permutation[q];
    if(std::find(group.begin(),group.end(),v)!=group.end()){block.push_back(v);if(static_cast<int>(q)<pivot)++removed_before;}
    else remaining.push_back(v);
  }
  int destination=std::max(0,std::min(static_cast<int>(remaining.size()),pivot-removed_before));
  remaining.insert(remaining.begin()+destination,block.begin(),block.end());return remaining;
}
ShallowResult projection_memory_search(const HardwareInfo& h,const Graph& g,I work_limit=16000000) {
  ShallowResult result;auto s=workspace_projection(g);if(s.targets.empty())return result;
  int k=static_cast<int>(s.targets.size());if(s.unit>work_limit)return result;
  std::vector<std::vector<int>> seeds;
  auto add=[&](const std::vector<int>& order) {
    std::vector<int> perm;std::vector<unsigned char> seen(g.n);
    for(int i:order)if(s.position[i]>=0){perm.push_back(i);seen[i]=1;}
    for(int i:s.targets)if(!seen[i])perm.push_back(i);
    if(std::find(seeds.begin(),seeds.end(),perm)==seeds.end())seeds.push_back(std::move(perm));
  };
  for(int mode=0;mode<6;++mode)add(ordering(g,mode));
  std::vector<std::vector<int>> uses(g.n);for(int q=0;q<k;++q)for(int i:s.closures[q])uses[i].push_back(q);
  std::vector<std::vector<I>> affinity(k,std::vector<I>(k));I pair_work=0;
  for(int p=0;p<g.n;++p)if(s.position[p]<0 && g.v[p].output_memory && uses[p].size()<=64) {
    I pairs=static_cast<I>(uses[p].size())*static_cast<I>(uses[p].size());if(pair_work+pairs>1000000)continue;
    pair_work+=pairs;result.work+=pairs;
    I weight=priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(std::max<size_t>(1,uses[p].size())));
    for(size_t a=0;a<uses[p].size();++a)for(size_t b=a+1;b<uses[p].size();++b) {
      int i=uses[p][a],j=uses[p][b];affinity[i][j]=positive_add(affinity[i][j],weight);affinity[j][i]=affinity[i][j];
    }
  }
  for(int window:{1,4})for(int start=0;start<6;++start) {
    std::vector<int> indices{start*k/6};std::vector<unsigned char> used(k);used[indices[0]]=1;
    while(static_cast<int>(indices.size())<k) {
      int best=-1;I best_score=-1;
      for(int q=0;q<k;++q)if(!used[q]) {
        I score=0;for(size_t recent=indices.size()>static_cast<size_t>(window)?indices.size()-window:0;recent<indices.size();++recent) {
          if(++result.work>work_limit){result.exhausted=true;return result;}
          score=positive_add(score,affinity[indices[recent]][q]);
        }
        if(score>best_score){best=q;best_score=score;}
      }
      used[best]=1;indices.push_back(best);
    }
    std::vector<int> perm;for(int q:indices)perm.push_back(s.targets[q]);add(perm);
  }
  for(int mode:{0,6,12,18,24,27,30})add(bundle_ordering(h,g,mode));
  for(int mode=0;mode<6;++mode)add(memory_ordering(h,g,mode));
  // Original direct-consumer sets only; a group proposes an ordering
  // move, never a fused operation, transformed edge or early release.
  auto groups=direct_consumer_groups(g,s,result.work,work_limit,result.exhausted);if(result.exhausted)return result;
  auto feasible=[](const ProjectionProfile& p){return p.excess==ProfileInteger();};
  bool have=false;auto evaluate=[&](const std::vector<int>& perm) {
    result.work+=s.unit;++result.evaluations;auto p=projection_profile(h,g,s,perm);
    if(!have || p.peak<result.best_peak){result.best_peak=p.peak;have=true;}return p;
  };
  std::vector<ProjectionProfile> starts;for(const auto& perm:seeds) {
    if(result.work+s.unit>work_limit){result.exhausted=true;return result;}
    auto p=evaluate(perm);if(feasible(p)){result.order=std::move(p.order);return result;}starts.push_back(std::move(p));
  }
  std::vector<size_t> ranked;for(size_t q=0;q<starts.size();++q)ranked.push_back(q);
  std::stable_sort(ranked.begin(),ranked.end(),[&](size_t a,size_t b){return starts[a]<starts[b];});if(ranked.size()>2)ranked.resize(2);
  uint32_t rng=static_cast<uint32_t>(g.n)*2654435761u+43u;
  for(size_t seed=0;seed<ranked.size();++seed) {
    auto current=starts[ranked[seed]];auto perm=current.permutation;
    I local_limit=seed+1==ranked.size()?work_limit:result.work+(work_limit-result.work)/static_cast<I>(ranked.size()-seed);
    for(int iteration=0;iteration<64;++iteration) {
      int critical=current.critical;if(critical<0)break;
      std::vector<std::pair<int,int>> moves;int stride=std::max(1,k/48);
      for(int q=0;q<k;q+=stride)if(q!=critical)moves.emplace_back(critical,q);
      std::vector<int> first(g.n,k),last(g.n,-1);
      for(int q=0;q<k;++q)for(int p:s.closures[s.position[perm[q]]]){first[p]=std::min(first[p],q);last[p]=q;}
      std::vector<int> held;for(int p=0;p<g.n;++p)if(first[p]<=critical && last[p]>critical)held.push_back(p);
      std::stable_sort(held.begin(),held.end(),[&](int a,int b){return g.v[a].output_memory>g.v[b].output_memory;});if(held.size()>48)held.resize(48);
      for(int p:held){moves.emplace_back(last[p],critical);if(critical)moves.emplace_back(last[p],critical-1);}
      for(int q=0;q<32;++q){rng=rng*1664525u+1013904223u;int a=static_cast<int>(rng%static_cast<uint32_t>(k));rng=rng*1664525u+1013904223u;int b=static_cast<int>(rng%static_cast<uint32_t>(k));if(a!=b)moves.emplace_back(a,b);}
      auto best=current;bool improved=false;std::set<std::pair<int,int>> tested;
      for(auto move:moves)if(tested.insert(move).second) {
        if(result.work+s.unit>local_limit)break;
        auto candidate=perm;int v=candidate[move.first];candidate.erase(candidate.begin()+move.first);candidate.insert(candidate.begin()+move.second,v);
        auto p=evaluate(candidate);if(p<best){best=std::move(p);improved=true;}
        if(feasible(best)){result.order=std::move(best.order);return result;}
      }
      // Evaluate block insertions only at a single-node local minimum.
      // Overlapping groups are separate candidates. Normalization enforces
      // all original interface dependencies; closure profiles charge W+O.
      if(!improved && result.work+s.unit<=local_limit) {
        std::vector<int> position(g.n,-1);for(int q=0;q<k;++q)position[perm[q]]=q;
        int tried=0;std::set<std::vector<int>> seen_permutations;
        for(const auto& group:groups) {
          int first=k,last=-1;for(int c:group.first){first=std::min(first,position[c]);last=std::max(last,position[c]);}
          if(first==last || !(first<=critical && critical<last))continue;
          if(++tried>24)break;
          for(int pivot:{critical,critical+1}) {
            if(result.work+s.unit>local_limit)break;
            auto candidate=move_consumer_group(perm,group.first,pivot);
            if(candidate==perm || !seen_permutations.insert(candidate).second)continue;
            auto p=evaluate(candidate);if(p<best){best=std::move(p);improved=true;}
            if(feasible(best)){result.order=std::move(best.order);return result;}
          }
        }
      }
      if(!improved || result.work+s.unit>local_limit)break;
      current=std::move(best);perm=current.permutation;
    }
    if(result.work+s.unit>work_limit){result.exhausted=true;break;}
  }
  return result;
}
