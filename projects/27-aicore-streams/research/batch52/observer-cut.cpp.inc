// Current-frontier release cut. The producer is already completed; every
// remaining ORIGINAL DIRECT user and its unfinished ancestors are included.
// No dependency rewriting, consumer fusion, workspace thresholds or seeds.
struct ReleaseCut {
  std::vector<int> pending,order;
  I peak=0,final_live=0;
  bool valid=false,exhausted=false;
};
// Isolated observation only; never changes solver values or charged work.
struct ObserverFrame {
  std::string kind,phase="initial",reason;
  bool transition_incomplete=false;
  int producer=-1;
  const std::vector<unsigned char>* done=nullptr,*included=nullptr;
  const std::vector<int>* users=nullptr,*degree=nullptr,*prefix=nullptr;
  const I* live=nullptr;I initial_live=0;
  void bind(const Graph&,const std::vector<unsigned char>& d,const std::vector<int>& u,
            const std::vector<int>& deg,const I& l){done=&d;users=&u;degree=&deg;live=&l;initial_live=l;}
};
struct ObserverLog {
  bool enabled=true,cut_exhausted=false,cut_complete=false,projection_exhausted=false;
  I cut_work=0,projection_work=0,total_work=0;
  const std::vector<int>* current_prefix=nullptr;
  std::map<std::string,uint64_t> counts,retained;
  std::vector<std::string> snapshots;
  void reset(){*this=ObserverLog();}
};
ObserverLog observer;
template<class T> void observe_array(std::ostream& out,const std::vector<T>& items) {
  out<<'[';bool first=true;for(auto x:items){if(!first)out<<',';first=false;out<<static_cast<I>(x);}out<<']';
}
void observe_order(std::ostream& out,const Graph& g,const std::vector<int>* order) {
  out<<'[';bool first=true;if(order)for(int i:*order){if(!first)out<<',';first=false;out<<g.v[i].id;}out<<']';
}
void observe_snapshot(const HardwareInfo& h,const Graph& g,const ObserverFrame& frame,
                      const std::string& reason,I work,I limit,const std::vector<int>* probe_order,
                      bool always=false) {
  if(!observer.enabled)return;
  std::string key=frame.kind+":"+frame.phase+":"+reason;
  ++observer.counts[key];
  if(!always && observer.retained[key]>=2)return;
  ++observer.retained[key];
  std::ostringstream out;
  out<<"{\"kind\":\""<<frame.kind<<"\",\"phase\":\""<<frame.phase<<"\",\"reason\":\""<<reason
     <<"\",\"charged_work\":"<<work<<",\"limit\":"<<limit<<",\"memory_limit\":"<<h.memory_limit
     <<",\"producer_id\":"<<(frame.producer>=0?g.v[frame.producer].id:-1);
  out<<",\"node_ids\":[";for(int i=0;i<g.n;++i){if(i)out<<',';out<<g.v[i].id;}out<<']';
  out<<",\"state_initialized\":"<<(frame.done?"true":"false");
  out<<",\"transition_may_be_incomplete\":"<<(frame.transition_incomplete?"true":"false");
  if(frame.done) {
    out<<",\"done\":";observe_array(out,*frame.done);
    out<<",\"remaining_direct_users\":";observe_array(out,*frame.users);
    out<<",\"remaining_degree\":";observe_array(out,*frame.degree);
    out<<",\"live\":"<<*frame.live<<",\"initial_live\":"<<frame.initial_live;
    out<<",\"outer_completed_order\":";
    observe_order(out,g,frame.prefix?frame.prefix:observer.current_prefix);
    out<<",\"probe_completed_order\":";observe_order(out,g,probe_order);
    std::vector<int> seen,ready,fit,cut_ready,cut_fit;
    for(int i=0;i<g.n;++i) {
      if(frame.included && (*frame.included)[i])seen.push_back(g.v[i].id);
      if((*frame.done)[i] || (*frame.degree)[i])continue;
      ready.push_back(g.v[i].id);bool fits=memory_fits(h.memory_limit,*frame.live,g.v[i].workspace_memory,g.v[i].output_memory);
      if(fits)fit.push_back(g.v[i].id);
      if(frame.included && (*frame.included)[i]){cut_ready.push_back(g.v[i].id);if(fits)cut_fit.push_back(g.v[i].id);}
    }
    out<<",\"closure_construction_seen_ids\":";observe_array(out,seen);
    out<<",\"global_ready_ids\":";observe_array(out,ready);
    out<<",\"global_ready_fit_ids\":";observe_array(out,fit);
    out<<",\"cut_ready_ids\":";observe_array(out,cut_ready);
    out<<",\"cut_ready_fit_ids\":";observe_array(out,cut_fit);
    out<<",\"held_outputs\":[";bool first=true;I sink=0,external=0;
    for(int i=0;i<g.n;++i)if((*frame.done)[i] && g.v[i].output_memory && ((*frame.users)[i] || g.out[i].empty())) {
      std::vector<int> pending_users,outside;for(int c:g.out[i])if(!(*frame.done)[c]){
        pending_users.push_back(g.v[c].id);if(frame.included && !(*frame.included)[c])outside.push_back(g.v[c].id);
      }
      if(g.out[i].empty())sink+=g.v[i].output_memory;
      if(!outside.empty())external+=g.v[i].output_memory;
      if(!first)out<<',';first=false;out<<"{\"producer_id\":"<<g.v[i].id<<",\"output\":"<<g.v[i].output_memory
        <<",\"sink\":"<<(g.out[i].empty()?"true":"false")<<",\"remaining_user_ids\":";
      observe_array(out,pending_users);out<<",\"outside_cut_user_ids\":";observe_array(out,outside);out<<'}';
    }
    out<<"],\"held_sink_output\":"<<sink<<",\"held_external_cut_output\":"<<external;
  }
  out<<'}';observer.snapshots.push_back(out.str());
}
void observe_probe_exit(const HardwareInfo& h,const Graph& g,const ReleaseCut& result,
                       const ObserverFrame& frame,I work,I limit) {
  std::string reason=frame.reason;
  if(result.exhausted)reason="budget_exhausted";
  else if(result.valid)reason="complete_cut";
  else if(reason.empty())reason="eligibility_or_other_rejection";
  if(reason=="greedy_stopped" && frame.done) {
    bool ready=false;for(int i:result.pending)if(!(*frame.done)[i] && !(*frame.degree)[i])ready=true;
    reason=ready?"ready_but_no_fit":"no_ready_in_cut";
  }
  observe_snapshot(h,g,frame,reason,work,limit,&result.order);
  if(result.valid && result.final_live>=frame.initial_live)++observer.counts["complete_cut:no_net_release"];
}
void observe_outer_exit(const HardwareInfo& h,const Graph& g,const ShallowResult& result,
                       const ObserverFrame& frame,I limit) {
  std::string reason=result.exhausted?"budget_exhausted":frame.reason;
  if(result.order.size()==static_cast<size_t>(g.n))reason="complete_graph";
  if(reason.empty())reason="other_rejection";
  observe_snapshot(h,g,frame,reason,result.work,limit,&result.order,true);
  observer.current_prefix=nullptr;
}
std::string observer_json() {
  std::ostringstream out;out<<"{\"cut_work\":"<<observer.cut_work<<",\"cut_exhausted\":"<<(observer.cut_exhausted?"true":"false")
    <<",\"cut_complete\":"<<(observer.cut_complete?"true":"false")<<",\"projection_work\":"<<observer.projection_work
    <<",\"projection_exhausted\":"<<(observer.projection_exhausted?"true":"false")<<",\"total_work\":"<<observer.total_work
    <<",\"counts\":{";bool first=true;for(const auto& pair:observer.counts){if(!first)out<<',';first=false;out<<'"'<<pair.first<<"\":"<<pair.second;}
  out<<"},\"snapshots\":[";first=true;for(const auto& row:observer.snapshots){if(!first)out<<',';first=false;out<<row;}
  out<<"]}";return out.str();
}

