#include "problem.h"
#include <algorithm>
#include <chrono>
#include <functional>
#include <limits>
#include <queue>
#include <set>
#include <stdexcept>
#include <map>
#include <tuple>
#include <unordered_map>

namespace aicore_detail {
using I = int64_t;

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

I scaled_priority(I priority,int capacity,int request) {
  const I limit=std::numeric_limits<I>::max(),quotient=priority/request,remainder=priority%request;
  if(quotient>limit/capacity)return limit;
  const I base=quotient*capacity,tail=remainder*capacity/request;
  return base>limit-tail?limit:base+tail;
}
struct Metrics { I candidates=0, feasible=0, time=-1, peak=-1, micros=0, duplicates=0, attempts=0, beam_expansions=0,beam_width=0, optimal_certificate=0,time_lower_bound=0,memory_lower_bound=0; };
thread_local Metrics metrics;
struct Graph {
  const std::vector<OperatorNode>& v;
  int n;
  std::unordered_map<int,int> index;
  std::vector<std::vector<int>> in,out;
  std::vector<I> rank, release,height;
  std::vector<int> topo;
  Graph(const HardwareInfo& h,const std::vector<OperatorNode>& nodes):v(nodes),n(static_cast<int>(nodes.size())),in(n),out(n),rank(n),release(n),height(n) {
    if(h.stream_num<1 || h.aic_core_num<0 || h.aiv_core_num<0 || h.memory_limit<0 ||
       h.event_wait_time<0 || h.event_record_time<0) throw std::invalid_argument("Invalid hardware");
    for(int i=0;i<n;++i) {
      const auto& x=v[i]; int type=static_cast<int>(x.core_type);
      if(!index.emplace(x.id,i).second) throw std::invalid_argument("Duplicate operator ID");
      if(type<0 || type>1 || x.core_num<1 || x.core_num>128 ||
         x.core_num>(type==0?h.aic_core_num:h.aiv_core_num) || x.exec_time<1 || x.exec_time>1000000000LL ||
         x.workspace_memory<0 || x.output_memory<0) throw std::invalid_argument("Invalid operator attributes");
    }
    std::vector<int> degree(n);
    for(int i=0;i<n;++i) {
      std::set<int> seen;
      for(int id:v[i].inputs) {
        if(!index.count(id) || !seen.insert(id).second || index.at(id)==i) throw std::invalid_argument("Invalid input IDs");
        int p=index.at(id); in[i].push_back(p); out[p].push_back(i); ++degree[i];
      }
    }
    for(int i=0;i<n;++i) if(!degree[i]) topo.push_back(i);
    for(size_t k=0;k<topo.size();++k) for(int j:out[topo[k]]) if(!--degree[j]) topo.push_back(j);
    if(static_cast<int>(topo.size())!=n) throw std::invalid_argument("Graph is cyclic");
    for(auto it=topo.rbegin();it!=topo.rend();++it) {
      int i=*it; for(int j:out[i]) {rank[i]=std::max(rank[i],rank[j]);height[i]=std::max(height[i],height[j]);} rank[i]+=v[i].exec_time;++height[i];
    }
    for(int i=0;i<n;++i) for(int p:in[i]) release[i]=positive_add(release[i],v[p].output_memory/static_cast<I>(out[p].size()));
  }
};

struct LowerBounds {I time=0,memory=0;};
LowerBounds lower_bounds(const HardwareInfo& h,const Graph& g) {
  LowerBounds b;I duration=0,work[2]={0,0},heavy_core[2]={0,0},heavy_memory=0,sinks=0,last_sink=std::numeric_limits<I>::max();
  for(int i=0;i<g.n;++i) {
    const auto& v=g.v[i];duration=positive_add(duration,v.exec_time);
    work[static_cast<int>(v.core_type)]=positive_add(work[static_cast<int>(v.core_type)],v.exec_time*v.core_num);
    int type=static_cast<int>(v.core_type),pool=type?h.aiv_core_num:h.aic_core_num;
    if(v.core_num>pool/2)heavy_core[type]=positive_add(heavy_core[type],v.exec_time);
    if(positive_add(v.workspace_memory,v.output_memory)>h.memory_limit/2)heavy_memory=positive_add(heavy_memory,v.exec_time);
    b.time=std::max(b.time,g.rank[i]);I parents=0;
    for(int p:g.in[i])parents=positive_add(parents,g.v[p].output_memory);
    b.memory=std::max(b.memory,positive_add(positive_add(v.workspace_memory,v.output_memory),parents));
    if(g.out[i].empty()) {sinks=positive_add(sinks,v.output_memory);last_sink=std::min(last_sink,positive_add(v.workspace_memory,parents));}
  }
  auto ceiling=[](I amount,int capacity){return amount/capacity+(amount%capacity!=0);};
  b.time=std::max(b.time,ceiling(duration,h.stream_num));
  for(int t=0;t<2;++t)if(work[t])b.time=std::max(b.time,ceiling(work[t],t?h.aiv_core_num:h.aic_core_num));
  // Compute intervals using more than half a resource are pairwise
  // disjoint. Core pools are separate; transient W+O shares one pool.
  b.time=std::max({b.time,heavy_core[0],heavy_core[1],heavy_memory});
  if(g.n)b.memory=std::max(b.memory,positive_add(sinks,last_sink));
  return b;
}
// Conditional on attaining the time lower bound: precedence-only windows
// still contain every real schedule. If both non-overlap orders are excluded,
// both workspaces/outputs and their distinct direct parent outputs coexist.
I forced_overlap_bound(const Graph& g,I time,I memory) {
  if(g.n>128)return memory;
  std::vector<I> earliest(g.n),latest_end(g.n);
  for(int i:g.topo){for(int p:g.in[i])earliest[i]=std::max(earliest[i],earliest[p]+g.v[p].exec_time);latest_end[i]=time-(g.rank[i]-g.v[i].exec_time);}
  std::vector<int> seen(g.n,-1);int epoch=0;
  for(int u=0;u<g.n;++u)for(int v=u+1;v<g.n;++v) {
    if(std::max(earliest[v],earliest[u]+g.v[u].exec_time)+g.v[v].exec_time<=latest_end[v] ||
       std::max(earliest[u],earliest[v]+g.v[v].exec_time)+g.v[u].exec_time<=latest_end[u])continue;
    I live=positive_add(positive_add(g.v[u].workspace_memory,g.v[u].output_memory),positive_add(g.v[v].workspace_memory,g.v[v].output_memory));
    ++epoch;seen[u]=seen[v]=epoch;
    for(int i:{u,v})for(int p:g.in[i])if(seen[p]!=epoch){seen[p]=epoch;live=positive_add(live,g.v[p].output_memory);}
    memory=std::max(memory,live);
  }
  return memory;
}

// Submission-side simulation is implemented separately from the local verifier.
struct Evaluation {bool valid=false; I time=0,peak=0;bool contended=false;};
Evaluation evaluate(const HardwareInfo& h,const Graph& g,const SchedulePlan& plan,bool generated=false) {
  std::vector<const StreamPlan*> flows;
  for(const auto& s:plan.streams)if(!s.tasks.empty())flows.push_back(&s);
  Evaluation e; const int streams=static_cast<int>(flows.size());
  if(streams>h.stream_num) return e;
  struct Task {int node,event; std::vector<int> wait;};
  std::vector<std::vector<Task>> tasks(streams);
  std::vector<int> owner(g.n,-1),position(g.n,-1),record(g.n,-1);
  std::unordered_map<int,int> event_owner;
  std::vector<int> dense_events(generated?g.n:0,-1);
  auto event_exists=[&](int id){return generated?(id>=0 && id<g.n && dense_events[id]>=0):event_owner.count(id)!=0;};
  auto event_index=[&](int id){return generated?dense_events[id]:event_owner.at(id);};
  int next_event=0;
  for(int s=0;s<streams;++s) for(const auto& t:flows[s]->tasks) {
    if(!g.index.count(t.op_id)) return e;
    int i=g.index.at(t.op_id); if(owner[i]>=0) return e;
    owner[i]=s; position[i]=static_cast<int>(tasks[s].size()); record[i]=t.record_after;
    if(t.record_after< -1)return e;
    if(t.record_after>=0) {
      if(generated){if(t.record_after>=g.n || event_exists(t.record_after))return e;dense_events[t.record_after]=next_event++;}
      else if(!event_owner.emplace(t.record_after,next_event++).second)return e;
    }
    tasks[s].push_back({i,t.record_after,t.wait_before});
  }
  for(int i=0;i<g.n;++i) if(owner[i]<0) return e;
  std::vector<int> recorder(next_event,-1),waited(next_event);
  for(int i=0;i<g.n;++i) if(record[i]>=0) recorder[event_index(record[i])]=i;
  for(int s=0;s<streams;++s) for(auto& t:tasks[s]) {
    std::sort(t.wait.begin(),t.wait.end());
    if(std::adjacent_find(t.wait.begin(),t.wait.end())!=t.wait.end()) return e;
    for(int p:g.in[t.node]) {
      if(owner[p]==s) {if(position[p]>=position[t.node]) return e;}
      else if(record[p]<0 || !std::binary_search(t.wait.begin(),t.wait.end(),record[p])) return e;
    }
    for(int& w:t.wait) {
      if(!event_exists(w)) return e;
      w=event_index(w); if(owner[recorder[w]]==s) return e; ++waited[w];
    }
    if(t.event>=0) t.event=event_index(t.event);
  }
  for(int x:waited) if(!x) return e;
  struct Cursor {size_t index=0; int stage=0; I due=-1;};
  std::vector<Cursor> cursor(streams);
  std::vector<bool> ready(next_event),done(g.n);
  std::vector<int> users(g.n); for(int i=0;i<g.n;++i) users[i]=static_cast<int>(g.out[i].size());
  int cores[2]={0,0},completed=0; I memory=0,clock=0;
  while(completed<g.n) {
    bool changed=true;
    while(changed && completed<g.n) {
      changed=false;
      for(int s=0;s<streams;++s) {
        auto& c=cursor[s]; if(c.index==tasks[s].size() || c.due!=clock) continue;
        auto& t=tasks[s][c.index]; const auto& v=g.v[t.node];
        if(c.stage==1) {c.stage=2;c.due=-1;changed=true;}
        else if(c.stage==3) {
          cores[static_cast<int>(v.core_type)]-=v.core_num; memory-=v.workspace_memory;
          done[t.node]=true; ++completed; e.time=clock;
          for(int p:g.in[t.node]) if(--users[p]==0) memory-=g.v[p].output_memory;
          if(t.event>=0 && h.event_record_time) {c.stage=4;if(completed<g.n && !checked_add(clock,h.event_record_time,c.due))return e;}
          else {if(t.event>=0)ready[t.event]=true; ++c.index;c.stage=0;c.due=-1;}
          changed=true;
        } else if(c.stage==4) {ready[t.event]=true;++c.index;c.stage=0;c.due=-1;changed=true;}
      }
      if(completed==g.n) break;
      for(int s=0;s<streams;++s) {
        auto& c=cursor[s]; if(c.index==tasks[s].size()) continue;
        auto& t=tasks[s][c.index]; const auto& v=g.v[t.node];
        if(c.stage==0) {
          bool all=true; for(int w:t.wait) if(!ready[w]) all=false;
          if(!all) continue;
          I delay;if(!checked_mul(static_cast<I>(t.wait.size()),h.event_wait_time,delay) || !checked_add(clock,delay,c.due))return e;c.stage=1;changed=true;
          if(c.due==clock) {c.stage=2;c.due=-1;}
        }
        if(c.stage==2) {
          int type=static_cast<int>(v.core_type),capacity=type==0?h.aic_core_num:h.aiv_core_num;
          if(v.core_num>capacity-cores[type] || !memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory)) {e.contended=true;continue;}
          for(int p:g.in[t.node]) if(!done[p]) return e;
          cores[type]+=v.core_num; memory+=v.workspace_memory+v.output_memory;
          e.peak=std::max(e.peak,memory);c.stage=3;if(!checked_add(clock,v.exec_time,c.due))return e;changed=true;
        }
      }
    }
    if(completed==g.n) break;
    I next=0;bool timer=false;
    for(const auto& c:cursor)if(c.due>clock && (!timer || c.due<next)){next=c.due;timer=true;}
    if(!timer)return e;
    clock=next;
  }
  e.valid=true;return e;
}

