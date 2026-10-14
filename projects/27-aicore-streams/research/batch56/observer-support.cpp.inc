// Fixed storage observation only. Never queried by scheduling/fees/comparators.
struct R56ObservationMeta {
  int stage=0,producer_id=-1,target_id=-1;
  I work=0,limit=0;
  uint64_t flags=0,order_size=0,peak_lo=0,peak_hi=0;
};
struct R56ObservationState {
  int stage=0,n=0,prefix_size=0,held_size=0,pending_size=0;
  I live=0;
  bool pending_provided=false,held_provided=true;
  std::array<int,4096> original_ids{},prefix_ids{},users{},degree{},held_ids{},pending_ids{};
  std::array<unsigned char,4096> done{};
};
struct R56Observer {
  std::array<R56ObservationMeta,16> metadata{};
  std::array<R56ObservationState,2> states{};
  std::array<uint64_t,256> stage_counts{};
  uint64_t metadata_seen=0,metadata_dropped=0,states_seen=0,states_dropped=0;
  int metadata_count=0,state_count=0;
  bool counter_overflow=false,state_shape_error=false;
  void reset() noexcept {*this=R56Observer();}
  void bump(uint64_t& x) noexcept {if(x==std::numeric_limits<uint64_t>::max())counter_overflow=true;else ++x;}
  void record(int stage,I work,I limit,int producer_id,int target_id,uint64_t flags,uint64_t order_size,uint64_t peak_lo=0,uint64_t peak_hi=0,bool keep=true) noexcept {
    if(stage<0 || stage>=256){state_shape_error=true;return;}
    bump(stage_counts[stage]);if(!keep)return;
    bump(metadata_seen);R56ObservationMeta item{stage,producer_id,target_id,work,limit,flags,order_size,peak_lo,peak_hi};
    if(metadata_count<16)metadata[metadata_count++]=item;
    else {metadata[15]=item;bump(metadata_dropped);} // first15 + last retained
  }
  void capture(int stage,const Graph& g,const std::vector<unsigned char>& done,
   const std::vector<int>& users,const std::vector<int>& degree,const std::vector<int>& prefix,
   const std::vector<int>& held,I live,const std::vector<int>* pending=nullptr,bool held_provided=true) noexcept {
    bump(states_seen);
    if(g.n>4096 || done.size()!=static_cast<size_t>(g.n) || users.size()!=done.size() || degree.size()!=done.size() || prefix.size()>4096 || held.size()>4096 || (pending && pending->size()>4096)){state_shape_error=true;return;}
    if(state_count==2){bump(states_dropped);return;}
    auto& s=states[state_count++];s.stage=stage;s.n=g.n;s.live=live;s.prefix_size=static_cast<int>(prefix.size());s.held_size=static_cast<int>(held.size());s.held_provided=held_provided;s.pending_provided=pending!=nullptr;s.pending_size=pending?static_cast<int>(pending->size()):0;
    for(int i=0;i<g.n;++i){s.original_ids[i]=g.v[i].id;s.done[i]=done[i];s.users[i]=users[i];s.degree[i]=degree[i];}
    for(size_t k=0;k<prefix.size();++k)s.prefix_ids[k]=g.v[prefix[k]].id;
    for(size_t k=0;k<held.size();++k)s.held_ids[k]=g.v[held[k]].id;
    if(pending)for(size_t k=0;k<pending->size();++k)s.pending_ids[k]=g.v[(*pending)[k]].id;
  }
};
R56Observer r56_observer;
const std::vector<int> r56_empty_ints;