bool cut_charge(I& work,I limit,I amount) {
  if(amount>limit-work){work=limit;return false;}
  work+=amount;return true;
}
ReleaseCut release_cut_probe(const HardwareInfo& h,const Graph& g,int producer,
 const std::vector<unsigned char>& completed,const std::vector<int>& remaining_users,
 const std::vector<int>& remaining_degree,I live,I& work,I limit) {
  ReleaseCut r;r.peak=r.final_live=live;
  ObserverFrame frame;frame.kind="probe";frame.producer=producer;frame.bind(g,completed,remaining_users,remaining_degree,live);
  auto charge=[&](I amount){if(!cut_charge(work,limit,amount)){r.exhausted=true;return false;}return true;};
  if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}
  if(!completed[producer] || !g.v[producer].output_memory || g.out[producer].empty() || !remaining_users[producer]){observe_probe_exit(h,g,r,frame,work,limit);return r;}
  frame.phase="copy";
  if(!charge(4*static_cast<I>(g.n))){observe_probe_exit(h,g,r,frame,work,limit);return r;}
  std::vector<unsigned char> included(g.n),done=completed;
  std::vector<int> stack,users=remaining_users,degree=remaining_degree;
  frame.bind(g,done,users,degree,live);frame.included=&included;frame.phase="closure";
  for(int c:g.out[producer]){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}if(!done[c])stack.push_back(c);}
  int count=0;
  while(!stack.empty()) {
    int i=stack.back();stack.pop_back();if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}
    if(done[i] || included[i])continue;included[i]=1;
    if(++count>128){frame.reason="cap128";{observe_probe_exit(h,g,r,frame,work,limit);return r;}} // Optional ordering accelerator, not a certificate.
    for(int p:g.in[i]){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}if(!done[p])stack.push_back(p);}
  }
  frame.phase="topo";
  for(int i:g.topo){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}if(included[i])r.pending.push_back(i);}
  frame.phase="greedy";
  while(r.order.size()<r.pending.size()) {
    int selected=-1;std::tuple<I,I,I> best;
    for(int i:r.pending) {
      if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}
      if(done[i] || degree[i])continue;
      const auto& v=g.v[i];if(!memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory))continue;
      I freed=0;
      for(int p:g.in[i]){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}if(users[p]==1)freed+=g.v[p].output_memory;}
      // freed is a subset of physically held live outputs, so is <=live.
      auto score=std::make_tuple(v.output_memory-freed,positive_add(v.workspace_memory,v.output_memory),static_cast<I>(v.id));
      if(selected<0 || score<best){selected=i;best=score;}
    }
    if(selected<0){frame.reason="greedy_stopped";{observe_probe_exit(h,g,r,frame,work,limit);return r;}}
    int i=selected;const auto& v=g.v[i];
    frame.phase="apply";frame.transition_incomplete=true;
    r.peak=std::max(r.peak,live+v.workspace_memory+v.output_memory);
    live+=v.output_memory;done[i]=1;r.order.push_back(i);
    for(int p:g.in[i]){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}if(!--users[p])live-=g.v[p].output_memory;}
    for(int c:g.out[i]){if(!charge(1)){observe_probe_exit(h,g,r,frame,work,limit);return r;}--degree[c];}
    frame.transition_incomplete=false;frame.phase="greedy";
  }
  // All original remaining direct users must have completed. In particular,
  // an outside/non-interface user is not silently omitted from this check.
  frame.phase="completion";
  if(users[producer]){frame.reason="producer_unreleased";{observe_probe_exit(h,g,r,frame,work,limit);return r;}}
  r.final_live=live;r.valid=true;{observe_probe_exit(h,g,r,frame,work,limit);return r;}
}
ShallowResult release_cut_order(const HardwareInfo& h,const Graph& g,I limit) {
  ShallowResult r;ObserverFrame frame;frame.kind="outer";if(g.n>4096){frame.reason="graph_cap4096";{observe_outer_exit(h,g,r,frame,limit);return r;}}
  if(!cut_charge(r.work,limit,3*static_cast<I>(g.n))){r.exhausted=true;{observe_outer_exit(h,g,r,frame,limit);return r;}}
  std::vector<unsigned char> done(g.n);std::vector<int> users(g.n),degree(g.n);
  for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
  I live=0,peak=0;std::vector<int> prefix;
  frame.bind(g,done,users,degree,live);frame.prefix=&prefix;observer.current_prefix=&prefix;
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
      if(!charge(1)){observe_outer_exit(h,g,r,frame,limit);return r;}
      if(done[i]){if(users[i] && g.v[i].output_memory)held.push_back(i);continue;}
      if(degree[i] || !memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory))continue;
      I net;if(!impact(i,net)){observe_outer_exit(h,g,r,frame,limit);return r;}
      auto score=std::make_tuple(net,positive_add(g.v[i].workspace_memory,g.v[i].output_memory),static_cast<I>(g.v[i].id));
      if(single<0 || score<best){single=i;best=score;}
      if(net<=0 && (safe<0 || g.v[i].id<g.v[safe].id))safe=i;
    }
    if(safe>=0){if(!apply(safe)){observe_outer_exit(h,g,r,frame,limit);return r;}continue;}
    bool sort_budget=true;
    std::stable_sort(held.begin(),held.end(),[&](int a,int b){if(!charge(1))sort_budget=false;return g.v[a].output_memory!=g.v[b].output_memory?g.v[a].output_memory>g.v[b].output_memory:g.v[a].id<g.v[b].id;});
    if(!sort_budget){observe_outer_exit(h,g,r,frame,limit);return r;}if(held.size()>24)held.resize(24);
    ReleaseCut selected;bool have=false;
    for(int p:held) {
      auto candidate=release_cut_probe(h,g,p,done,users,degree,live,r.work,limit);++r.evaluations;
      if(candidate.exhausted){r.exhausted=true;{observe_outer_exit(h,g,r,frame,limit);return r;}}
      if(candidate.valid && (!have || std::tie(candidate.final_live,candidate.peak)<std::tie(selected.final_live,selected.peak))) {selected=std::move(candidate);have=true;}
    }
    if(have){for(int i:selected.order)if(!apply(i)){frame.reason="apply_rejected";{observe_outer_exit(h,g,r,frame,limit);return r;}}}
    else {if(single<0 || !apply(single)){frame.reason="no_progress";{observe_outer_exit(h,g,r,frame,limit);return r;}}}
  }
  r.order=std::move(prefix);r.best_peak=ProfileInteger(peak);{observe_outer_exit(h,g,r,frame,limit);return r;}
}