std::vector<int> ordering(const Graph& g,int mode) {
  auto score=[&](int i)->std::tuple<I,I,I> {
    const auto& v=g.v[i];
    if(mode==1) return {g.release[i]-v.output_memory,-v.workspace_memory,g.rank[i]};
    if(mode==2) return {-positive_add(v.workspace_memory,v.output_memory),g.rank[i],g.release[i]};
    if(mode==3) return {-static_cast<I>(v.id),0,0};
    if(mode==4) return {g.rank[i]/std::max<I>(1,positive_add(v.output_memory,v.workspace_memory)),g.release[i],g.rank[i]};
    if(mode==5) return {priority_sub(g.release[i]-v.output_memory,v.workspace_memory),g.rank[i],-static_cast<I>(v.id)};
    return {g.rank[i],g.release[i]-v.output_memory,-static_cast<I>(v.id)};
  };
  auto less=[&](int a,int b) {return score(a)!=score(b)?score(a)<score(b):g.v[a].id>g.v[b].id;};
  std::priority_queue<int,std::vector<int>,decltype(less)> ready(less);
  std::vector<int> degree(g.n),result;
  for(int i=0;i<g.n;++i) {degree[i]=static_cast<int>(g.in[i].size());if(!degree[i])ready.push(i);}
  while(!ready.empty()) {int i=ready.top();ready.pop();result.push_back(i);for(int j:g.out[i])if(!--degree[j])ready.push(j);}
  return result;
}

// A single stream has no events and cannot overlap computations. This exact
// linear model uses the same DIRECT-consumer lifetime as the general model.
Evaluation serial_evaluate(const HardwareInfo& h,const Graph& g,const std::vector<int>& order) {
  Evaluation e; I live=0;if(order.size()!=static_cast<size_t>(g.n))return e;
  std::vector<unsigned char> seen(g.n);
  std::vector<int> users(g.n);for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  for(int i:order) {
    if(i<0 || i>=g.n || seen[i])return e;
    for(int p:g.in[i])if(!seen[p])return e;
    seen[i]=1;
    if(!memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory))return e;
    live+=g.v[i].workspace_memory;live+=g.v[i].output_memory;e.peak=std::max(e.peak,live);
    if(!checked_add(e.time,g.v[i].exec_time,e.time))return e;
    live-=g.v[i].workspace_memory;
    for(int p:g.in[i])if(!--users[p])live-=g.v[p].output_memory;
  }
  e.valid=true;return e;
}

// Normalize event labels to their producer, but preserve compressed stream
// IDs and task order. Exact bucket comparison prevents hash-collision pruning.
std::vector<int> signature(const Graph& g,const std::vector<int>& order,const std::vector<int>& assignment,int streams,int guards,
                           const std::vector<std::pair<int,int>>& extra) {
  // Task order/membership determine every original-data event. Only the
  // additional cross-stream guards need storing; event labels are immaterial.
  std::vector<std::vector<int>> flows(streams);for(int i:order)flows[assignment[i]].push_back(i);
  std::vector<int> key;key.reserve(g.n+streams+1);key.push_back(0);
  for(const auto& flow:flows)if(!flow.empty()){++key[0];key.push_back(static_cast<int>(flow.size()));key.insert(key.end(),flow.begin(),flow.end());}
  std::vector<std::pair<int,int>> edges=extra;
  if(guards)for(size_t k=1;k<order.size();++k)if(guards==1 || (g.v[order[k-1]].workspace_memory>0 || g.v[order[k]].workspace_memory>0))edges.emplace_back(order[k-1],order[k]);
  edges.erase(std::remove_if(edges.begin(),edges.end(),[&](auto e){return assignment[e.first]==assignment[e.second] || std::find(g.in[e.second].begin(),g.in[e.second].end(),e.first)!=g.in[e.second].end();}),edges.end());
  std::sort(edges.begin(),edges.end());edges.erase(std::unique(edges.begin(),edges.end()),edges.end());
  key.push_back(static_cast<int>(edges.size()));for(auto e:edges){key.push_back(e.first);key.push_back(e.second);}
  return key;
}

// Dynamic list priorities credit a producer output only when the candidate
// is its LAST remaining direct consumer. Ready scores only change when a
// producer has one consumer left; lazy versions make those updates cheap.
std::vector<int> memory_ordering(const HardwareInfo& h,const Graph& g,int mode) {
  using Score=std::tuple<I,I,I,I>;
  struct Entry {Score score;int node,version;bool operator<(const Entry& b)const{return score!=b.score?score<b.score:node>b.node;}};
  std::priority_queue<Entry> queue;
  std::vector<int> users(g.n),degree(g.n),version(g.n);std::vector<I> release(g.n),attachment(g.n);std::vector<bool> done(g.n);
  for(int i=0;i<g.n;++i){users[i]=static_cast<int>(g.out[i].size());degree[i]=static_cast<int>(g.in[i].size());}
  for(int i=0;i<g.n;++i)for(int p:g.in[i])if(users[p]==1)release[i]=positive_add(release[i],g.v[p].output_memory);
  auto score=[&](int i)->Score {
    const auto& v=g.v[i];I net=release[i]-v.output_memory;
    if(mode==0)return {net,-v.workspace_memory,g.rank[i],0};
    if(mode==1)return {priority_sub(net,v.workspace_memory),net,g.rank[i],0};
    if(mode==3)return {g.height[i],net,-v.workspace_memory,0};
    if(mode==4 || mode==5) {
      I prospective=0,opening=std::numeric_limits<I>::max();
      I shared=0;
      for(int child:g.out[i])if(!done[child]) {
        opening=std::min<I>(opening,degree[child]);
        if(degree[child]==1)prospective=positive_add(prospective,std::max<I>(0,release[child]-g.v[child].output_memory));
        if(mode==5 && g.in[child].size()<=64){I live=0;for(int p:g.in[child])if(done[p])live=positive_add(live,g.v[p].output_memory);shared=std::max(shared,live);}
      }
      // When no output is live yet, prefer a consumer needing fewer missing
      // inputs. This opens a compact frontier rather than an arbitrary centre
      // of a memory window. Thereafter attachment follows surviving inputs.
      if(mode==4)return {net,prospective,attachment[i],-opening};
      if(net>=0)return {2,net,prospective,-opening};
      if(shared>0)return {1,prospective,shared,-opening};
      return {0,-opening,-positive_add(v.workspace_memory,v.output_memory),g.rank[i]};
    }
    return {-positive_add(v.workspace_memory,v.output_memory),net,g.rank[i],0};
  };
  auto push=[&](int i){queue.push({score(i),i,++version[i]});};
  for(int i=0;i<g.n;++i)if(!degree[i])push(i);
  std::vector<int> result;result.reserve(g.n);I live=0;
  while(static_cast<int>(result.size())<g.n) {
    std::vector<Entry> blocked;int chosen=-1;
    while(!queue.empty()) {
      auto e=queue.top();queue.pop();if(done[e.node] || e.version!=version[e.node])continue;
      const auto& v=g.v[e.node];
      if(memory_fits(h.memory_limit,live,v.workspace_memory,v.output_memory)){chosen=e.node;break;}
      blocked.push_back(e);
    }
    for(const auto& e:blocked)queue.push(e);
    if(chosen<0)return {};
    int i=chosen;result.push_back(i);done[i]=true;live+=g.v[i].output_memory;
    for(int p:g.in[i]) {
      if(!--users[p])live-=g.v[p].output_memory;
      else if(users[p]==1)for(int j:g.out[p])if(!done[j]){release[j]=positive_add(release[j],g.v[p].output_memory);if(!degree[j])push(j);break;}
    }
    for(int j:g.out[i]) {
      if(!--degree[j])push(j);
      else if((mode==4 || mode==5) && g.in[j].size()<=64)for(int p:g.in[j])if(!done[p]) {
        attachment[p]=positive_add(attachment[p],g.v[i].output_memory);
        if(!degree[p])push(p);
      }
    }
  }
  return result;
}

// Bounded serial-frontier beam for <=512 nodes. Every partial state checks
// exact allocation and DIRECT-user release. It branches on several feasible
// ready nodes and deduplicates completed sets, retaining the lowest peak for
// identical sets. No serial order is claimed globally optimal.
std::vector<int> beam_ordering(const HardwareInfo& h,const Graph& g,int width=8,int branching=6,int mode=0) {
  if(g.n>512)return {};
  struct State {std::vector<int> degree,users,ready,order;std::vector<unsigned char> done;I live=0,peak=0,freed=0;uint64_t hash=0;};
  State initial;initial.degree.resize(g.n);initial.users.resize(g.n);initial.done.resize(g.n);
  for(int i=0;i<g.n;++i){initial.degree[i]=static_cast<int>(g.in[i].size());initial.users[i]=static_cast<int>(g.out[i].size());if(!initial.degree[i])initial.ready.push_back(i);}
  std::vector<State> beam{initial};
  auto mix=[](uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);};
  for(int depth=0;depth<g.n;++depth) {
    std::vector<State> children;
    for(const auto& state:beam) {
      using Score=std::tuple<I,I,I,I>;std::vector<std::pair<Score,int>> options;
      for(int i:state.ready) {
        const auto& v=g.v[i];if(!memory_fits(h.memory_limit,state.live,v.workspace_memory,v.output_memory))continue;
        I released=0;for(int p:g.in[i])if(state.users[p]==1)released=positive_add(released,g.v[p].output_memory);
        I net=released-v.output_memory,opening=std::numeric_limits<I>::max(),prospective=0,shared=0;
        for(int c:g.out[i])if(!state.done[c] && g.in[c].size()<=64) {
          opening=std::min<I>(opening,state.degree[c]);I live=0,future=0;
          for(int p:g.in[c]){if(state.done[p])live=positive_add(live,g.v[p].output_memory);if(state.users[p]==1)future=positive_add(future,g.v[p].output_memory);}
          shared=std::max(shared,live);if(state.degree[c]==1)prospective=positive_add(prospective,std::max<I>(0,future-g.v[c].output_memory));
        }
        Score score=net>=0?Score{2,net,prospective,-opening}:(shared>0?Score{1,prospective,shared,-opening}:Score{0,-opening,-positive_add(v.workspace_memory,v.output_memory),g.rank[i]});
        options.emplace_back(score,i);
      }
      std::sort(options.begin(),options.end(),[&](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:g.v[a.second].id<g.v[b.second].id;});
      if(options.size()>static_cast<size_t>(branching))options.resize(branching);
      for(auto option:options) {
        int i=option.second;State child=state;++metrics.beam_expansions;child.hash^=mix(static_cast<uint64_t>(i));
        child.peak=std::max(child.peak,child.live+g.v[i].workspace_memory+g.v[i].output_memory);child.live+=g.v[i].output_memory;child.done[i]=1;child.order.push_back(i);
        auto it=std::find(child.ready.begin(),child.ready.end(),i);*it=child.ready.back();child.ready.pop_back();
        for(int p:g.in[i])if(!--child.users[p]){child.live-=g.v[p].output_memory;child.freed=positive_add(child.freed,g.v[p].output_memory);}
        for(int c:g.out[i])if(!--child.degree[c])child.ready.push_back(c);
        children.push_back(std::move(child));
      }
    }
    if(children.empty())return {};
    auto score=[&](const State& state){I nearest=std::numeric_limits<I>::max();for(int i=0;i<g.n;++i)if(!state.done[i] && !g.in[i].empty()) {
      bool active=false;for(int p:g.in[i])if(state.done[p] && g.v[p].output_memory){active=true;break;}if(active)nearest=std::min<I>(nearest,state.degree[i]);
    }
      if(mode==1){I residual=0;for(int i=0;i<g.n;++i)if(state.done[i])residual=positive_add(residual,g.out[i].empty()?positive_mul(g.v[i].output_memory,1024):priority_mul_div(g.v[i].output_memory,1024*static_cast<I>(state.users[i]),static_cast<uint64_t>(g.out[i].size())));return std::make_tuple(residual,state.live,state.peak,-state.freed);}
      return std::make_tuple(-state.freed,nearest,state.live,state.peak);};
    std::vector<std::tuple<I,I,I,I>> scores;for(const auto& state:children)scores.push_back(score(state));
    std::vector<int> positions(children.size());for(size_t k=0;k<positions.size();++k)positions[k]=static_cast<int>(k);
    std::stable_sort(positions.begin(),positions.end(),[&](int a,int b){return scores[a]<scores[b];});
    std::unordered_map<uint64_t,std::vector<int>> unique;std::vector<State> next;next.reserve(width);
    for(int k:positions) {
      auto& bucket=unique[children[k].hash];bool duplicate=false;for(int j:bucket)if(next[j].done==children[k].done){duplicate=true;break;}
      if(duplicate)continue;
      bucket.push_back(static_cast<int>(next.size()));next.push_back(std::move(children[k]));if(next.size()==static_cast<size_t>(width))break;
    }
    beam=std::move(next);metrics.beam_width=std::max<I>(metrics.beam_width,beam.size());
  }
  return beam.front().order;
}

