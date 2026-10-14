#include "problem.h"
#include <algorithm>
#include <chrono>
#include <functional>
#include <limits>
#include <queue>
#include <set>
#include <stdexcept>
#include <tuple>
#include <unordered_map>

namespace aicore_detail {
using I = int64_t;
struct Metrics { I candidates=0, feasible=0, time=-1, peak=-1, micros=0, duplicates=0, attempts=0, beam_expansions=0,beam_width=0; };
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
    for(int i=0;i<n;++i) for(int p:in[i]) release[i]+=v[p].output_memory/static_cast<I>(out[p].size());
  }
};

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
          if(t.event>=0 && h.event_record_time) {c.stage=4;c.due=clock+h.event_record_time;}
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
          c.stage=1;c.due=clock+static_cast<I>(t.wait.size())*h.event_wait_time;changed=true;
          if(c.due==clock) {c.stage=2;c.due=-1;}
        }
        if(c.stage==2) {
          int type=static_cast<int>(v.core_type),capacity=type==0?h.aic_core_num:h.aiv_core_num;
          if(cores[type]+v.core_num>capacity || memory+v.workspace_memory+v.output_memory>h.memory_limit) {e.contended=true;continue;}
          for(int p:g.in[t.node]) if(!done[p]) return e;
          cores[type]+=v.core_num; memory+=v.workspace_memory+v.output_memory;
          e.peak=std::max(e.peak,memory);c.stage=3;c.due=clock+v.exec_time;changed=true;
        }
      }
    }
    if(completed==g.n) break;
    I next=std::numeric_limits<I>::max();
    for(const auto& c:cursor) if(c.due>clock) next=std::min(next,c.due);
    if(next==std::numeric_limits<I>::max()) return e;
    clock=next;
  }
  e.valid=true;return e;
}

