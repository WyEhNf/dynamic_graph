from pathlib import Path
base=Path('research/batch39/solution.cpp').read_text(encoding='utf-8')
s=base
def rep(a,b):
 global s
 assert a in s,a
 s=s.replace(a,b)
helpers=r'''
// Saturation is for priorities/lower bounds ONLY. Actual live allocations and
// timers are checked before addition, so INT64_MAX remains a legal value.
I positive_add(I a,I b) {return a>std::numeric_limits<I>::max()-b?std::numeric_limits<I>::max():a+b;}
I positive_mul(I a,I b) {return b && a>std::numeric_limits<I>::max()/b?std::numeric_limits<I>::max():a*b;}
I priority_sub(I a,I b) {return a< -std::numeric_limits<I>::max()+b?-std::numeric_limits<I>::max():a-b;}
bool checked_add(I a,I b,I& out) {if(a>std::numeric_limits<I>::max()-b)return false;out=a+b;return true;}
bool checked_mul(I a,I b,I& out) {if(b && a>std::numeric_limits<I>::max()/b)return false;out=a*b;return true;}
bool memory_fits(I limit,I live,I workspace,I output) {
  if(live>limit)return false;
  I left=limit-live;
  if(workspace>left)return false;
  return output<=left-workspace;
}
// Exact floor(a*b/d), clamped only AFTER division; no compiler extensions.
// Unsigned remainders below d (d<=INT64_MAX+1) can safely be doubled/added.
I priority_mul_div(I a,I b,uint64_t d) {
  if(!b)return 0;
  if(a<=std::numeric_limits<I>::max()/b)return static_cast<I>(static_cast<uint64_t>(a*b)/d);
  I q=0;uint64_t r=0,aq=static_cast<uint64_t>(a)/d,ar=static_cast<uint64_t>(a)%d;
  int bit=62;while(bit>0 && !(static_cast<uint64_t>(b)&(1ull<<bit)))--bit;
  for(;bit>=0;--bit) {
    r*=2;I carry=r>=d;if(carry)r-=d;q=positive_add(positive_mul(q,2),carry);
    if(static_cast<uint64_t>(b)&(1ull<<bit)){r+=ar;carry=r>=d;if(carry)r-=d;q=positive_add(q,positive_add(static_cast<I>(aq),carry));}
  }
  return q;
}
'''
rep('using I = int64_t;','using I = int64_t;\n'+helpers)
rep('I positive_add(I a,I b) {\n  return a>std::numeric_limits<I>::max()-b?std::numeric_limits<I>::max():a+b;\n}\n','')
rep('release[i]+=v[p].output_memory/static_cast<I>(out[p].size());','release[i]=positive_add(release[i],v[p].output_memory/static_cast<I>(out[p].size()));')
# Actual Event model
rep('c.stage=4;c.due=clock+h.event_record_time;','c.stage=4;if(completed<g.n && !checked_add(clock,h.event_record_time,c.due))return e;')
rep('c.stage=1;c.due=clock+static_cast<I>(t.wait.size())*h.event_wait_time;changed=true;', 'I delay;if(!checked_mul(static_cast<I>(t.wait.size()),h.event_wait_time,delay) || !checked_add(clock,delay,c.due))return e;c.stage=1;changed=true;')
rep('cores[type]+v.core_num>capacity || memory+v.workspace_memory+v.output_memory>h.memory_limit','v.core_num>capacity-cores[type] || !memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory)')
rep('e.peak=std::max(e.peak,memory);c.stage=3;c.due=clock+v.exec_time;changed=true;','e.peak=std::max(e.peak,memory);c.stage=3;if(!checked_add(clock,v.exec_time,c.due))return e;changed=true;')
rep('I next=std::numeric_limits<I>::max();\n    for(const auto& c:cursor) if(c.due>clock) next=std::min(next,c.due);\n    if(next==std::numeric_limits<I>::max()) return e;', 'I next=0;bool timer=false;\n    for(const auto& c:cursor)if(c.due>clock && (!timer || c.due<next)){next=c.due;timer=true;}\n    if(!timer)return e;')
# Actual serial model + validate full order, eliminating empty-oracle false success
rep('Evaluation e; I live=0;\n  std::vector<int> users', 'Evaluation e; I live=0;if(order.size()!=static_cast<size_t>(g.n))return e;\n  std::vector<unsigned char> seen(g.n);\n  std::vector<int> users')
rep('    live+=g.v[i].workspace_memory+g.v[i].output_memory;\n    e.peak=std::max(e.peak,live);if(live>h.memory_limit)return e;\n    e.time+=g.v[i].exec_time;live-=g.v[i].workspace_memory;', '    if(i<0 || i>=g.n || seen[i])return e;for(int p:g.in[i])if(!seen[p])return e;seen[i]=1;\n    if(!memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory))return e;\n    live+=g.v[i].workspace_memory;live+=g.v[i].output_memory;e.peak=std::max(e.peak,live);\n    if(!checked_add(e.time,g.v[i].exec_time,e.time))return e;live-=g.v[i].workspace_memory;')
# Safe priority arithmetic; keep small-input exact ordering
for a,b in [('g.release[i]-v.output_memory-v.workspace_memory','priority_sub(g.release[i]-v.output_memory,v.workspace_memory)'),('-v.workspace_memory-v.output_memory','-positive_add(v.workspace_memory,v.output_memory)'),('v.output_memory+v.workspace_memory','positive_add(v.output_memory,v.workspace_memory)'),('net-v.workspace_memory','priority_sub(net,v.workspace_memory)'),('-workspace-g.v[i].output_memory','-positive_add(workspace,g.v[i].output_memory)')]:rep(a,b)
rep('g.v[order[k-1]].workspace_memory+g.v[order[k]].workspace_memory>0','(g.v[order[k-1]].workspace_memory>0 || g.v[order[k]].workspace_memory>0)')
rep('g.v[p].workspace_memory+g.v[i].workspace_memory>0','(g.v[p].workspace_memory>0 || g.v[i].workspace_memory>0)')
rep('live+v.workspace_memory+v.output_memory<=h.memory_limit','memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory)')
rep('state.live+v.workspace_memory+v.output_memory>h.memory_limit','!memory_fits(h.memory_limit,state.live,v.workspace_memory,v.output_memory)')
# Scores whose cumulative sums can exceed actual live memory
for target,expr in [('release[i]','g.v[p].output_memory'),('release[j]','g.v[p].output_memory'),('attachment[p]','g.v[i].output_memory'),('prospective','std::max<I>(0,release[child]-g.v[child].output_memory)'),('live','g.v[p].output_memory'),('future','g.v[p].output_memory'),('prospective','std::max<I>(0,future-g.v[c].output_memory)'),('child.freed','g.v[p].output_memory'),('need','g.v[c].output_memory'),('need','workspace'),('credit','g.v[p].output_memory'),('released','g.v[p].output_memory'),('need','g.v[p].output_memory+g.v[p].workspace_memory'),('new_output','v.output_memory'),('inputs','g.v[p].output_memory')]:
 old=f'{target}+={expr};'
 if old in s:s=s.replace(old,f'{target}=positive_add({target},{expr if "+" not in expr else "positive_add(g.v[p].output_memory,g.v[p].workspace_memory)"});')