// Complete a target together with its missing ancestors, checking the actual
// serial allocation/release of the whole bundle before choosing it. This
// avoids greedily opening several incomplete consumer frontiers. Ancestor
// count and graph size are bounded; a rejected bundle is not a proof of no
// feasible order. Temporary consumer counts are rolled back after each probe.
std::vector<int> bundle_ordering(const HardwareInfo& h,const Graph& g,int mode) {
  if(g.n>4096)return {};
  const bool grouped=mode>=21;const int objective=mode%3;const int group_limit=mode>=30?8:4;
  std::vector<std::vector<int>> members;
  if(grouped) {
    members.resize(g.n);std::vector<int> parent(g.n),size(g.n,1);for(int i=0;i<g.n;++i)parent[i]=i;
    auto root=[&](int i){while(parent[i]!=i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
    std::unordered_map<int,I> affinity;bool wide_affinity=false;
    for(int p=0;p<g.n;++p)if(g.v[p].output_memory && g.out[p].size()>=2 && g.out[p].size()<=static_cast<size_t>(group_limit)) {
      std::vector<int> children;for(int c:g.out[p])if(g.out[c].empty() || g.v[c].workspace_memory>=g.v[c].output_memory)children.push_back(c);
      if(mode>=24){I child_work=0;for(int c:children)child_work+=g.v[c].exec_time;if(g.v[p].exec_time*static_cast<I>(children.size())>child_work)continue;}
      if(g.out[p].size()>4 && children.size()>=2)wide_affinity=true;
      I weight=std::max<I>(1,priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(g.out[p].size()))/g.v[p].exec_time);
      for(size_t a=0;a<children.size();++a)for(size_t b=a+1;b<children.size();++b){int i=std::min(children[a],children[b]),j=std::max(children[a],children[b]);affinity[i*g.n+j]=positive_add(affinity[i*g.n+j],weight);}
    }
    std::vector<std::pair<I,int>> edges;for(const auto& x:affinity)edges.emplace_back(x.second,x.first);
    std::sort(edges.begin(),edges.end(),[](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:a.second<b.second;});
    for(const auto& edge:edges){int a=root(edge.second/g.n),b=root(edge.second%g.n);if(a!=b && size[a]+size[b]<=group_limit){parent[b]=a;size[a]+=size[b];}}
    for(int i=0;i<g.n;++i)members[root(i)].push_back(i);
    if(mode>=33) {
      bool wide_group=false;int target_groups=0;
      for(const auto& group:members) {
        if(group.size()>4)wide_group=true;
        for(int c:group)if(!g.in[c].empty() || g.out[c].empty()){++target_groups;break;}
      }
      // <=128 initial targets never activate the changing shortlist; target
      // count only decreases. Wider groups are an empirical cost trigger.
      if(!wide_group || target_groups<=128)return {};
    }
    if(mode>=30 && mode<33 && !wide_affinity) {
      bool expanded=false;for(const auto& group:members)if(group.size()>4){expanded=true;break;}
      // Without any new affinity edges or merges beyond four members the
      // preceding owner-mode traversals are identical, so skip repetition.
      if(!expanded)return {};
    }
    for(auto& group:members)std::sort(group.begin(),group.end(),[&](int a,int b){return g.v[a].workspace_memory!=g.v[b].workspace_memory?g.v[a].workspace_memory<g.v[b].workspace_memory:g.v[a].id<g.v[b].id;});
  }
  // Ordering-only owner preference: a unique co-consumer group with at
  // least two users is completed before isolated users of the same input.
  // These edges never enter event assembly or original output user counts.
  std::vector<std::vector<int>> preferred_in;
  if(mode>=27) {
    preferred_in=g.in;std::vector<int> group_of(g.n),count(g.n),touched;
    for(int k=0;k<g.n;++k)for(int c:members[k])group_of[c]=k;
    for(int p=0;p<g.n;++p)if(g.v[p].output_memory && g.out[p].size()>=3) {
      for(int c:g.out[p]){int k=group_of[c];if(!count[k]++)touched.push_back(k);}
      int owner=-1,maximum=1;bool tie=false;
      for(int k:touched)if(count[k]>maximum){owner=k;maximum=count[k];tie=false;}else if(count[k]==maximum)tie=true;
      if(owner>=0 && !tie) {
        std::vector<int> owner_users;for(int c:g.out[p])if(group_of[c]==owner)owner_users.push_back(c);
        for(int c:g.out[p])if(group_of[c]!=owner)preferred_in[c].insert(preferred_in[c].end(),owner_users.begin(),owner_users.end());
      }
      for(int k:touched)count[k]=0;
      touched.clear();
    }
    std::vector<int> degree(g.n),queue;std::vector<std::vector<int>> after(g.n);
    for(int i=0;i<g.n;++i){auto& in=preferred_in[i];std::sort(in.begin(),in.end());in.erase(std::unique(in.begin(),in.end()),in.end());degree[i]=static_cast<int>(in.size());for(int p:in)after[p].push_back(i);if(!degree[i])queue.push_back(i);}
    for(size_t k=0;k<queue.size();++k)for(int c:after[queue[k]])if(!--degree[c])queue.push_back(c);
    if(static_cast<int>(queue.size())!=g.n)return {};
  }
  const auto& traversal_in=preferred_in.empty()?g.in:preferred_in;
  std::vector<int> hint_group;
  if(mode>=33){hint_group.resize(g.n);for(int k=0;k<g.n;++k)for(int c:members[k])hint_group[c]=k;}
  std::vector<int> users(g.n),marks(g.n);std::vector<unsigned char> done(g.n);int epoch=0;
  for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  std::vector<int> result;result.reserve(g.n);I live=0;
  while(static_cast<int>(result.size())<g.n) {
    using Score=std::tuple<I,I,I,I>;
    Score best{std::numeric_limits<I>::min(),0,0,0};std::vector<int> selected;
    std::vector<int> targets;
    for(int i=0;i<g.n;++i) {
      if(!grouped){if(!done[i] && (!g.in[i].empty() || g.out[i].empty()))targets.push_back(i);}
      else for(int c:members[i])if(!done[c] && (!g.in[c].empty() || g.out[c].empty())){targets.push_back(i);break;}
    }
    if(g.n>512 && targets.size()>128) {
      using Hint=std::tuple<I,I,I>;std::vector<std::vector<Hint>> hints(4,std::vector<Hint>(g.n));
      std::vector<int> parent_uses(mode>=33?g.n:0),touched;
      for(int i:targets) {
        I need=g.v[i].output_memory,credit=0,released=0,missing=0;
        I workspace=g.v[i].workspace_memory;
        if(mode>=33) {
          need=workspace=0;
          for(int c:members[i])if(!done[c]) {
            need=positive_add(need,g.v[c].output_memory);workspace=std::max(workspace,g.v[c].workspace_memory);
            for(int p:g.in[c]){if(!parent_uses[p]++)touched.push_back(p);}
          }
          need=positive_add(need,workspace);
          for(int p:touched) {
            if(done[p]){credit=positive_add(credit,g.v[p].output_memory);if(users[p]==parent_uses[p])released=positive_add(released,g.v[p].output_memory);}
            else if(hint_group[p]!=i){need=positive_add(need,positive_add(g.v[p].output_memory,g.v[p].workspace_memory));++missing;}
            parent_uses[p]=0;
          }
          touched.clear();
        } else for(int p:g.in[i])if(done[p]){credit=positive_add(credit,g.v[p].output_memory);if(users[p]==1)released=positive_add(released,g.v[p].output_memory);}else{need=positive_add(need,positive_add(g.v[p].output_memory,g.v[p].workspace_memory));++missing;}
        hints[0][i]={released-need,credit,-missing};hints[1][i]={-need,credit,-missing};
        hints[2][i]={priority_mul_div(credit,1024,static_cast<uint64_t>(need)+1),-missing,-need};hints[3][i]={-missing,credit,-positive_add(workspace,g.v[i].output_memory)};
      }
      std::set<int> selected_targets;
      for(int hint=0;hint<4;++hint) {
        std::sort(targets.begin(),targets.end(),[&](int a,int b){return hints[hint][a]!=hints[hint][b]?hints[hint][a]>hints[hint][b]:g.v[a].id<g.v[b].id;});
        for(size_t k=0;k<std::min<size_t>(32,targets.size());++k)selected_targets.insert(targets[k]);
      }
      targets.assign(selected_targets.begin(),selected_targets.end());
    }
    for(int target:targets) {
      ++epoch;std::vector<int> bundle;std::vector<std::pair<int,size_t>> stack;
      if(grouped){for(int c:members[target])if(!done[c])stack.emplace_back(c,0);}
      else stack.emplace_back(target,0);
      int visited=0;bool bounded=true;
      while(!stack.empty()) {
        auto& frame=stack.back();int i=frame.first;
        if(done[i] || marks[i]==epoch){stack.pop_back();continue;}
        if(!frame.second && ++visited>(grouped?128:64)){bounded=false;break;}
        while(frame.second<traversal_in[i].size() && (done[traversal_in[i][frame.second]] || marks[traversal_in[i][frame.second]]==epoch))++frame.second;
        if(frame.second<traversal_in[i].size())stack.emplace_back(traversal_in[i][frame.second++],0);
        else {marks[i]=epoch;bundle.push_back(i);stack.pop_back();}
      }
      if(!bounded)continue;
      I next=live,peak=live,new_output=0,credit=0;bool fit=true;
      std::vector<int> touched;
      for(int i:bundle) {
        const auto& v=g.v[i];if(!memory_fits(h.memory_limit,next,v.workspace_memory,v.output_memory)){fit=false;break;}
        peak=std::max(peak,next+v.workspace_memory+v.output_memory);
        next+=v.output_memory;new_output=positive_add(new_output,v.output_memory);
        for(int p:g.in[i]) {
          if(done[p])credit=positive_add(credit,g.v[p].output_memory);
          touched.push_back(p);if(!--users[p])next-=g.v[p].output_memory;
        }
      }
      for(int p:touched)++users[p];
      if(!fit)continue;
      I gain=live-next;
      Score score=objective==0?Score{gain,credit,-peak,-static_cast<I>(bundle.size())}:
        objective==1?Score{-new_output,credit,gain,-peak}:Score{priority_mul_div(credit,1024,static_cast<uint64_t>(new_output)+1),gain,-peak,-static_cast<I>(bundle.size())};
      if(selected.empty() || score>best || (score==best && g.v[target].id<g.v[selected.back()].id)){best=score;selected=std::move(bundle);}
    }
    if(selected.empty())return {};
    for(int i:selected) {
      done[i]=1;result.push_back(i);live+=g.v[i].output_memory;
      for(int p:g.in[i])if(!--users[p])live-=g.v[p].output_memory;
    }
  }
  return result;
}

// Project serial feasibility to completed sink-ancestor closures. A node is
// completed exactly when at least one selected sink contains it. Therefore
// live memory and remaining DIRECT users depend on the sink subset alone;
// failed subsets can be memoized. Each transition uses a fixed iterative DFS
// prerequisite order, so this is NOT complete over all serial node orders.
// It is bounded by 18 closure groups, 512 nodes and eight million probes.
// Partitioned profiles accept up to 72 or 144 sinks, in groups <=4 or <=8.
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
  for(int p=0;p<g.n;++p)if(s.position[p]<0 && g.v[p].output_memory && g.out[p].size()>=2 && g.out[p].size()<=16) {
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

std::vector<int> sink_projection_order(const HardwareInfo& h,const Graph& g,bool partition=false,bool wide=false) {
  if(g.n>512)return {};
  std::vector<int> sinks;for(int i=0;i<g.n;++i)if(g.out[i].empty())sinks.push_back(i);
  if(wide && (sinks.size()<=72 || sinks.size()>144))return {};
  std::vector<std::vector<int>> groups;
  for(int i:sinks)groups.push_back({i});
  if(sinks.size()>18) {
    if(!partition || sinks.size()>(wide?144u:72u))return {};
    std::vector<int> owner(g.n,-1),parent(sinks.size()),size(sinks.size(),1);
    for(size_t i=0;i<sinks.size();++i){owner[sinks[i]]=static_cast<int>(i);parent[i]=static_cast<int>(i);}
    auto root=[&](int i){while(parent[i]!=i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
    std::unordered_map<int,I> affinity;
    for(int p=0;p<g.n;++p)if(g.v[p].output_memory && !g.out[p].empty() && g.out[p].size()<=16) {
      std::vector<int> children;for(int c:g.out[p])if(owner[c]>=0)children.push_back(owner[c]);
      I weight=priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(g.out[p].size()));
      if(wide)weight=std::max<I>(1,weight/g.v[p].exec_time);
      for(size_t a=0;a<children.size();++a)for(size_t b=a+1;b<children.size();++b){int i=std::min(children[a],children[b]),j=std::max(children[a],children[b]);affinity[i*static_cast<int>(sinks.size())+j]=positive_add(affinity[i*static_cast<int>(sinks.size())+j],weight);}
    }
    std::vector<std::pair<I,int>> edges;for(const auto& x:affinity)edges.emplace_back(x.second,x.first);
    std::sort(edges.begin(),edges.end(),[](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:a.second<b.second;});
    int count=static_cast<int>(sinks.size());
    for(const auto& edge:edges) {
      int a=root(edge.second/static_cast<int>(sinks.size())),b=root(edge.second%static_cast<int>(sinks.size()));
      if(a==b || size[a]+size[b]>(wide?8:4))continue;
      parent[b]=a;size[a]+=size[b];if(--count==18)break;
    }
    if(count>18)return {};
    std::vector<std::vector<int>> merged(sinks.size());for(size_t i=0;i<sinks.size();++i)merged[root(static_cast<int>(i))].push_back(sinks[i]);
    groups.clear();for(auto& members:merged)if(!members.empty())groups.push_back(std::move(members));
  } else if(partition)return {};
  const unsigned full=(1u<<groups.size())-1;std::vector<unsigned> cover(g.n);
  std::vector<std::vector<int>> closure(groups.size());
  for(size_t k=0;k<groups.size();++k) {
    std::vector<unsigned char> emitted(g.n);std::vector<std::pair<int,size_t>> stack;
    for(int sink:groups[k])stack.emplace_back(sink,0);
    while(!stack.empty()) {
      auto& f=stack.back();int i=f.first;if(emitted[i]){stack.pop_back();continue;}
      while(f.second<g.in[i].size() && emitted[g.in[i][f.second]])++f.second;
      if(f.second<g.in[i].size())stack.emplace_back(g.in[i][f.second++],0);
      else {emitted[i]=1;cover[i]|=1u<<k;closure[k].push_back(i);stack.pop_back();}
    }
  }
  std::vector<unsigned char> visited(full+1);std::vector<int> initial(g.n),result;
  for(int i=0;i<g.n;++i)initial[i]=static_cast<int>(g.out[i].size());
  I work=0;bool exhausted=false;
  struct Option {unsigned bit;I live,peak;std::vector<int> order,users;};
  std::function<bool(unsigned,I,const std::vector<int>&)> search;
  search=[&](unsigned mask,I live,const std::vector<int>& users) {
    if(mask==full)return true;
    if(visited[mask])return false;
    visited[mask]=1;
    std::vector<Option> options;
    for(size_t k=0;k<groups.size();++k)if(!(mask&(1u<<k))) {
      work+=g.n;if(work>8000000){exhausted=true;return false;}
      Option x{1u<<k,live,live,{},users};bool fit=true;
      for(int i:closure[k])if(!(cover[i]&mask)) {
        work+=1+g.in[i].size();if(work>8000000){exhausted=true;return false;}
        const auto& v=g.v[i];if(!memory_fits(h.memory_limit,x.live,v.workspace_memory,v.output_memory)){fit=false;break;}
        x.peak=std::max(x.peak,x.live+v.workspace_memory+v.output_memory);
        x.live+=v.output_memory;x.order.push_back(i);
        for(int p:g.in[i])if(!--x.users[p])x.live-=g.v[p].output_memory;
      }
      if(fit)options.push_back(std::move(x));
    }
    std::stable_sort(options.begin(),options.end(),[](const Option& a,const Option& b){return std::tie(a.live,a.peak)<std::tie(b.live,b.peak);});
    for(const auto& x:options) {
      size_t old=result.size();result.insert(result.end(),x.order.begin(),x.order.end());
      if(search(mask|x.bit,x.live,x.users))return true;
      result.resize(old);if(exhausted)return false;
    }
    return false;
  };
  if(!search(0,0,initial))return {};
  return result;
}

// For small memory-hard graphs, subset DP proves the minimum SERIAL peak.
// It is only invoked after static serial priorities fail the memory gate;
// parallel optimality is deliberately not claimed.
std::vector<int> serial_oracle(const Graph& g) {
  if(g.n>18)return {};
  const unsigned states=1u<<g.n;const I infinity=std::numeric_limits<I>::max();
  std::vector<unsigned> pred(g.n),succ(g.n);
  for(int i=0;i<g.n;++i){for(int p:g.in[i])pred[i]|=1u<<p;for(int c:g.out[i])succ[i]|=1u<<c;}
  std::vector<I> peak(states,infinity);std::vector<int> last(states,-1);peak[0]=0;
  for(unsigned mask=0;mask<states;++mask)if(mask==0 || last[mask]>=0) {
    I live=0;bool fits=true;for(int i=0;i<g.n;++i)if((mask&(1u<<i)) && (!succ[i] || (succ[i]&~mask)))if(!checked_add(live,g.v[i].output_memory,live)){fits=false;break;}if(!fits)continue;
    for(int i=0;i<g.n;++i)if(!(mask&(1u<<i)) && !(pred[i]&~mask)) {
      if(!memory_fits(infinity,live,g.v[i].workspace_memory,g.v[i].output_memory))continue;
      unsigned next=mask|(1u<<i);I cost=std::max(peak[mask],live+g.v[i].workspace_memory+g.v[i].output_memory);
      if(last[next]<0 || cost<peak[next]){peak[next]=cost;last[next]=i;}
    }
  }
  if(states>1 && last[states-1]<0)return {};
  std::vector<int> order;for(unsigned mask=states-1;mask;){int i=last[mask];order.push_back(i);mask^=1u<<i;}
  std::reverse(order.begin(),order.end());return order;
}


// Recognize a complete nested fork/join component. Every fork keeps its own
// original direct edge to the join; a branch has no boundary-crossing users.
// Optimize ONLY the two contiguous branch orders, not arbitrary interleavings
// or dominant profiles. A final evaluator remains the feasibility authority.
std::vector<int> strict_fork_join_order(const Graph& g) {
  if(g.n>4096)return {};
  std::vector<int> roots;for(int i=0;i<g.n;++i)if(g.in[i].empty())roots.push_back(i);
  if(roots.size()!=1)return {};
  struct Block {bool valid=false;int terminal=-1;I peak=0,output=0;};
  std::vector<unsigned char> visited(g.n);
  std::vector<int> first_root(g.n,-1),second_root(g.n,-1),join_node(g.n,-1);
  std::function<Block(int,int,int,int)> parse;
  parse=[&](int root,int parent,int consumer,int depth)->Block {
    if(depth>512 || visited[root])return {};
    if(parent<0 ? !g.in[root].empty() : (g.in[root].size()!=1 || g.in[root][0]!=parent))return {};
    visited[root]=1;
    if(g.out[root].size()<=1) {
      if(consumer<0 ? !g.out[root].empty() : (g.out[root].size()!=1 || g.out[root][0]!=consumer))return {};
      return {true,root,positive_add(g.v[root].workspace_memory,g.v[root].output_memory),g.v[root].output_memory};
    }
    if(g.out[root].size()!=3)return {};
    int join=-1;std::vector<int> children;
    for(int c:g.out[root]) {
      if(g.in[c].size()==3) {if(join>=0)return {};join=c;}
      else children.push_back(c);
    }
    if(join<0 || children.size()!=2 || visited[join])return {};
    if(consumer<0 ? !g.out[join].empty() : (g.out[join].size()!=1 || g.out[join][0]!=consumer))return {};
    auto a=parse(children[0],root,join,depth+1);if(!a.valid)return {};
    auto b=parse(children[1],root,join,depth+1);if(!b.valid)return {};
    std::vector<int> actual=g.in[join],expected{root,a.terminal,b.terminal};
    std::sort(actual.begin(),actual.end());std::sort(expected.begin(),expected.end());if(actual!=expected)return {};
    visited[join]=1;
    I fork_output=g.v[root].output_memory;
    auto peak_order=[&](const Block& first,const Block& second) {
      I p=positive_add(g.v[root].workspace_memory,fork_output);
      p=std::max(p,positive_add(fork_output,first.peak));
      p=std::max(p,positive_add(fork_output,positive_add(first.output,second.peak)));
      I at_join=positive_add(fork_output,positive_add(a.output,b.output));
      at_join=positive_add(at_join,positive_add(g.v[join].workspace_memory,g.v[join].output_memory));
      return std::max(p,at_join);
    };
    I ab=peak_order(a,b),ba=peak_order(b,a);
    first_root[root]=children[0];second_root[root]=children[1];join_node[root]=join;
    if(ba<ab || (ba==ab && g.v[children[1]].id<g.v[children[0]].id))std::swap(first_root[root],second_root[root]);
    return {true,join,std::min(ab,ba),g.v[join].output_memory};
  };
  auto result=parse(roots[0],-1,-1,0);
  if(!result.valid || std::count(visited.begin(),visited.end(),static_cast<unsigned char>(1))!=g.n)return {};
  // Emit the selected profile in one explicit traversal. No subtree order
  // vector is repeatedly copied through its ancestors. Negative markers are
  // complements of valid node indices and emit only the original join node.
  std::vector<int> order,stack{roots[0]};order.reserve(g.n);
  while(!stack.empty()) {
    int i=stack.back();stack.pop_back();
    if(i<0){order.push_back(~i);continue;}
    order.push_back(i);
    if(join_node[i]>=0) {stack.push_back(~join_node[i]);stack.push_back(second_root[i]);stack.push_back(first_root[i]);}
  }
  if(order.size()!=static_cast<size_t>(g.n))return {};
  return order;
}

struct SerialFrontierResult {
  std::vector<int> order;
  I work=0;
  size_t failed_states=0;
  bool exhausted=false;
};
// Fixed-budget SERIAL feasibility search. A completed set uniquely determines
// its live outputs. Only fully explored failures enter the transposition set.
// Ready tasks with nonpositive output impact may be advanced safely: their
// released parents have no remaining user except this task. This preserves
// feasibility at the given capacity, not the minimum achievable peak.
SerialFrontierResult serial_frontier_search(const HardwareInfo& h,const Graph& g,I work_limit=8000000,bool paired=false,bool greedy=false,bool inside_normalize=false) {
  SerialFrontierResult result;
  if(g.n>768)return result;
  std::vector<int> degree(g.n),users(g.n),order;
  std::vector<unsigned char> done(g.n);
  std::vector<unsigned long long> mask((g.n+63)/64);
  std::set<int> ready;
  std::set<std::vector<unsigned long long>> failed;
  // If i is an ancestor of a direct user of p, a completed p output cannot
  // be released before i completes. Track this unavoidable future overlap.
  // This is stronger than counting only the direct inputs of i, and does not
  // add edges or change the actual release recurrence.
  const size_t words=(g.n+63)/64;
  std::vector<std::vector<unsigned long long>> ancestors(g.n,std::vector<unsigned long long>(words));
  for(int i:g.topo) {
    ancestors[i][i/64]|=1ull<<(i%64);
    for(int p:g.in[i])for(size_t k=0;k<words;++k)ancestors[i][k]|=ancestors[p][k];
  }
  std::vector<std::vector<int>> retained_targets(g.n);
  for(int p=0;p<g.n;++p)if(g.v[p].output_memory) {
    std::vector<unsigned long long> bits(words);
    for(int c:g.out[p])for(size_t k=0;k<words;++k)bits[k]|=ancestors[c][k];
    for(int i=0;i<g.n;++i)if(bits[i/64]&(1ull<<(i%64)))retained_targets[p].push_back(i);
  }
  std::vector<I> pinned(g.n);
  // Search useful completions before individual allocations. Every original
  // single-node branch remains below, so macros are an ordering accelerator,
  // not a claim that one fixed ancestor traversal covers all legal schedules.
  std::vector<std::vector<int>> closures;
  std::vector<unsigned char> target_node(g.n);
  for(int target=0;target<g.n;++target) {
    I inputs=0;for(int p:g.in[target])inputs=positive_add(inputs,g.v[p].output_memory);
    if(inputs<=g.v[target].output_memory)continue;
    target_node[target]=1;
    std::vector<int> closure;
    for(int i:g.topo)if(ancestors[target][i/64]&(1ull<<(i%64)))closure.push_back(i);
    closures.push_back(std::move(closure));
  }
  if(paired) {
    // A producer's actual co-consumers give pair affinity; no inferred data
    // dependency or output lifetime is introduced. Limit only the optional
    // macro accelerator; every original singleton branch still remains.
    std::unordered_map<int,I> affinity;
    for(int p=0;p<g.n;++p)if(g.v[p].output_memory) {
      std::vector<int> targets;for(int c:g.out[p])if(target_node[c])targets.push_back(c);
      I weight=priority_mul_div(g.v[p].output_memory,1024,static_cast<uint64_t>(std::max<size_t>(1,g.out[p].size())));
      for(size_t a=0;a<targets.size();++a)for(size_t b=a+1;b<targets.size();++b) {
        int i=std::min(targets[a],targets[b]),j=std::max(targets[a],targets[b]);affinity[i*g.n+j]=positive_add(affinity[i*g.n+j],weight);
      }
    }
    std::vector<std::pair<I,int>> pairs;for(const auto& x:affinity)pairs.emplace_back(x.second,x.first);
    std::sort(pairs.begin(),pairs.end(),[](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:a.second<b.second;});
    if(pairs.size()>48)pairs.resize(48);
    for(const auto& pair:pairs) {
      int a=pair.second/g.n,b=pair.second%g.n;std::vector<int> closure;
      for(int i:g.topo)if((ancestors[a][i/64]|ancestors[b][i/64])&(1ull<<(i%64)))closure.push_back(i);
      closures.push_back(std::move(closure));
    }
  }
  I live=0,sink_live=0;
  for(int i=0;i<g.n;++i) {
    degree[i]=static_cast<int>(g.in[i].size());users[i]=static_cast<int>(g.out[i].size());
    if(!degree[i])ready.insert(i);
  }
  auto charge=[&](I amount) {
    result.work=positive_add(result.work,amount);
    if(result.work>work_limit){result.exhausted=true;return false;}return true;
  };
  auto impact=[&](int i) {
    I released=0;for(int p:g.in[i])if(users[p]==1)released=positive_add(released,g.v[p].output_memory);
    return g.v[i].output_memory-released;
  };
  auto apply=[&](int i) {
    charge(static_cast<I>(retained_targets[i].size()+g.out[i].size()));
    for(int target:retained_targets[i])if(target!=i && !done[target])pinned[target]+=g.v[i].output_memory;
    ready.erase(i);done[i]=1;mask[i/64]|=1ull<<(i%64);order.push_back(i);
    live+=g.v[i].output_memory;if(g.out[i].empty())sink_live+=g.v[i].output_memory;
    for(int p:g.in[i])if(!--users[p])live-=g.v[p].output_memory;
    for(int c:g.out[i])if(!--degree[c])ready.insert(c);
  };
  auto undo=[&](int i) {
    for(int target:retained_targets[i])if(target!=i && !done[target])pinned[target]-=g.v[i].output_memory;
    for(int c:g.out[i]){if(!degree[c])ready.erase(c);++degree[c];}
    for(int p:g.in[i]){if(!users[p])live+=g.v[p].output_memory;++users[p];}
    live-=g.v[i].output_memory;if(g.out[i].empty())sink_live-=g.v[i].output_memory;
    order.pop_back();done[i]=0;mask[i/64]&=~(1ull<<(i%64));ready.insert(i);
  };
  auto fits=[&](int i){return memory_fits(h.memory_limit,live,g.v[i].workspace_memory,g.v[i].output_memory);};
  std::function<bool()> search;
  search=[&]() {
    const size_t prefix=order.size();
    auto rollback=[&](){while(order.size()>prefix)undo(order.back());};
    if(result.exhausted)return false;
    // Each safe advance has its own exchange argument; normalization need not
    // be confluent. Determinism only selects one feasibility-preserving order.
    while(true) {
      int safe=-1;
      for(int i:ready) {
        if(!charge(1+static_cast<I>(g.in[i].size()))){rollback();return false;}
        if(fits(i) && impact(i)<=0){safe=i;break;}
      }
      if(safe<0)break;
      apply(safe);
      if(result.exhausted){rollback();return false;}
    }
    if(order.size()==static_cast<size_t>(g.n)){result.order=order;return true;}
    if(failed.find(mask)!=failed.end()){rollback();return false;}
    bool impossible=false;
    for(int i=0;i<g.n;++i)if(!done[i]) {
      if(!charge(1+static_cast<I>(g.in[i].size()))){rollback();return false;}
      I left=h.memory_limit;auto take=[&](I amount){if(amount>left)return false;left-=amount;return true;};
      bool fits=take(sink_live) && take(pinned[i]) && take(g.v[i].workspace_memory) && take(g.v[i].output_memory);
      for(int p:g.in[i])if(!done[p] && !take(g.v[p].output_memory))fits=false;
      if(!fits){impossible=true;break;}
    }
    std::vector<int> options;
    if(!impossible)for(int i:ready) {
      if(!charge(1+static_cast<I>(g.in[i].size()))){rollback();return false;}
      if(fits(i))options.push_back(i);
    }
    struct Macro {std::vector<int> nodes;I final_live,peak;};
    std::vector<Macro> macros;
    std::set<std::vector<unsigned long long>> seen_macro;
    if(!impossible)for(const auto& closure:closures) {
      std::vector<unsigned long long> pending(words);size_t pending_count=0;
      for(int i:closure)if(!done[i]){pending[i/64]|=1ull<<(i%64);++pending_count;}
      if(pending_count<2 || !seen_macro.insert(pending).second)continue;
      const size_t begin=order.size();I peak=live;bool fit=true;
      for(int i:closure) {
        // A safe ready consumer outside this closure may free an opened
        // producer before the next allocation. Record every actual action
        // for exact rollback, without adding dependencies or release credit.
        if(inside_normalize)while(true) {
          int safe=-1;
          for(int j:ready) {
            if(!charge(1+static_cast<I>(g.in[j].size()))){fit=false;break;}
            if(fits(j) && impact(j)<=0){safe=j;break;}
          }
          if(!fit || safe<0)break;
          peak=std::max(peak,live+g.v[safe].workspace_memory+g.v[safe].output_memory);
          apply(safe);
          if(result.exhausted){fit=false;break;}
        }
        if(!fit)break;
        if(done[i])continue;
        if(!charge(1+static_cast<I>(g.in[i].size()))){fit=false;break;}
        if(!fits(i)){fit=false;break;}
        peak=std::max(peak,live+g.v[i].workspace_memory+g.v[i].output_memory);apply(i);
        if(result.exhausted){fit=false;break;}
      }
      if(fit && order.size()>begin+1) {
        // In greedy mode only the first stable-sorted macro can be used;
        // streaming the minimum avoids storing every candidate at each depth.
        if(!greedy)macros.push_back({std::vector<int>(order.begin()+begin,order.end()),live,peak});
        else if(macros.empty() || std::tie(live,peak)<std::tie(macros[0].final_live,macros[0].peak)) {
          Macro best{std::vector<int>(order.begin()+begin,order.end()),live,peak};
          if(macros.empty())macros.push_back(std::move(best));else macros[0]=std::move(best);
        }
      }
      while(order.size()>begin)undo(order.back());
      if(result.exhausted){rollback();return false;}
    }
    std::stable_sort(macros.begin(),macros.end(),[](const Macro& a,const Macro& b) {
      return std::tie(a.final_live,a.peak)<std::tie(b.final_live,b.peak);
    });
    for(const auto& macro:macros) {
      for(int i:macro.nodes)apply(i);
      if(search())return true;
      for(size_t k=macro.nodes.size();k>0;--k)undo(macro.nodes[k-1]);
      if(result.exhausted){rollback();return false;}
      if(greedy){result.exhausted=true;rollback();return false;}
    }
    std::sort(options.begin(),options.end(),[&](int a,int b) {
      I ia=impact(a),ib=impact(b);
      if(ia!=ib)return ia<ib;
      if(g.out[a].size()!=g.out[b].size())return g.out[a].size()>g.out[b].size();
      return g.v[a].id<g.v[b].id;
    });
    for(int i:options) {
      apply(i);if(search())return true;undo(i);
      if(result.exhausted){rollback();return false;}
      if(greedy){result.exhausted=true;rollback();return false;}
    }
    // Full bitsets avoid hash aliasing. A hard state-memory bound also stops
    // search explicitly; interrupted states are never certified as failures.
    if(failed.size()>=100000){result.exhausted=true;rollback();return false;}
    failed.insert(mask);result.failed_states=failed.size();rollback();return false;
  };
  search();return result;
}

// Sparse dependency neighborhoods can hide a useful memory traversal when
// IDs and records are shuffled. Low-degree undirected BFS gives a locality
// permutation; Kahn scheduling restores all directed precedence constraints.
std::vector<std::vector<int>> locality_orders(const Graph& g) {
  std::vector<std::vector<int>> adjacent(g.n);
  for(int i=0;i<g.n;++i){adjacent[i]=g.in[i];adjacent[i].insert(adjacent[i].end(),g.out[i].begin(),g.out[i].end());
    std::sort(adjacent[i].begin(),adjacent[i].end(),[&](int a,int b){size_t da=g.in[a].size()+g.out[a].size(),db=g.in[b].size()+g.out[b].size();return da!=db?da<db:g.v[a].id<g.v[b].id;});}
  std::vector<bool> visited(g.n);std::vector<int> permutation,marks(g.n),distance(g.n);int epoch=0;
  for(int component=0;component<g.n;++component)if(!visited[component]) {
    int root=component;
    auto bfs=[&](int source){std::vector<int> order{source};++epoch;marks[source]=epoch;distance[source]=0;
      for(size_t k=0;k<order.size();++k)for(int j:adjacent[order[k]])if(marks[j]!=epoch){marks[j]=epoch;distance[j]=distance[order[k]]+1;order.push_back(j);}
      return order;};
    for(int pass=0;pass<3;++pass){auto traversal=bfs(root);int next=root;
      for(int i:traversal)if(distance[i]>distance[next] ||
        (distance[i]==distance[next] && adjacent[i].size()<adjacent[next].size()))next=i;
      root=next;}
    auto traversal=bfs(root);for(int i:traversal){visited[i]=true;permutation.push_back(i);}
  }
  std::vector<std::vector<int>> result;
  for(bool reverse:{false,true}) {
    std::vector<int> position(g.n),degree(g.n),order;
    for(int k=0;k<g.n;++k)position[permutation[k]]=reverse?g.n-k:k;
    auto less=[&](int a,int b){return position[a]>position[b];};std::priority_queue<int,std::vector<int>,decltype(less)> ready(less);
    for(int i=0;i<g.n;++i){degree[i]=static_cast<int>(g.in[i].size());if(!degree[i])ready.push(i);}
    while(!ready.empty()){int i=ready.top();ready.pop();order.push_back(i);for(int j:g.out[i])if(!--degree[j])ready.push(j);}
    result.push_back(std::move(order));
  }
  return result;
}

// Complete the prerequisites of low-output targets before opening unrelated
// branches. Iterative DFS avoids stack overflow and never changes data edges.
// Unlike undirected BFS this can retain locality across shared relay roots.
std::vector<int> completion_order(const Graph& g,int mode) {
  std::vector<int> targets=g.topo;
  std::sort(targets.begin(),targets.end(),[&](int a,int b){
    I ca=g.v[a].output_memory,cb=g.v[b].output_memory;
    if(mode==1){ca=positive_add(ca,g.v[a].workspace_memory);cb=positive_add(cb,g.v[b].workspace_memory);}
    if(ca!=cb)return ca<cb;
    if(g.out[a].size()!=g.out[b].size())return g.out[a].size()<g.out[b].size();
    return g.v[a].id<g.v[b].id;
  });
  std::vector<bool> done(g.n);std::vector<int> result;result.reserve(g.n);
  std::vector<std::pair<int,size_t>> stack;
  for(int target:targets)if(!done[target]) {
    stack.emplace_back(target,0);
    while(!stack.empty()) {
      auto& frame=stack.back();int i=frame.first;
      if(done[i]){stack.pop_back();continue;}
      while(frame.second<g.in[i].size() && done[g.in[i][frame.second]])++frame.second;
      if(frame.second<g.in[i].size()){int p=g.in[i][frame.second++];stack.emplace_back(p,0);}
      else {done[i]=true;result.push_back(i);stack.pop_back();}
    }
  }
  return result;
}

SchedulePlan assemble(const Graph& g,const std::vector<int>& order,const std::vector<int>& assignment,int streams,int guards,
                      const std::vector<std::pair<int,int>>& extra={}) {
  SchedulePlan plan; plan.streams.resize(streams);
  std::vector<std::vector<int>> before=g.in;
  for(auto edge:extra)before[edge.second].push_back(edge.first);
  // Guard edges affect time only: original Graph::in/out still determines output lifetime.
  if(guards) for(size_t k=1;k<order.size();++k) {
    int p=order[k-1],i=order[k];
    if(assignment[p]!=assignment[i] && (guards==1 || (g.v[p].workspace_memory>0 || g.v[i].workspace_memory>0))) before[i].push_back(p);
  }
  std::vector<int> event(g.n,-1); int next=0;
  for(int i:order) for(int p:before[i]) if(assignment[p]!=assignment[i] && event[p]<0) event[p]=next++;
  for(int i:order) {
    StreamTask t{g.v[i].id,{},event[i]};
    for(int p:before[i]) if(assignment[p]!=assignment[i]) t.wait_before.push_back(event[p]);
    std::sort(t.wait_before.begin(),t.wait_before.end());
    t.wait_before.erase(std::unique(t.wait_before.begin(),t.wait_before.end()),t.wait_before.end());
    plan.streams[assignment[i]].tasks.push_back(std::move(t));
  }
  plan.streams.erase(std::remove_if(plan.streams.begin(),plan.streams.end(),[](const auto& s){return s.tasks.empty();}),plan.streams.end());
  return plan;
}

std::vector<int> assign(const HardwareInfo& h,const Graph& g,const std::vector<int>& order,int streams,int affinity) {
  std::vector<I> available(streams),finish(g.n);
  std::vector<int> result(g.n,-1),last_type(streams,-1);
  std::vector<int> parent_count,touched;std::vector<I> parent_finish;
  for(int i:order) {
    int best=0; I cost=std::numeric_limits<I>::max();
    bool grouped=g.in[i].size()>=8 && streams>=4 && static_cast<I>(g.in[i].size())*streams>=64;I first=0,second=0;int first_owner=-1;
    if(grouped)for(int p:g.in[i])if(result[p]<0){grouped=false;break;}
    if(grouped) {
      if(parent_count.empty()){parent_count.resize(streams);parent_finish.resize(streams);}
      for(int p:g.in[i]) {int owner=result[p];if(!parent_count[owner]++)touched.push_back(owner);parent_finish[owner]=std::max(parent_finish[owner],finish[p]);}
      for(int owner:touched) {I value=parent_finish[owner];if(value>first){second=first;first=value;first_owner=owner;}else second=std::max(second,value);}
    }
    for(int s=0;s<streams;++s) {
      I start=available[s],waits=0;
      if(grouped) {
        waits=static_cast<I>(g.in[i].size())-parent_count[s];start=std::max(start,parent_finish[s]);
        if(waits)start=std::max(start,positive_add((s==first_owner?second:first),h.event_record_time));
      } else for(int p:g.in[i]) {start=std::max(start,positive_add(finish[p],(result[p]!=s?h.event_record_time:0)));if(result[p]!=s)++waits;}
      I end=positive_add(positive_add(start,positive_mul(waits,h.event_wait_time)),g.v[i].exec_time);
      if(affinity && last_type[s]>=0 && last_type[s]!=static_cast<int>(g.v[i].core_type)) end=positive_add(end,positive_add(h.event_record_time,h.event_wait_time));
      if(end<cost) {cost=end;best=s;}
    }
    for(int owner:touched){parent_count[owner]=0;parent_finish[owner]=0;}touched.clear();
    result[i]=best;available[best]=finish[i]=cost;last_type[best]=static_cast<int>(g.v[i].core_type);
  }
  return result;
}

struct ResourceCandidate {std::vector<int> order,assignment;std::vector<std::pair<int,int>> guards;};
// Construct a feasible-oriented list schedule. Wait reservations are charged
// early, conservatively holding cores and memory until computation ends.
// Frontier guards can preserve release decisions across real stream queues;
// only the independent exact evaluator decides whether the final plan is legal.
ResourceCandidate resource_list(const HardwareInfo& h,const Graph& g,int streams,int mode,bool guard) {
  ResourceCandidate result;result.assignment.assign(g.n,-1);
  std::vector<int> degree(g.n),users(g.n),frontier(streams,-1),active(streams,-1),ready;
  std::vector<I> finish(g.n),flow_ready(streams);std::vector<bool> done(g.n);
  for(int i=0;i<g.n;++i){degree[i]=static_cast<int>(g.in[i].size());users[i]=static_cast<int>(g.out[i].size());if(!degree[i])ready.push_back(i);}
  int cores[2]={0,0},completed=0;I memory=0,clock=0;
  while(completed<g.n) {
    for(int s=0;s<streams;++s)if(active[s]>=0 && finish[active[s]]==clock) {
      int i=active[s];active[s]=-1;done[i]=true;frontier[s]=i;++completed;
      cores[static_cast<int>(g.v[i].core_type)]-=g.v[i].core_num;memory-=g.v[i].workspace_memory;
      for(int p:g.in[i])if(!--users[p])memory-=g.v[p].output_memory;
      for(int j:g.out[i])if(!--degree[j])ready.push_back(j);
    }
    for(int s=0;s<streams;++s)if(active[s]<0 && flow_ready[s]<=clock) {
      int chosen=-1;std::tuple<I,I,I> best;
      for(size_t k=0;k<ready.size();++k) {
        int i=ready[k];const auto& v=g.v[i];int type=static_cast<int>(v.core_type),cap=type==0?h.aic_core_num:h.aiv_core_num;
        if(v.core_num>cap-cores[type] || !memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory))continue;
        I release=0;for(int p:g.in[i])if(users[p]==1)release=positive_add(release,g.v[p].output_memory);
        I local=0;for(int p:g.in[i])if(result.assignment[p]==s)local=positive_add(local,positive_add(h.event_wait_time,h.event_record_time));
        std::tuple<I,I,I> score=mode==0?std::make_tuple(positive_add(g.rank[i],local),release-v.output_memory,-v.workspace_memory):
                                                   std::make_tuple(release-v.output_memory,positive_add(g.rank[i],local),-v.workspace_memory);
        if(mode==2)score=std::make_tuple(scaled_priority(positive_add(g.rank[i],local),cap,v.core_num),release-v.output_memory,-v.exec_time*v.core_num);
        if(mode==3)score=std::make_tuple(positive_add(g.rank[i]-v.exec_time,local),release-v.output_memory,-v.exec_time*v.core_num);
        if(chosen<0 || score>best){chosen=static_cast<int>(k);best=score;}
      }
      if(chosen<0)continue;
      int i=ready[chosen];ready[chosen]=ready.back();ready.pop_back();const auto& v=g.v[i];
      std::vector<int> waits;for(int p:g.in[i])if(result.assignment[p]!=s)waits.push_back(p);
      if(guard)for(int other=0;other<streams;++other)if(other!=s && frontier[other]>=0) {
        int p=frontier[other];result.guards.emplace_back(p,i);waits.push_back(p);
      }
      std::sort(waits.begin(),waits.end());waits.erase(std::unique(waits.begin(),waits.end()),waits.end());
      I start=clock;for(int p:waits)start=std::max(start,positive_add(finish[p],h.event_record_time));
      finish[i]=positive_add(positive_add(start,positive_mul(static_cast<I>(waits.size()),h.event_wait_time)),v.exec_time);
      flow_ready[s]=positive_add(finish[i],h.event_record_time);active[s]=i;result.assignment[i]=s;result.order.push_back(i);
      cores[static_cast<int>(v.core_type)]+=v.core_num;memory+=v.workspace_memory+v.output_memory;
    }
    if(completed==g.n)break;
    I next=std::numeric_limits<I>::max();
    bool timer=false;for(int s=0;s<streams;++s){I at=active[s]>=0?finish[active[s]]:flow_ready[s];if(at>clock && (!timer || at<next)){next=at;timer=true;}}
    if(!timer){result.order.clear();return result;}
    clock=next;
  }
  return result;
}
// A constructive variant with pending Wait and active Compute kept separate.
// It allocates resources only when Compute actually starts. Record is still
// conservatively charged at all producer ends before event usage is known;
// emitted plans therefore remain candidates, filtered by the exact evaluator.
ResourceCandidate resource_delayed(const HardwareInfo& h,const Graph& g,int streams,int mode,bool guard) {
  ResourceCandidate result;result.assignment.assign(g.n,-1);
  std::vector<int> degree(g.n),users(g.n),frontier(streams,-1),active(streams,-1),ready;
  std::vector<unsigned char> computing(streams);std::vector<I> finish(g.n),flow_ready(streams),due(streams);
  for(int i=0;i<g.n;++i){degree[i]=static_cast<int>(g.in[i].size());users[i]=static_cast<int>(g.out[i].size());if(!degree[i])ready.push_back(i);}
  int cores[2]={0,0},completed=0;I memory=0,clock=0;
  bool numeric_failure=false;
  auto start_compute=[&](int s) {
    int i=active[s];const auto& v=g.v[i];int type=static_cast<int>(v.core_type),cap=type==0?h.aic_core_num:h.aiv_core_num;
    if(v.core_num>cap-cores[type] || !memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory))return;
    cores[type]+=v.core_num;memory+=v.workspace_memory+v.output_memory;computing[s]=1;if(!checked_add(clock,v.exec_time,due[s])){numeric_failure=true;return;}finish[i]=due[s];
  };
  while(completed<g.n) {
    for(int s=0;s<streams;++s)if(active[s]>=0 && computing[s] && due[s]==clock) {
      int i=active[s];active[s]=-1;computing[s]=0;frontier[s]=i;++completed;flow_ready[s]=positive_add(clock,h.event_record_time);
      cores[static_cast<int>(g.v[i].core_type)]-=g.v[i].core_num;memory-=g.v[i].workspace_memory;
      for(int p:g.in[i])if(!--users[p])memory-=g.v[p].output_memory;
      for(int c:g.out[i])if(!--degree[c])ready.push_back(c);
    }
    for(int s=0;s<streams;++s) {
      if(active[s]>=0){if(!computing[s] && due[s]<=clock)start_compute(s);continue;}
      if(flow_ready[s]>clock)continue;
      int chosen=-1;std::tuple<I,I,I> best;
      for(size_t k=0;k<ready.size();++k) {
        int i=ready[k];const auto& v=g.v[i];int type=static_cast<int>(v.core_type),cap=type==0?h.aic_core_num:h.aiv_core_num;
        if(!memory_fits(h.memory_limit,memory,v.workspace_memory,v.output_memory) || v.core_num>cap-cores[type]) {
          bool pending=false;
          for(int p:g.in[i])if(result.assignment[p]!=s && (positive_add(finish[p],h.event_record_time)>clock || h.event_wait_time))pending=true;
          if(guard)for(int other=0;other<streams;++other)if(other!=s && frontier[other]>=0 && (positive_add(finish[frontier[other]],h.event_record_time)>clock || h.event_wait_time))pending=true;
          if(!pending)continue;
        }
        I release=0,local=0;for(int p:g.in[i]){if(users[p]==1)release=positive_add(release,g.v[p].output_memory);if(result.assignment[p]==s)local=positive_add(local,positive_add(h.event_record_time,h.event_wait_time));}
        std::tuple<I,I,I> score=mode==1?std::make_tuple(release-v.output_memory,positive_add(g.rank[i],local),-v.workspace_memory):
          mode==2?std::make_tuple(scaled_priority(positive_add(g.rank[i],local),cap,v.core_num),release-v.output_memory,-v.exec_time*v.core_num):std::make_tuple(positive_add(g.rank[i],local),release-v.output_memory,-v.workspace_memory);
        if(chosen<0 || score>best){chosen=static_cast<int>(k);best=score;}
      }
      if(chosen<0)continue;
      int i=ready[chosen];ready[chosen]=ready.back();ready.pop_back();std::vector<int> waits;
      for(int p:g.in[i])if(result.assignment[p]!=s)waits.push_back(p);
      if(guard)for(int other=0;other<streams;++other)if(other!=s && frontier[other]>=0){int p=frontier[other];waits.push_back(p);result.guards.emplace_back(p,i);}
      std::sort(waits.begin(),waits.end());waits.erase(std::unique(waits.begin(),waits.end()),waits.end());
      due[s]=clock;for(int p:waits)due[s]=std::max(due[s],positive_add(finish[p],h.event_record_time));
      due[s]=positive_add(due[s],positive_mul(static_cast<I>(waits.size()),h.event_wait_time));active[s]=i;result.assignment[i]=s;result.order.push_back(i);
      if(due[s]==clock)start_compute(s);
    }
    if(completed==g.n)break;
    I next=std::numeric_limits<I>::max();
    bool timer=false;for(int s=0;s<streams;++s){I at=active[s]>=0?due[s]:flow_ready[s];if(at>clock && (!timer || at<next)){next=at;timer=true;}}
    if(!timer || numeric_failure){result.order.clear();return result;}
    clock=next;
  }
  return result;
}
} // namespace aicore_detail

