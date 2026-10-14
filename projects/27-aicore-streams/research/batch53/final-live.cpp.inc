// Exact final-live dominance at ONE completed prefix. Logical work units
// cover every new traversal, state test, count, memory read and arithmetic.
// This is not a cycle count. Existing 4n copying and all old charges remain.
bool release_cut_final_dominated(const Graph& g,
 const std::vector<int>& pending,const std::vector<unsigned char>& included,
 const std::vector<unsigned char>& completed,const std::vector<int>& remaining_users,
 I live,I incumbent,I& work,I limit,ProfileInteger& final,bool& dominated) {
  auto charge=[&](I amount){return cut_charge(work,limit,amount);};
  if(!charge(g.n))return false; // zero-initialize n counters
  std::vector<int> hits(g.n),touched;
  for(int i:pending) {
    if(!charge(1))return false; // pending-node traversal
    for(int p:g.in[i]) {
      if(!charge(2))return false; // original edge + completed-parent test
      if(completed[p]) {
        if(!charge(2))return false; // first-hit test + increment
        if(!hits[p]++)touched.push_back(p);
      }
    }
  }
  I retained=live;
  for(int p:touched) {
    if(!charge(2))return false; // distinct-parent traversal + users comparison
    if(hits[p]==remaining_users[p]) {
      if(!charge(3))return false; // output read + nonnegative guard + subtract
      if(g.v[p].output_memory>retained)throw std::logic_error("Invalid physical cut prefix");
      retained-=g.v[p].output_memory;
    }
  }
  if(!charge(1))return false; // exact wide conversion
  final=ProfileInteger(retained);
  for(int i:pending) {
    if(!charge(2))return false; // node traversal + original sink test
    bool held=g.out[i].empty();
    if(!held)for(int c:g.out[i]) {
      if(!charge(3))return false; // original edge + done + included tests
      if(!completed[c] && !included[c]){held=true;break;}
    }
    if(held) {
      if(!charge(2))return false; // output read + exact wide addition
      final+=ProfileInteger(g.v[i].output_memory);
    }
  }
  if(!charge(1))return false; // strict wide comparison; equality not pruned
  dominated=ProfileInteger(incumbent)<final;return true;
}