# Above live replacement only standalone g.v[p] score/oracle; undo exact restoration repaired below.
s=s.replace('if(!users[p])live=positive_add(live,g.v[p].output_memory);','if(!users[p])live+=g.v[p].output_memory;')
rep('g.v[p].output_memory*1024/static_cast<I>(g.out[p].size())','priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(g.out[p].size()))')
rep('g.v[p].output_memory*1024/std::max<I>(1,static_cast<I>(g.out[p].size()))','priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(std::max<size_t>(1,g.out[p].size())))')
# Individual affinity keys bounded by graph-size entry gates.
import re
s=re.sub(r'(affinity\[[^;]+?\])\+=weight;',r'\1=positive_add(\1,weight);',s)
rep('credit*1024/(need+1)','priority_mul_div(credit,1024,static_cast<uint64_t>(need)+1)')
rep('credit*1024/(new_output+1)','priority_mul_div(credit,1024,static_cast<uint64_t>(new_output)+1)')
rep('residual+=g.out[i].empty()?g.v[i].output_memory*1024:g.v[i].output_memory*1024*state.users[i]/static_cast<I>(g.out[i].size());','residual=positive_add(residual,g.out[i].empty()?positive_mul(g.v[i].output_memory,1024):priority_mul_div(g.v[i].output_memory,1024*static_cast<I>(state.users[i]),static_cast<uint64_t>(g.out[i].size())));')
# Probe allocation proof precedes exact peak sum
rep('const auto& v=g.v[i];peak=std::max(peak,next+v.workspace_memory+v.output_memory);\n        if(peak>h.memory_limit){fit=false;break;}', 'const auto& v=g.v[i];if(!memory_fits(h.memory_limit,next,v.workspace_memory,v.output_memory)){fit=false;break;}\n        peak=std::max(peak,next+v.workspace_memory+v.output_memory);')
rep('const auto& v=g.v[i];x.peak=std::max(x.peak,x.live+v.workspace_memory+v.output_memory);\n        if(x.peak>h.memory_limit){fit=false;break;}', 'const auto& v=g.v[i];if(!memory_fits(h.memory_limit,x.live,v.workspace_memory,v.output_memory)){fit=false;break;}\n        x.peak=std::max(x.peak,x.live+v.workspace_memory+v.output_memory);')
# Exact small serial DP: separate reachability from MAX peak.
rep('if(peak[mask]!=infinity)', 'if(mask==0 || last[mask]>=0)')
rep('I live=0;for(int i=0;i<g.n;++i)if((mask&(1u<<i)) && (!succ[i] || (succ[i]&~mask)))live+=g.v[i].output_memory;', 'I live=0;bool fits=true;for(int i=0;i<g.n;++i)if((mask&(1u<<i)) && (!succ[i] || (succ[i]&~mask)))if(!checked_add(live,g.v[i].output_memory,live)){fits=false;break;}if(!fits)continue;')
rep('unsigned next=mask|(1u<<i);I cost=std::max(peak[mask],live+g.v[i].workspace_memory+g.v[i].output_memory);\n      if(cost<peak[next])','if(!memory_fits(infinity,live,g.v[i].workspace_memory,g.v[i].output_memory))continue;\n      unsigned next=mask|(1u<<i);I cost=std::max(peak[mask],live+g.v[i].workspace_memory+g.v[i].output_memory);\n      if(last[next]<0 || cost<peak[next])')
rep('std::vector<int> order;for(unsigned mask=states-1;mask;)', 'if(states>1 && last[states-1]<0)return {};\n  std::vector<int> order;for(unsigned mask=states-1;mask;)')
# Pinned exact additions only for currently pending targets. Completed targets
# are never read; symmetric undo skips exactly targets already done before i.
rep('for(int target:retained_targets[i])pinned[target]+=g.v[i].output_memory;', 'for(int target:retained_targets[i])if(target!=i && !done[target])pinned[target]+=g.v[i].output_memory;')
rep('for(int target:retained_targets[i])pinned[target]-=g.v[i].output_memory;', 'for(int target:retained_targets[i])if(target!=i && !done[target])pinned[target]-=g.v[i].output_memory;')
rep('return positive_add(live,positive_add(g.v[i].workspace_memory,g.v[i].output_memory))<=h.memory_limit;', 'return memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory);')
rep('I required=mandatory[i];\n      for(int p:g.in[i])if(done[p])required-=g.v[p].output_memory;\n      if(positive_add(sink_live,positive_add(pinned[i],required))>h.memory_limit){impossible=true;break;}', 'I left=h.memory_limit;auto take=[&](I amount){if(amount>left)return false;left-=amount;return true;};\n      bool fits=take(sink_live) && take(pinned[i]) && take(g.v[i].workspace_memory) && take(g.v[i].output_memory);\n      for(int p:g.in[i])if(!done[p] && !take(g.v[p].output_memory))fits=false;\n      if(!fits){impossible=true;break;}')
rep('ca+=g.v[a].workspace_memory;cb+=g.v[b].workspace_memory;', 'ca=positive_add(ca,g.v[a].workspace_memory);cb=positive_add(cb,g.v[b].workspace_memory);')
# Estimated assignment times/priorities may saturate, actual Event evaluator
# rejects unrepresentable timestamps. Constructive variants also remain proposals.
rep('(s==first_owner?second:first)+h.event_record_time','positive_add((s==first_owner?second:first),h.event_record_time)')
rep('finish[p]+(result[p]!=s?h.event_record_time:0)','positive_add(finish[p],(result[p]!=s?h.event_record_time:0))')
rep('I end=start+waits*h.event_wait_time+g.v[i].exec_time;', 'I end=positive_add(positive_add(start,positive_mul(waits,h.event_wait_time)),g.v[i].exec_time);')
rep('end+=h.event_record_time+h.event_wait_time;', 'end=positive_add(end,positive_add(h.event_record_time,h.event_wait_time));')
for a,b in [('memory+v.workspace_memory+v.output_memory>h.memory_limit','!memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory)'),('cores[type]+v.core_num>cap','v.core_num>cap-cores[type]'),('local+=h.event_wait_time+h.event_record_time;','local=positive_add(local,positive_add(h.event_wait_time,h.event_record_time));'),('local+=h.event_record_time+h.event_wait_time;','local=positive_add(local,positive_add(h.event_record_time,h.event_wait_time));'),('g.rank[i]+local','positive_add(g.rank[i],local)'),('g.rank[i]-v.exec_time+local','positive_add(g.rank[i]-v.exec_time,local)'),('finish[p]+h.event_record_time','positive_add(finish[p],h.event_record_time)'),('finish[frontier[other]]+h.event_record_time','positive_add(finish[frontier[other]],h.event_record_time)'),('finish[i]+h.event_record_time','positive_add(finish[i],h.event_record_time)'),('clock+h.event_record_time','positive_add(clock,h.event_record_time)'),('start+static_cast<I>(waits.size())*h.event_wait_time+v.exec_time','positive_add(positive_add(start,positive_mul(static_cast<I>(waits.size()),h.event_wait_time)),v.exec_time)'),('due[s]+=static_cast<I>(waits.size())*h.event_wait_time;','due[s]=positive_add(due[s],positive_mul(static_cast<I>(waits.size()),h.event_wait_time));'),('due[s]=finish[i]=clock+v.exec_time;','if(!checked_add(clock,v.exec_time,due[s])){numeric_failure=true;return;}finish[i]=due[s];')]:
 if a in s:rep(a,b)