// Optional telemetry does not change the official interface.
int64_t AicoreLastMetric(int key) {
  const auto& m=aicore_detail::metrics;
  switch(key) {case 0:return m.candidates;case 1:return m.feasible;case 2:return m.time;case 3:return m.peak;case 4:return m.micros;case 5:return m.duplicates;case 6:return m.attempts;case 7:return m.beam_expansions;case 8:return m.beam_width;case 9:return m.optimal_certificate;case 10:return m.time_lower_bound;case 11:return m.memory_lower_bound;default:return -1;}
}

int64_t AicoreEvaluateMetric(const HardwareInfo& hw,const std::vector<OperatorNode>& nodes,
                            const SchedulePlan& plan,int key) {
  try {
    aicore_detail::Graph g(hw,nodes);auto e=aicore_detail::evaluate(hw,g,plan);
    if(key==0)return e.valid?1:0;
    if(!e.valid)return -1;
    return key==1?e.time:(key==2?e.peak:-1);
  } catch(const std::exception&) {return key==0?0:-1;}
}

SchedulePlan ScheduleCvGraph(const HardwareInfo& hw,const std::vector<OperatorNode>& nodes,int64_t deadline_us) {
  using namespace aicore_detail;
  metrics={};auto started=std::chrono::steady_clock::now();
  Graph graph(hw,nodes);
  if(deadline_us<0) throw std::invalid_argument("Negative deadline");
  if(nodes.empty()) {metrics.time=metrics.peak=0;return {};}
  I terminal_left=hw.memory_limit;
  for(int i=0;i<graph.n;++i) {
    I left=hw.memory_limit;auto take=[&](I amount){if(amount>left)return false;left-=amount;return true;};
    bool fits=take(nodes[i].workspace_memory) && take(nodes[i].output_memory);
    for(int p:graph.in[i])if(!take(nodes[p].output_memory))fits=false;
    if(!fits)throw std::runtime_error("Necessary direct-input memory gate exceeds capacity");
    if(graph.out[i].empty()){if(nodes[i].output_memory>terminal_left)throw std::runtime_error("Final output memory exceeds capacity");terminal_left-=nodes[i].output_memory;}
  }
  const int largest=std::min({hw.stream_num,graph.n,256});
  std::set<int> counts{1,largest};for(int s:{2,3,4,8,16,32,64,128})if(s<=largest)counts.insert(s);
  const int modes=graph.n>2048?4:6;
  const int base_budget=graph.n>2048?36:(graph.n>512?96:220);int budget=base_budget;
  bool found=false;Evaluation best;SchedulePlan answer;
  auto bounds=lower_bounds(hw,graph);bool overlap_checked=false;
  metrics.time_lower_bound=bounds.time;metrics.memory_lower_bound=bounds.memory;
  auto certified=[&](){
    if(!found || best.time!=bounds.time)return false;
    if(!overlap_checked){bounds.memory=forced_overlap_bound(graph,bounds.time,bounds.memory);overlap_checked=true;metrics.memory_lower_bound=bounds.memory;}
    return best.peak==bounds.memory;
  };
  auto finish=[&](){
    metrics.time=best.time;metrics.peak=best.peak;metrics.optimal_certificate=certified()?1:0;
    metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
    return answer;
  };
  std::vector<int> best_order,best_assignment;int best_streams=1;
  struct CachedCandidate {std::vector<int> key;Evaluation evaluation;};
  std::unordered_map<uint64_t,std::vector<CachedCandidate>> seen;
  auto consider=[&](const std::vector<int>& order,const std::vector<int>& assignment,int streams,int guards=0,
                    const std::vector<std::pair<int,int>>& extra=std::vector<std::pair<int,int>>{},bool serial=false)->Evaluation {
    if(order.size()!=static_cast<size_t>(graph.n) || metrics.candidates>=budget)return {};
    ++metrics.attempts;auto key=signature(graph,order,assignment,streams,guards,extra);uint64_t hash=1469598103934665603ULL;
    for(int x:key){hash^=static_cast<uint32_t>(x);hash*=1099511628211ULL;}
    auto& bucket=seen[hash];for(const auto& prior:bucket)if(prior.key==key){++metrics.duplicates;return prior.evaluation;}
    ++metrics.candidates;
    auto p=assemble(graph,order,assignment,streams,guards,extra);
    auto e=serial?serial_evaluate(hw,graph,order):evaluate(hw,graph,p,true);
    bucket.push_back({std::move(key),e});
    if(!e.valid || e.time>deadline_us)return e;
    ++metrics.feasible;
    if(!found || std::tie(e.time,e.peak)<std::tie(best.time,best.peak)) {
      found=true;best=e;answer=p;best_order=order;best_assignment=assignment;best_streams=streams;
    }
    return e;
  };
  std::vector<std::vector<int>> orders;
  bool serial_fits=false;
  for(int mode=0;mode<modes;++mode) {
    orders.push_back(ordering(graph,mode));const auto& order=orders.back();
    std::vector<int> assignment(graph.n,0);serial_fits=serial_fits || serial_evaluate(hw,graph,order).valid;
    consider(order,assignment,1,0,{},true);
    if(certified())return finish();
  }
  if(certified())return finish();
  if(!serial_fits && graph.n<=18) {
    auto order=serial_oracle(graph);std::vector<int> assignment(graph.n,0);
    consider(order,assignment,1,0,{},true);orders.push_back(std::move(order));
  }
  if(certified())return finish();
  for(const auto& order:orders) {
    if(metrics.candidates>=budget)break;
    for(int streams:counts) if(streams>1 && metrics.candidates<budget) for(int affinity=0;affinity<2 && metrics.candidates<budget;++affinity) {
      auto assignment=assign(hw,graph,order,streams,affinity);
      consider(order,assignment,streams);
      if(graph.n<=512) consider(order,assignment,streams,2);
    }
  }
  if(certified())return finish();
  if(found && graph.n<=512) {
    auto order=best_order;auto assignment=best_assignment;int streams=best_streams;
    for(size_t k=0;k<order.size() && metrics.candidates<budget;++k) {
      int i=order[k];
      for(int s=0;s<std::min(streams,4) && metrics.candidates<budget;++s) if(s!=assignment[i]) {
        auto moved=assignment;moved[i]=s;
        consider(order,moved,streams);
      }
      if(k+1<order.size()) {
        int j=order[k+1];
        if(std::find(graph.in[j].begin(),graph.in[j].end(),i)==graph.in[j].end()) {
          auto swapped=order;std::swap(swapped[k],swapped[k+1]);
          consider(swapped,assignment,streams);
        }
      }
    }
  }
  // Additional strategies receive a separate small budget, preserving the
  // original portfolio/local-search result instead of displacing candidates.
  if(!found || graph.n<=2048) {
    budget=metrics.candidates+32;
    for(int mode:{3,0,1,2}) {
      auto order=memory_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int streams:std::set<int>{std::min(largest,4),std::min(largest,16)})if(streams>1) {
        auto assignment=assign(hw,graph,order,streams,0);consider(order,assignment,streams);
        if(graph.n<=512)consider(order,assignment,streams,2);
      }
    }
    if(!found && graph.n<=10000) {
      budget=metrics.candidates+16;
      for(const auto& order:locality_orders(graph)) {
        std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
        for(int streams:std::set<int>{std::min(largest,4),std::min(largest,16)})if(streams>1) {
          auto assignment=assign(hw,graph,order,streams,0);consider(order,assignment,streams);
          consider(order,assignment,streams,2);
        }
      }
    }
    if(!found && graph.n<=10000) {
      budget=metrics.candidates+16;
      for(int mode=0;mode<2 && !found;++mode) {
        auto order=completion_order(graph,mode);std::vector<int> serial(graph.n,0);
        consider(order,serial,1,0,{},true);
        for(int s:std::set<int>{std::min(largest,4),std::min(largest,16)})if(s>1) {
          auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);
          consider(order,assignment,s,2);
        }
      }
    }
    if(!found && graph.n<=2048) {
      budget=metrics.candidates+8;
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,16)})for(int mode=0;mode<2;++mode)for(bool guard:{false,true}) {
        auto candidate=resource_list(hw,graph,s,mode,guard);if(static_cast<int>(candidate.order.size())!=graph.n)continue;
        consider(candidate.order,candidate.assignment,s,0,candidate.guards);
      }
    }
  }
  // Small cases are cheap enough to enumerate topological interleavings,
  // stream memberships and additional event edges completely for two flows.
  // Every acyclic explicit-direct-sync plan with <=2 flows has such an order;
  // canonical producer events cover arbitrary labels. Larger graphs retain
  // bounded heuristics; no global optimality claim is made for them.
  if(certified())return finish();
  if(graph.n<=6 && largest>=2) {
    // Five/six-node cases first exhaust membership/order combinations WITHOUT
    // added guards, then try one edge (and two edges for six nodes). These are
    // bounded searches, not complete arbitrary-event plan enumerations.
    budget=metrics.candidates+(graph.n<=4?30000:6000);
    for(int phase=0;phase<(graph.n>=5?(graph.n==6?3:2):1);++phase) {
    // Reserve a separate budget per phase for six-node cases, so guard
    // exploration cannot consume the no-extra-event membership/order phase.
    if(graph.n==6 && phase)budget=metrics.candidates+(phase==1?12000:8000);
    std::vector<int> order(graph.n);for(int i=0;i<graph.n;++i)order[i]=i;
    do {
      std::vector<int> position(graph.n);for(int k=0;k<graph.n;++k)position[order[k]]=k;
      bool topological=true;for(int i=0;i<graph.n;++i)for(int p:graph.in[i])if(position[p]>=position[i])topological=false;
      if(!topological)continue;
      for(unsigned code=0;code<(1u<<graph.n) && (graph.n!=6 || metrics.candidates<budget);++code) {
        std::vector<int> assignment(graph.n);for(int i=0;i<graph.n;++i)assignment[i]=static_cast<int>((code>>i)&1u);
        std::vector<std::pair<int,int>> optional;
        for(int a=0;a<graph.n;++a)for(int b=a+1;b<graph.n;++b){int p=order[a],i=order[b];if(assignment[p]!=assignment[i] && std::find(graph.in[i].begin(),graph.in[i].end(),p)==graph.in[i].end())optional.emplace_back(p,i);}
        if(graph.n>=5) {
          if(phase==0)consider(order,assignment,2);
          else {
            auto original=consider(order,assignment,2);
            // Without resource blocking, added waits cannot start any task
            // earlier with the same per-stream queue. Strictly slower base
            // plans therefore cannot beat best T. Equal T keeps peak search.
            if(original.valid && !original.contended && found && original.time>best.time)continue;
            if(phase==1)for(auto edge:optional)consider(order,assignment,2,0,{edge});
            else for(size_t a=0;a<optional.size() && metrics.candidates<budget;++a)for(size_t b=a+1;b<optional.size() && metrics.candidates<budget;++b)consider(order,assignment,2,0,{optional[a],optional[b]});
          }
        } else for(unsigned mask=0;mask<(1u<<optional.size());++mask) {
            std::vector<std::pair<int,int>> extra;for(size_t k=0;k<optional.size();++k)if(mask&(1u<<k))extra.push_back(optional[k]);
            consider(order,assignment,2,0,extra);
          }
      }
    }while((graph.n!=6 || metrics.candidates<budget) && std::next_permutation(order.begin(),order.end()));
    }
  }
  // Stream ID is a scheduling priority at equal timestamps. Preserve the
  // existing verified plan, and try a few renumberings only under initial
  // resource contention. Original tasks and extra guards are reconstructed.
  if(found && graph.n<=2048 && answer.streams.size()>1) {
    int demand[2]={0,0};I memory_demand=0;
    for(const auto& s:answer.streams)if(s.tasks.front().wait_before.empty()) {
      const auto& v=nodes[graph.index.at(s.tasks.front().op_id)];demand[static_cast<int>(v.core_type)]+=v.core_num;memory_demand=positive_add(memory_demand,positive_add(v.workspace_memory,v.output_memory));
    }
    if(demand[0]>hw.aic_core_num || demand[1]>hw.aiv_core_num || memory_demand>hw.memory_limit) {
      int streams=static_cast<int>(answer.streams.size());auto order=best_order;
      std::vector<int> owner(graph.n),producer(graph.n,-1),head(streams);
      for(int s=0;s<streams;++s) {
        head[s]=graph.index.at(answer.streams[s].tasks.front().op_id);
        for(const auto& t:answer.streams[s].tasks){int i=graph.index.at(t.op_id);owner[i]=s;if(t.record_after>=0)producer[t.record_after]=i;}
      }
      std::vector<std::pair<int,int>> extra;
      for(const auto& s:answer.streams)for(const auto& t:s.tasks){int i=graph.index.at(t.op_id);for(int e:t.wait_before){int p=producer[e];if(std::find(graph.in[i].begin(),graph.in[i].end(),p)==graph.in[i].end())extra.emplace_back(p,i);}}
      budget=metrics.candidates+3;
      for(int mode=0;mode<3;++mode) {
        std::vector<int> permutation(streams);for(int s=0;s<streams;++s)permutation[s]=s;
        if(mode==0)std::reverse(permutation.begin(),permutation.end());
        else std::sort(permutation.begin(),permutation.end(),[&](int a,int b){int i=head[a],j=head[b];I ma=positive_add(nodes[i].workspace_memory,nodes[i].output_memory),mb=positive_add(nodes[j].workspace_memory,nodes[j].output_memory);
          if(mode==1)return ma!=mb?ma<mb:a<b;
          return graph.rank[i]!=graph.rank[j]?graph.rank[i]>graph.rank[j]:a<b;});
        std::vector<int> position(streams),assignment(graph.n);for(int s=0;s<streams;++s)position[permutation[s]]=s;
        for(int i=0;i<graph.n;++i)assignment[i]=position[owner[i]];
        consider(order,assignment,streams,0,extra);
      }
    }
  }
  // Feasibility recovery AFTER all existing search and Stream arbitration.
  // This preserves the complete trajectory of every previously feasible
  // case, including improvements produced by late neighbourhood selection.
  if(!found && graph.n<=10000) {
    budget=metrics.candidates+5;
    auto order=memory_ordering(hw,graph,4);
    if(static_cast<int>(order.size())==graph.n) {
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,16)})if(s>1) {
        auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);
        if(graph.n<=512)consider(order,assignment,s,2);
      }
    }
  }
  if(!found && graph.n<=10000) {
    budget=metrics.candidates+10;
    std::vector<std::vector<int>> recovery;
    if(graph.n<=512){auto order=beam_ordering(hw,graph);if(static_cast<int>(order.size())==graph.n)recovery.push_back(std::move(order));}
    auto greedy=memory_ordering(hw,graph,5);if(static_cast<int>(greedy.size())==graph.n)recovery.push_back(std::move(greedy));
    for(const auto& order:recovery) {
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);if(graph.n<=512)consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n<=4096) {
    budget=metrics.candidates+9;
    for(int mode=0;mode<3;++mode) {
      auto order=bundle_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      int s=std::min(largest,4);if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);if(graph.n<=512)consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n<=512) {
    budget=metrics.candidates+6;
    for(int mode=0;mode<2;++mode) {
      auto order=beam_ordering(hw,graph,32,12,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      int s=std::min(largest,4);if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n<=512) {
    budget=metrics.candidates+3;
    auto order=sink_projection_order(hw,graph,true);
    if(static_cast<int>(order.size())==graph.n) {
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      int s=std::min(largest,4);if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n<=512) {
    budget=metrics.candidates+3;
    auto order=sink_projection_order(hw,graph);
    if(static_cast<int>(order.size())==graph.n) {
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      int s=std::min(largest,4);if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n>=16 && graph.n<=2048 && (hw.event_record_time || hw.event_wait_time)) {
    budget=metrics.candidates+4;
    for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})for(int mode=0;mode<2;++mode) {
      auto candidate=resource_delayed(hw,graph,s,mode,mode==1);
      if(static_cast<int>(candidate.order.size())==graph.n)consider(candidate.order,candidate.assignment,s,0,candidate.guards);
    }
  }
  if(certified())return finish();
  // Preserve all existing arbitration first, then compare a small resource-
  // aware portfolio for QUALITY. Unlike the recovery-only strategy above,
  // these candidates cannot displace any already examined neighbourhood.
  if(found && graph.n>=16 && graph.n<=2048 && largest>1) {
    budget=metrics.candidates+4;
    for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})for(int mode=0;mode<2;++mode) {
      auto candidate=resource_list(hw,graph,s,mode,mode==1);
      if(static_cast<int>(candidate.order.size())==graph.n)consider(candidate.order,candidate.assignment,s,0,candidate.guards);
    }
    budget=metrics.candidates+4;
    for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})for(int mode=2;mode<4;++mode) {
      auto candidate=resource_list(hw,graph,s,mode,false);
      if(static_cast<int>(candidate.order.size())==graph.n)consider(candidate.order,candidate.assignment,s,0,candidate.guards);
    }
    if(hw.event_record_time || hw.event_wait_time) {
      budget=metrics.candidates+4;
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})for(int mode:{0,2}) {
        auto candidate=resource_delayed(hw,graph,s,mode,false);
        if(static_cast<int>(candidate.order.size())==graph.n)consider(candidate.order,candidate.assignment,s,0,candidate.guards);
      }
    }
  }
  // Complete small co-consumer groups so all their actual direct-user
  // releases contribute to the bundle score, without adding data edges.
  if(!found && graph.n<=4096) {
    budget=metrics.candidates+9;
    for(int mode=24;mode<27 && !found;++mode) {
      auto order=bundle_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);}
    }
  }
  if(!found && graph.n<=4096) {
    budget=metrics.candidates+9;
    for(int mode=27;mode<30 && !found;++mode) {
      auto order=bundle_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);}
    }
  }
  if(!found && graph.n<=4096) {
    budget=metrics.candidates+9;
    for(int mode=30;mode<33 && !found;++mode) {
      auto order=bundle_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);}
    }
  }
  if(!found && graph.n>512 && graph.n<=4096) {
    budget=metrics.candidates+9;
    for(int mode=33;mode<36 && !found;++mode) {
      auto order=bundle_ordering(hw,graph,mode);if(static_cast<int>(order.size())!=graph.n)continue;
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);}
    }
  }
  if(!found && graph.n<=512) {
    budget=metrics.candidates+3;
    auto order=sink_projection_order(hw,graph,true,true);
    if(static_cast<int>(order.size())==graph.n) {
      std::vector<int> serial(graph.n,0);consider(order,serial,1,0,{},true);
      int s=std::min(largest,4);if(s>1){auto assignment=assign(hw,graph,order,s,0);consider(order,assignment,s);consider(order,assignment,s,2);}
    }
  }
  if(!found && graph.n<=4096) {
    auto order=strict_fork_join_order(graph);
    if(static_cast<int>(order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,order,s,0);
        consider(order,assignment,s);consider(order,assignment,s,2);
      }
    }
  }
  if(!found && graph.n<=768) {
    // Recovery evidence showed useful completions on the first macro path;
    // failed-path backtracking consumed CPU without restoring more cases.
    // Policy truncation is explicit and never an infeasibility certificate.
    auto searched=serial_frontier_search(hw,graph,8000000,false,true);
    if(static_cast<int>(searched.order.size())!=graph.n)searched=serial_frontier_search(hw,graph,8000000,true,true);
    if(static_cast<int>(searched.order.size())!=graph.n)searched=serial_frontier_search(hw,graph,8000000,true,true,true);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      std::vector<int> serial(graph.n,0);consider(searched.order,serial,1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
  if(!found && graph.n<=4096) {
    auto searched=shallow_memory_search(hw,graph);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
  if(!found && graph.n<=4096) {
    auto searched=projection_memory_search(hw,graph);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
  if(!found) throw std::runtime_error("No verified feasible plan in bounded search; feasibility is not guaranteed by this heuristic");
  return finish();
}
