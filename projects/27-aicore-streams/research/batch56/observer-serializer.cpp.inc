static std::string r56_observer_json(){
  const auto& o=aicore_detail::r56_observer;std::ostringstream s;
  s<<"{\"metadata_limit\":16,\"state_limit\":2,\"array_limit\":4096,\"selection\":\"first15_and_last_metadata_first2_states\",\"metadata_seen\":"<<o.metadata_seen<<",\"metadata_dropped\":"<<o.metadata_dropped<<",\"states_seen\":"<<o.states_seen<<",\"states_dropped\":"<<o.states_dropped<<",\"counter_overflow\":"<<(o.counter_overflow?"true":"false")<<",\"state_shape_error\":"<<(o.state_shape_error?"true":"false")<<",\"stage_counts\":[";
  for(size_t k=0;k<r56_stage_labels.size();++k){if(k)s<<',';s<<"{\"id\":"<<k<<",\"label\":"<<local_json::quote(r56_stage_labels[k])<<",\"count\":"<<o.stage_counts[k]<<'}';}
  s<<"],\"metadata\":[";for(int k=0;k<o.metadata_count;++k){if(k)s<<',';const auto& x=o.metadata[k];s<<"{\"stage\":"<<x.stage<<",\"producer_id\":"<<x.producer_id<<",\"target_id\":"<<x.target_id<<",\"work\":"<<x.work<<",\"limit\":"<<x.limit<<",\"flags\":"<<x.flags<<",\"order_size\":"<<x.order_size<<",\"peak_lo\":"<<x.peak_lo<<",\"peak_hi\":"<<x.peak_hi<<'}';}
  s<<"],\"states\":[";
  auto ints=[&](const char* label,const auto& a,int n){s<<",\""<<label<<"\":[";for(int j=0;j<n;++j){if(j)s<<',';s<<static_cast<int64_t>(a[j]);}s<<']';};
  for(int k=0;k<o.state_count;++k){if(k)s<<',';const auto& x=o.states[k];s<<"{\"stage\":"<<x.stage<<",\"n\":"<<x.n<<",\"live\":"<<x.live<<",\"pending_provided\":"<<(x.pending_provided?"true":"false")<<",\"held_provided\":"<<(x.held_provided?"true":"false");ints("original_ids",x.original_ids,x.n);ints("prefix_ids",x.prefix_ids,x.prefix_size);ints("done",x.done,x.n);ints("users",x.users,x.n);ints("degree",x.degree,x.n);ints("held_ids",x.held_ids,x.held_size);ints("pending_ids",x.pending_ids,x.pending_size);s<<'}';}
  s<<"]}";return s.str();
}