# Delayed overflow exits without bogus actual held counters.
rep('  auto start_compute=[&](int s) {','  bool numeric_failure=false;\n  auto start_compute=[&](int s) {')
rep('    if(completed==g.n)break;\n    I next=', '    if(completed==g.n)break;\n    I next=') # no-op assert; timer sentinel replace constructive loops separately
rep('for(int s=0;s<streams;++s){if(active[s]>=0)next=std::min(next,finish[active[s]]);else if(flow_ready[s]>clock)next=std::min(next,flow_ready[s]);}\n    if(next==std::numeric_limits<I>::max()){result.order.clear();return result;}', 'bool timer=false;for(int s=0;s<streams;++s){I at=active[s]>=0?finish[active[s]]:flow_ready[s];if(at>clock && (!timer || at<next)){next=at;timer=true;}}\n    if(!timer){result.order.clear();return result;}')
rep('for(int s=0;s<streams;++s){if(active[s]>=0){if(due[s]>clock)next=std::min(next,due[s]);}else if(flow_ready[s]>clock)next=std::min(next,flow_ready[s]);}\n    if(next==std::numeric_limits<I>::max()){result.order.clear();return result;}', 'bool timer=false;for(int s=0;s<streams;++s){I at=active[s]>=0?due[s]:flow_ready[s];if(at>clock && (!timer || at<next)){next=at;timer=true;}}\n    if(!timer || numeric_failure){result.order.clear();return result;}')
# Initial contention demand is a Boolean/priority only, saturation safe.
rep('memory_demand+=v.workspace_memory+v.output_memory;', 'memory_demand=positive_add(memory_demand,positive_add(v.workspace_memory,v.output_memory));')
rep('I ma=nodes[i].workspace_memory+nodes[i].output_memory,mb=nodes[j].workspace_memory+nodes[j].output_memory;', 'I ma=positive_add(nodes[i].workspace_memory,nodes[i].output_memory),mb=positive_add(nodes[j].workspace_memory,nodes[j].output_memory);')
# Prevent empty oracle order becoming a bogus successful serial plan / graph
# candidate key. Also use safe necessary live gates, not global output sums.
rep('    if(metrics.candidates>=budget)return {};','    if(order.size()!=static_cast<size_t>(graph.n) || metrics.candidates>=budget)return {};')
rep('  if(nodes.empty()) {metrics.time=metrics.peak=0;return {};}','''  if(nodes.empty()) {metrics.time=metrics.peak=0;return {};}
  I terminal_left=hw.memory_limit;
  for(int i=0;i<graph.n;++i) {
    I left=hw.memory_limit;auto take=[&](I amount){if(amount>left)return false;left-=amount;return true;};
    bool fits=take(nodes[i].workspace_memory) && take(nodes[i].output_memory);
    for(int p:graph.in[i])if(!take(nodes[p].output_memory))fits=false;
    if(!fits)throw std::runtime_error("Necessary direct-input memory gate exceeds capacity");
    if(graph.out[i].empty()){if(nodes[i].output_memory>terminal_left)throw std::runtime_error("Final output memory exceeds capacity");terminal_left-=nodes[i].output_memory;}
  }''')
