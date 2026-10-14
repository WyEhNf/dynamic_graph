// R55 isolated optional repair: SAME prefix and complete original-user cut.
// The caller invokes this only after its unchanged greedy path hits no-fit.
// Width/branching are two; exact masks identify states, never scalar live/F.
ReleaseCut failed_cut_beam_repair(const HardwareInfo& h,const Graph& g,int producer,
 const std::vector<int>& pending,const std::vector<int>& remaining_users,
 const std::vector<int>& remaining_degree,I initial_live,I& work,I limit) {
  ReleaseCut r;r.peak=r.final_live=initial_live;
  auto charge=[&](I amount){if(!cut_charge(work,limit,amount)){r.exhausted=true;return false;}return true;};
  if(!charge(1))return r; // New entry/shape predicate, before context work.
  const int count=static_cast<int>(pending.size());
  if(!count || count>128)return r;
  if(!charge(g.n))return r;std::vector<int> position(g.n,-1);
  if(!charge(count))return r;for(int j=0;j<count;++j)position[pending[j]]=j;
  if(!charge(g.n))return r;std::vector<int> user_position(g.n,-1),original_users;
  auto include_user=[&](int i){if(user_position[i]>=0)return true;if(!charge(1))return false;user_position[i]=static_cast<int>(original_users.size());original_users.push_back(i);return true;};
  for(int i:pending) {
    if(!charge(1) || !include_user(i))return r;
    for(int p:g.in[i]){if(!charge(1) || !include_user(p))return r;}
  }
  if(!charge(2*static_cast<I>(count)))return r;
  std::vector<std::vector<int>> inputs(count),successors(count);
  for(int j=0;j<count;++j) {
    int i=pending[j];
    for(int p:g.in[i]){if(!charge(1))return r;inputs[j].push_back(user_position[p]);}
    for(int c:g.out[i]) {
      if(!charge(1))return r;int target=position[c];
      if(target>=0){if(!charge(1))return r;successors[j].push_back(target);}
    }
  }
  struct State {std::vector<int> users,degree;uint64_t lo=0,hi=0;I live=0,peak=0;int parent=-1,last=-1;};
  struct Link {int parent,node;};
  if(!charge(6))return r;State initial;initial.live=initial.peak=initial_live;
  if(!charge(static_cast<I>(original_users.size())+count))return r;
  for(int i:original_users)initial.users.push_back(remaining_users[i]);
  for(int i:pending)initial.degree.push_back(remaining_degree[i]);
  std::vector<State> beam;beam.reserve(2);if(!charge(1))return r;beam.push_back(std::move(initial));
  std::vector<Link> links;links.reserve(4*count);
  using Score=std::tuple<I,I,I>;
  struct Choice {Score score;int local;};
  for(int depth=0;depth<count;++depth) {
    std::vector<State> next;next.reserve(2);
    for(const auto& state:beam) {
      std::vector<Choice> choices;choices.reserve(2);
      for(int j=0;j<count;++j) {
        if(!charge(1))return r;
        bool completed=j<64?bool(state.lo&(uint64_t(1)<<j)):bool(state.hi&(uint64_t(1)<<(j-64)));
        if(completed || state.degree[j])continue;
        const auto& v=g.v[pending[j]];
        if(!memory_fits(h.memory_limit,state.live,v.workspace_memory,v.output_memory))continue;
        I freed=0;
        for(int p:inputs[j]){if(!charge(1))return r;if(state.users[p]==1)freed+=g.v[original_users[p]].output_memory;}
        Score score{v.output_memory-freed,positive_add(v.workspace_memory,v.output_memory),static_cast<I>(v.id)};
        size_t slot=0;
        while(slot<choices.size()){if(!charge(1))return r;if(score<choices[slot].score)break;++slot;}
        if(slot<2) {
          I size_after_discard=static_cast<I>(choices.size()==2?1:choices.size());
          I shifted=std::max<I>(0,size_after_discard-static_cast<I>(slot));
          if(!charge(4*(shifted+1)))return r;
          if(choices.size()==2)choices.pop_back();
          choices.insert(choices.begin()+slot,Choice{score,j});
        }
      }
      for(const auto& choice:choices) {
        int j=choice.local,i=pending[j];const auto& v=g.v[i];
        if(!charge(static_cast<I>(original_users.size())+count+6))return r;State child=state;
        if(!charge(4))return r;
        child.peak=std::max(child.peak,child.live+v.workspace_memory+v.output_memory);
        child.live+=v.output_memory;child.last=j;
        if(j<64)child.lo|=uint64_t(1)<<j;else child.hi|=uint64_t(1)<<(j-64);
        for(int p:inputs[j]){if(!charge(1))return r;if(!--child.users[p])child.live-=g.v[original_users[p]].output_memory;}
        for(int c:successors[j]){if(!charge(1))return r;--child.degree[c];}
        if(!charge(3))return r;links.push_back({state.parent,i});child.parent=static_cast<int>(links.size()-1);
        int identical=-1;
        for(size_t k=0;k<next.size();++k){if(!charge(2))return r;if(next[k].lo==child.lo && next[k].hi==child.hi){identical=static_cast<int>(k);break;}}
        if(identical>=0) {
          if(!charge(1))return r;
          if(child.peak<next[identical].peak){if(!charge(1))return r;next[identical]=std::move(child);}
        }else if(next.size()<2) {if(!charge(1))return r;next.push_back(std::move(child));}
        else {
          if(!charge(1))return r;
          if(std::tie(child.live,child.peak)<std::tie(next[1].live,next[1].peak)){if(!charge(1))return r;next[1]=std::move(child);}
        }
        if(next.size()==2) {
          if(!charge(1))return r;
          if(std::tie(next[1].live,next[1].peak)<std::tie(next[0].live,next[0].peak)){if(!charge(3))return r;std::swap(next[0],next[1]);}
        }
      }
    }
    if(next.empty())return r;
    if(!charge(1))return r;beam=std::move(next);
  }
  if(!charge(2))return r;
  int user=user_position[producer];if(user<0 || beam.front().users[user])return r;
  std::vector<int> order;
  for(int link=beam.front().parent;link>=0;link=links[link].parent){if(!charge(3))return r;order.push_back(links[link].node);}
  if(!charge(static_cast<I>(order.size()/2)))return r;std::reverse(order.begin(),order.end());
  if(!charge(count))return r;r.pending=pending;
  r.order=std::move(order);r.peak=beam.front().peak;r.final_live=beam.front().live;r.valid=true;return r;
}
