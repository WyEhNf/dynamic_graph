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