s=s.replace('if(i<0 || i>=g.n || seen[i])return e;for(int p:g.in[i])if(!seen[p])return e;seen[i]=1;', 'if(i<0 || i>=g.n || seen[i])return e;\n    for(int p:g.in[i])if(!seen[p])return e;\n    seen[i]=1;')
s=s.replace('if(!checked_add(e.time,g.v[i].exec_time,e.time))return e;live-=g.v[i].workspace_memory;', 'if(!checked_add(e.time,g.v[i].exec_time,e.time))return e;\n    live-=g.v[i].workspace_memory;')
s=s.replace('release+=g.v[p].output_memory;', 'release=positive_add(release,g.v[p].output_memory);')
s=s.replace('  std::vector<I> mandatory(g.n);\n','').replace('    mandatory[i]=positive_add(g.v[i].workspace_memory,g.v[i].output_memory);\n    for(int p:g.in[i])mandatory[i]=positive_add(mandatory[i],g.v[p].output_memory);\n','')
Path('research/batch42/solution.cpp').write_text(s,encoding='utf-8')
# Independent validator: separately written checks, no shared helper dependency.
v=Path('src/simulator.cpp').read_text(encoding='utf-8')
v=v.replace('  int64_t now=0, memory=0;', '''  int64_t now=0, memory=0;
  auto advance=[](int64_t from,int64_t delay,int64_t& until){
    if(delay>std::numeric_limits<int64_t>::max()-from)return false;
    until=from+delay;return true;
  };
  auto reserve=[&](const OperatorNode& op){
    int64_t spare=hw.memory_limit-memory;
    if(op.workspace_memory>spare)return false;
    spare-=op.workspace_memory;return op.output_memory<=spare;
  };''')