std::vector<int> ordering(const Graph& g,int mode) {
  auto score=[&](int i)->std::tuple<I,I,I> {
    const auto& v=g.v[i];
    if(mode==1) return {g.release[i]-v.output_memory,-v.workspace_memory,g.rank[i]};
    if(mode==2) return {-v.workspace_memory-v.output_memory,g.rank[i],g.release[i]};
    if(mode==3) return {-static_cast<I>(v.id),0,0};
    if(mode==4) return {g.rank[i]/std::max<I>(1,v.output_memory+v.workspace_memory),g.release[i],g.rank[i]};
    if(mode==5) return {g.release[i]-v.output_memory-v.workspace_memory,g.rank[i],-static_cast<I>(v.id)};
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
  Evaluation e; I live=0;
  std::vector<int> users(g.n);for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  for(int i:order) {
    live+=g.v[i].workspace_memory+g.v[i].output_memory;
    e.peak=std::max(e.peak,live);if(live>h.memory_limit)return e;
    e.time+=g.v[i].exec_time;live-=g.v[i].workspace_memory;
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
  if(guards)for(size_t k=1;k<order.size();++k)if(guards==1 || g.v[order[k-1]].workspace_memory+g.v[order[k]].workspace_memory>0)edges.emplace_back(order[k-1],order[k]);
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
  for(int i=0;i<g.n;++i)for(int p:g.in[i])if(users[p]==1)release[i]+=g.v[p].output_memory;
  auto score=[&](int i)->Score {
    const auto& v=g.v[i];I net=release[i]-v.output_memory;
    if(mode==0)return {net,-v.workspace_memory,g.rank[i],0};
    if(mode==1)return {net-v.workspace_memory,net,g.rank[i],0};
    if(mode==3)return {g.height[i],net,-v.workspace_memory,0};
    if(mode==4 || mode==5) {
      I prospective=0,opening=std::numeric_limits<I>::max();
      I shared=0;
      for(int child:g.out[i])if(!done[child]) {
        opening=std::min<I>(opening,degree[child]);
        if(degree[child]==1)prospective+=std::max<I>(0,release[child]-g.v[child].output_memory);
        if(mode==5 && g.in[child].size()<=64){I live=0;for(int p:g.in[child])if(done[p])live+=g.v[p].output_memory;shared=std::max(shared,live);}
      }
      // When no output is live yet, prefer a consumer needing fewer missing
      // inputs. This opens a compact frontier rather than an arbitrary centre
      // of a memory window. Thereafter attachment follows surviving inputs.
      if(mode==4)return {net,prospective,attachment[i],-opening};
      if(net>=0)return {2,net,prospective,-opening};
      if(shared>0)return {1,prospective,shared,-opening};
      return {0,-opening,-v.workspace_memory-v.output_memory,g.rank[i]};
    }
    return {-v.workspace_memory-v.output_memory,net,g.rank[i],0};
  };
  auto push=[&](int i){queue.push({score(i),i,++version[i]});};
  for(int i=0;i<g.n;++i)if(!degree[i])push(i);
  std::vector<int> result;result.reserve(g.n);I live=0;
  while(static_cast<int>(result.size())<g.n) {
    std::vector<Entry> blocked;int chosen=-1;
    while(!queue.empty()) {
      auto e=queue.top();queue.pop();if(done[e.node] || e.version!=version[e.node])continue;
      const auto& v=g.v[e.node];
      if(live+v.workspace_memory+v.output_memory<=h.memory_limit){chosen=e.node;break;}
      blocked.push_back(e);
    }
    for(const auto& e:blocked)queue.push(e);
    if(chosen<0)return {};
    int i=chosen;result.push_back(i);done[i]=true;live+=g.v[i].output_memory;
    for(int p:g.in[i]) {
      if(!--users[p])live-=g.v[p].output_memory;
      else if(users[p]==1)for(int j:g.out[p])if(!done[j]){release[j]+=g.v[p].output_memory;if(!degree[j])push(j);break;}
    }
    for(int j:g.out[i]) {
      if(!--degree[j])push(j);
      else if((mode==4 || mode==5) && g.in[j].size()<=64)for(int p:g.in[j])if(!done[p]) {
        attachment[p]+=g.v[i].output_memory;
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
        const auto& v=g.v[i];if(state.live+v.workspace_memory+v.output_memory>h.memory_limit)continue;
        I released=0;for(int p:g.in[i])if(state.users[p]==1)released+=g.v[p].output_memory;
        I net=released-v.output_memory,opening=std::numeric_limits<I>::max(),prospective=0,shared=0;
        for(int c:g.out[i])if(!state.done[c] && g.in[c].size()<=64) {
          opening=std::min<I>(opening,state.degree[c]);I live=0,future=0;
          for(int p:g.in[c]){if(state.done[p])live+=g.v[p].output_memory;if(state.users[p]==1)future+=g.v[p].output_memory;}
          shared=std::max(shared,live);if(state.degree[c]==1)prospective+=std::max<I>(0,future-g.v[c].output_memory);
        }
        Score score=net>=0?Score{2,net,prospective,-opening}:(shared>0?Score{1,prospective,shared,-opening}:Score{0,-opening,-v.workspace_memory-v.output_memory,g.rank[i]});
        options.emplace_back(score,i);
      }
      std::sort(options.begin(),options.end(),[&](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:g.v[a.second].id<g.v[b.second].id;});
      if(options.size()>static_cast<size_t>(branching))options.resize(branching);
      for(auto option:options) {
        int i=option.second;State child=state;++metrics.beam_expansions;child.hash^=mix(static_cast<uint64_t>(i));
        child.peak=std::max(child.peak,child.live+g.v[i].workspace_memory+g.v[i].output_memory);child.live+=g.v[i].output_memory;child.done[i]=1;child.order.push_back(i);
        auto it=std::find(child.ready.begin(),child.ready.end(),i);*it=child.ready.back();child.ready.pop_back();
        for(int p:g.in[i])if(!--child.users[p]){child.live-=g.v[p].output_memory;child.freed+=g.v[p].output_memory;}
        for(int c:g.out[i])if(!--child.degree[c])child.ready.push_back(c);
        children.push_back(std::move(child));
      }
    }
    if(children.empty())return {};
    auto score=[&](const State& state){I nearest=std::numeric_limits<I>::max();for(int i=0;i<g.n;++i)if(!state.done[i] && !g.in[i].empty()) {
      bool active=false;for(int p:g.in[i])if(state.done[p] && g.v[p].output_memory){active=true;break;}if(active)nearest=std::min<I>(nearest,state.degree[i]);
    }
      if(mode==1){I residual=0;for(int i=0;i<g.n;++i)if(state.done[i])residual+=g.out[i].empty()?g.v[i].output_memory*1024:g.v[i].output_memory*1024*state.users[i]/static_cast<I>(g.out[i].size());return std::make_tuple(residual,state.live,state.peak,-state.freed);}
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
  std::vector<int> users(g.n),marks(g.n);std::vector<unsigned char> done(g.n);int epoch=0;
  for(int i=0;i<g.n;++i)users[i]=static_cast<int>(g.out[i].size());
  std::vector<int> result;result.reserve(g.n);I live=0;
  while(static_cast<int>(result.size())<g.n) {
    using Score=std::tuple<I,I,I,I>;
    Score best{std::numeric_limits<I>::min(),0,0,0};std::vector<int> selected;
    std::vector<int> targets;
    for(int i=0;i<g.n;++i)if(!done[i] && (!g.in[i].empty() || g.out[i].empty()))targets.push_back(i);
    if(g.n>512 && targets.size()>128) {
      using Hint=std::tuple<I,I,I>;std::vector<std::vector<Hint>> hints(4,std::vector<Hint>(g.n));
      for(int i:targets) {
        I need=g.v[i].output_memory,credit=0,released=0,missing=0;
        for(int p:g.in[i])if(done[p]){credit+=g.v[p].output_memory;if(users[p]==1)released+=g.v[p].output_memory;}else{need+=g.v[p].output_memory+g.v[p].workspace_memory;++missing;}
        hints[0][i]={released-need,credit,-missing};hints[1][i]={-need,credit,-missing};
        hints[2][i]={credit*1024/(need+1),-missing,-need};hints[3][i]={-missing,credit,-g.v[i].workspace_memory-g.v[i].output_memory};
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
      stack.emplace_back(target,0);
      int visited=0;bool bounded=true;
      while(!stack.empty()) {
        auto& frame=stack.back();int i=frame.first;
        if(done[i] || marks[i]==epoch){stack.pop_back();continue;}
        if(!frame.second && ++visited>64){bounded=false;break;}
        while(frame.second<g.in[i].size() && (done[g.in[i][frame.second]] || marks[g.in[i][frame.second]]==epoch))++frame.second;
        if(frame.second<g.in[i].size())stack.emplace_back(g.in[i][frame.second++],0);
        else {marks[i]=epoch;bundle.push_back(i);stack.pop_back();}
      }
      if(!bounded)continue;
      I next=live,peak=live,new_output=0,credit=0;bool fit=true;
      std::vector<int> touched;
      for(int i:bundle) {
        const auto& v=g.v[i];peak=std::max(peak,next+v.workspace_memory+v.output_memory);
        if(peak>h.memory_limit){fit=false;break;}
        next+=v.output_memory;new_output+=v.output_memory;
        for(int p:g.in[i]) {
          if(done[p])credit+=g.v[p].output_memory;
          touched.push_back(p);if(!--users[p])next-=g.v[p].output_memory;
        }
      }
      for(int p:touched)++users[p];
      if(!fit)continue;
      I gain=live-next;
      Score score=mode==0?Score{gain,credit,-peak,-static_cast<I>(bundle.size())}:
        mode==1?Score{-new_output,credit,gain,-peak}:Score{credit*1024/(new_output+1),gain,-peak,-static_cast<I>(bundle.size())};
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
// It is bounded by 18 sinks, 512 nodes and eight million elementary probes.
std::vector<int> sink_projection_order(const HardwareInfo& h,const Graph& g,bool partition=false) {
  if(g.n>512)return {};
  std::vector<int> sinks;for(int i=0;i<g.n;++i)if(g.out[i].empty())sinks.push_back(i);
  std::vector<std::vector<int>> groups;
  for(int i:sinks)groups.push_back({i});
  if(sinks.size()>18) {
    if(!partition || sinks.size()>72)return {};
    std::vector<int> owner(g.n,-1),parent(sinks.size()),size(sinks.size(),1);
    for(size_t i=0;i<sinks.size();++i){owner[sinks[i]]=static_cast<int>(i);parent[i]=static_cast<int>(i);}
    auto root=[&](int i){while(parent[i]!=i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
    std::unordered_map<int,I> affinity;
    for(int p=0;p<g.n;++p)if(g.v[p].output_memory && !g.out[p].empty() && g.out[p].size()<=16) {
      std::vector<int> children;for(int c:g.out[p])if(owner[c]>=0)children.push_back(owner[c]);
      I weight=g.v[p].output_memory*1024/static_cast<I>(g.out[p].size());
      for(size_t a=0;a<children.size();++a)for(size_t b=a+1;b<children.size();++b){int i=std::min(children[a],children[b]),j=std::max(children[a],children[b]);affinity[i*static_cast<int>(sinks.size())+j]+=weight;}
    }
    std::vector<std::pair<I,int>> edges;for(const auto& x:affinity)edges.emplace_back(x.second,x.first);
    std::sort(edges.begin(),edges.end(),[](const auto& a,const auto& b){return a.first!=b.first?a.first>b.first:a.second<b.second;});
    int count=static_cast<int>(sinks.size());
    for(const auto& edge:edges) {
      int a=root(edge.second/static_cast<int>(sinks.size())),b=root(edge.second%static_cast<int>(sinks.size()));
      if(a==b || size[a]+size[b]>4)continue;
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
        const auto& v=g.v[i];x.peak=std::max(x.peak,x.live+v.workspace_memory+v.output_memory);
        if(x.peak>h.memory_limit){fit=false;break;}
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
  for(unsigned mask=0;mask<states;++mask)if(peak[mask]!=infinity) {
    I live=0;for(int i=0;i<g.n;++i)if((mask&(1u<<i)) && (!succ[i] || (succ[i]&~mask)))live+=g.v[i].output_memory;
    for(int i=0;i<g.n;++i)if(!(mask&(1u<<i)) && !(pred[i]&~mask)) {
      unsigned next=mask|(1u<<i);I cost=std::max(peak[mask],live+g.v[i].workspace_memory+g.v[i].output_memory);
      if(cost<peak[next]){peak[next]=cost;last[next]=i;}
    }
  }
  std::vector<int> order;for(unsigned mask=states-1;mask;){int i=last[mask];order.push_back(i);mask^=1u<<i;}
  std::reverse(order.begin(),order.end());return order;
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
    if(mode==1){ca+=g.v[a].workspace_memory;cb+=g.v[b].workspace_memory;}
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
    if(assignment[p]!=assignment[i] && (guards==1 || g.v[p].workspace_memory+g.v[i].workspace_memory>0)) before[i].push_back(p);
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
  for(int i:order) {
    int best=0; I cost=std::numeric_limits<I>::max();
    for(int s=0;s<streams;++s) {
      I start=available[s],waits=0;
      for(int p:g.in[i]) {start=std::max(start,finish[p]+(result[p]!=s?h.event_record_time:0));if(result[p]!=s)++waits;}
      I end=start+waits*h.event_wait_time+g.v[i].exec_time;
      if(affinity && last_type[s]>=0 && last_type[s]!=static_cast<int>(g.v[i].core_type)) end+=h.event_record_time+h.event_wait_time;
      if(end<cost) {cost=end;best=s;}
    }
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
        if(cores[type]+v.core_num>cap || memory+v.workspace_memory+v.output_memory>h.memory_limit)continue;
        I release=0;for(int p:g.in[i])if(users[p]==1)release+=g.v[p].output_memory;
        I local=0;for(int p:g.in[i])if(result.assignment[p]==s)local+=h.event_wait_time+h.event_record_time;
        std::tuple<I,I,I> score=mode==0?std::make_tuple(g.rank[i]+local,release-v.output_memory,-v.workspace_memory):
                                                   std::make_tuple(release-v.output_memory,g.rank[i]+local,-v.workspace_memory);
        if(chosen<0 || score>best){chosen=static_cast<int>(k);best=score;}
      }
      if(chosen<0)continue;
      int i=ready[chosen];ready[chosen]=ready.back();ready.pop_back();const auto& v=g.v[i];
      std::vector<int> waits;for(int p:g.in[i])if(result.assignment[p]!=s)waits.push_back(p);
      if(guard)for(int other=0;other<streams;++other)if(other!=s && frontier[other]>=0) {
        int p=frontier[other];result.guards.emplace_back(p,i);waits.push_back(p);
      }
      std::sort(waits.begin(),waits.end());waits.erase(std::unique(waits.begin(),waits.end()),waits.end());
      I start=clock;for(int p:waits)start=std::max(start,finish[p]+h.event_record_time);
      finish[i]=start+static_cast<I>(waits.size())*h.event_wait_time+v.exec_time;
      flow_ready[s]=finish[i]+h.event_record_time;active[s]=i;result.assignment[i]=s;result.order.push_back(i);
      cores[static_cast<int>(v.core_type)]+=v.core_num;memory+=v.workspace_memory+v.output_memory;
    }
    if(completed==g.n)break;
    I next=std::numeric_limits<I>::max();
    for(int s=0;s<streams;++s){if(active[s]>=0)next=std::min(next,finish[active[s]]);else if(flow_ready[s]>clock)next=std::min(next,flow_ready[s]);}
    if(next==std::numeric_limits<I>::max()){result.order.clear();return result;}
    clock=next;
  }
  return result;
}
} // namespace aicore_detail

// Optional telemetry does not change the official interface.
int64_t AicoreLastMetric(int key) {
  const auto& m=aicore_detail::metrics;
  switch(key) {case 0:return m.candidates;case 1:return m.feasible;case 2:return m.time;case 3:return m.peak;case 4:return m.micros;case 5:return m.duplicates;case 6:return m.attempts;case 7:return m.beam_expansions;case 8:return m.beam_width;default:return -1;}
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
  const int largest=std::min({hw.stream_num,graph.n,256});
  std::set<int> counts{1,largest};for(int s:{2,3,4,8,16,32,64,128})if(s<=largest)counts.insert(s);
  const int modes=graph.n>2048?4:6;
  const int base_budget=graph.n>2048?36:(graph.n>512?96:220);int budget=base_budget;
  bool found=false;Evaluation best;SchedulePlan answer;
  std::vector<int> best_order,best_assignment;int best_streams=1;
  struct CachedCandidate {std::vector<int> key;Evaluation evaluation;};
  std::unordered_map<uint64_t,std::vector<CachedCandidate>> seen;
  auto consider=[&](const std::vector<int>& order,const std::vector<int>& assignment,int streams,int guards=0,
                    const std::vector<std::pair<int,int>>& extra=std::vector<std::pair<int,int>>{},bool serial=false)->Evaluation {
    if(metrics.candidates>=budget)return {};
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
  std::vector<std::vector<int>> orders;for(int mode=0;mode<modes;++mode)orders.push_back(ordering(graph,mode));
  bool serial_fits=false;
  for(const auto& order:orders) {
    std::vector<int> assignment(graph.n,0);serial_fits=serial_fits || serial_evaluate(hw,graph,order).valid;
    consider(order,assignment,1,0,{},true);
  }
  if(!serial_fits && graph.n<=18) {
    auto order=serial_oracle(graph);std::vector<int> assignment(graph.n,0);
    consider(order,assignment,1,0,{},true);orders.push_back(std::move(order));
  }
  for(const auto& order:orders) {
    if(metrics.candidates>=budget)break;
    for(int streams:counts) if(streams>1 && metrics.candidates<budget) for(int affinity=0;affinity<2 && metrics.candidates<budget;++affinity) {
      auto assignment=assign(hw,graph,order,streams,affinity);
      consider(order,assignment,streams);
      if(graph.n<=512) consider(order,assignment,streams,2);
    }
  }
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
      const auto& v=nodes[graph.index.at(s.tasks.front().op_id)];demand[static_cast<int>(v.core_type)]+=v.core_num;memory_demand+=v.workspace_memory+v.output_memory;
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
        else std::sort(permutation.begin(),permutation.end(),[&](int a,int b){int i=head[a],j=head[b];I ma=nodes[i].workspace_memory+nodes[i].output_memory,mb=nodes[j].workspace_memory+nodes[j].output_memory;
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
  // Preserve all existing arbitration first, then compare a small resource-
  // aware portfolio for QUALITY. Unlike the recovery-only strategy above,
  // these candidates cannot displace any already examined neighbourhood.
  if(found && graph.n>=16 && graph.n<=2048 && largest>1) {
    budget=metrics.candidates+4;
    for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})for(int mode=0;mode<2;++mode) {
      auto candidate=resource_list(hw,graph,s,mode,mode==1);
      if(static_cast<int>(candidate.order.size())==graph.n)consider(candidate.order,candidate.assignment,s,0,candidate.guards);
    }
  }
  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
  if(!found) throw std::runtime_error("No verified feasible plan in bounded search; feasibility is not guaranteed by this heuristic");
  metrics.time=best.time;metrics.peak=best.peak;
  return answer;
}