v=v.replace('st.phase=4; st.until=now+hw.event_record_time;', 'st.phase=4;if(completed<n && !advance(now,hw.event_record_time,st.until))return fail("Record timestamp exceeds int64");')
v=v.replace('st.phase=1; st.until=now+static_cast<int64_t>(task.wait_before.size())*hw.event_wait_time;', '''int64_t count_wait=static_cast<int64_t>(task.wait_before.size());
          if(count_wait && hw.event_wait_time>std::numeric_limits<int64_t>::max()/count_wait)return fail("Wait duration exceeds int64");
          st.phase=1;if(!advance(now,count_wait*hw.event_wait_time,st.until))return fail("Wait timestamp exceeds int64");''')
v=v.replace('used[type]+v.core_num>capacity || memory+v.workspace_memory+v.output_memory>hw.memory_limit', 'v.core_num>capacity-used[type] || !reserve(v)')
v=v.replace('st.phase=3; st.until=now+v.exec_time; changed=true;', 'st.phase=3;if(!advance(now,v.exec_time,st.until))return fail("Compute timestamp exceeds int64");changed=true;')
v=v.replace('int64_t next=std::numeric_limits<int64_t>::max();\n    for(const auto& st:state) if(st.until>now) next=std::min(next,st.until);\n    if(next==std::numeric_limits<int64_t>::max())', 'int64_t next=0;bool scheduled=false;\n    for(const auto& st:state)if(st.until>now && (!scheduled || st.until<next)){next=st.until;scheduled=true;}\n    if(!scheduled)')
Path('research/batch42/simulator.cpp').write_text(v,encoding='utf-8')
print('prepared correctness candidate; default untouched')

