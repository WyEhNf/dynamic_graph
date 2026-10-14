#include "problem.h"
#include <algorithm>
#include <chrono>
#include <limits>
#include <queue>
#include <set>
#include <stdexcept>
#include <tuple>
#include <unordered_map>

namespace aicore_detail {
using I = int64_t;
struct Metrics { I candidates=0, feasible=0, time=-1, peak=-1, micros=0; };
thread_local Metrics metrics;
struct Graph {
  const std::vector<OperatorNode>& v;
  int n;
  std::unordered_map<int,int> index;
  std::vector<std::vector<int>> in,out;
  std::vector<I> rank, release;
  std::vector<int> topo;
  Graph(const HardwareInfo& h,const std::vector<OperatorNode>& nodes):v(nodes),n(static_cast<int>(nodes.size())),in(n),out(n),rank(n),release(n) {
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
      int i=*it; for(int j:out[i]) rank[i]=std::max(rank[i],rank[j]); rank[i]+=v[i].exec_time;
    }
    for(int i=0;i<n;++i) for(int p:in[i]) release[i]+=v[p].output_memory/static_cast<I>(out[p].size());
  }
};

// Submission-side simulation is implemented separately from the local verifier.
struct Evaluation {bool valid=false; I time=0,peak=0;};
Evaluation evaluate(const HardwareInfo& h,const Graph& g,const SchedulePlan& plan) {
  std::vector<const StreamPlan*> flows;
  for(const auto& s:plan.streams)if(!s.tasks.empty())flows.push_back(&s);
  Evaluation e; const int streams=static_cast<int>(flows.size());
  if(streams>h.stream_num) return e;
  struct Task {int node,event; std::vector<int> wait;};
  std::vector<std::vector<Task>> tasks(streams);
  std::vector<int> owner(g.n,-1),position(g.n,-1),record(g.n,-1);
  std::unordered_map<int,int> event_owner;
  int next_event=0;
  for(int s=0;s<streams;++s) for(const auto& t:flows[s]->tasks) {
    if(!g.index.count(t.op_id)) return e;
    int i=g.index.at(t.op_id); if(owner[i]>=0) return e;
    owner[i]=s; position[i]=static_cast<int>(tasks[s].size()); record[i]=t.record_after;
    if(t.record_after< -1)return e;
    if(t.record_after>=0 && !event_owner.emplace(t.record_after,next_event++).second) return e;
    tasks[s].push_back({i,t.record_after,t.wait_before});
  }
  for(int i=0;i<g.n;++i) if(owner[i]<0) return e;
  std::vector<int> recorder(next_event,-1),waited(next_event);
  for(int i=0;i<g.n;++i) if(record[i]>=0) recorder[event_owner.at(record[i])]=i;
  for(int s=0;s<streams;++s) for(auto& t:tasks[s]) {
    std::sort(t.wait.begin(),t.wait.end());
    if(std::adjacent_find(t.wait.begin(),t.wait.end())!=t.wait.end()) return e;
    for(int p:g.in[t.node]) {
      if(owner[p]==s) {if(position[p]>=position[t.node]) return e;}
      else if(record[p]<0 || !std::binary_search(t.wait.begin(),t.wait.end(),record[p])) return e;
    }
    for(int& w:t.wait) {
      if(!event_owner.count(w)) return e;
      w=event_owner.at(w); if(owner[recorder[w]]==s) return e; ++waited[w];
    }
    if(t.event>=0) t.event=event_owner.at(t.event);
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
          if(cores[type]+v.core_num>capacity || memory+v.workspace_memory+v.output_memory>h.memory_limit) continue;
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

SchedulePlan assemble(const Graph& g,const std::vector<int>& order,const std::vector<int>& assignment,int streams,int guards) {
  SchedulePlan plan; plan.streams.resize(streams);
  std::vector<std::vector<int>> before=g.in;
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
} // namespace aicore_detail

// Optional telemetry does not change the official interface.
int64_t AicoreLastMetric(int key) {
  const auto& m=aicore_detail::metrics;
  switch(key) {case 0:return m.candidates;case 1:return m.feasible;case 2:return m.time;case 3:return m.peak;case 4:return m.micros;default:return -1;}
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
  const int budget=graph.n>2048?36:(graph.n>512?96:220);
  bool found=false;Evaluation best;SchedulePlan answer;
  std::vector<int> best_order,best_assignment;int best_streams=1;
  auto consider=[&](const SchedulePlan& p,const std::vector<int>& order,const std::vector<int>& assignment,int streams) {
    if(metrics.candidates>=budget)return;
    ++metrics.candidates;auto e=evaluate(hw,graph,p);
    if(!e.valid || e.time>deadline_us)return;
    ++metrics.feasible;
    if(!found || std::tie(e.time,e.peak)<std::tie(best.time,best.peak)) {
      found=true;best=e;answer=p;best_order=order;best_assignment=assignment;best_streams=streams;
    }
  };
  for(int mode=0;mode<modes;++mode) {
    auto order=ordering(graph,mode);std::vector<int> assignment(graph.n,0);
    consider(assemble(graph,order,assignment,1,0),order,assignment,1);
  }
  for(int mode=0;mode<modes && metrics.candidates<budget;++mode) {
    auto order=ordering(graph,mode);
    for(int streams:counts) if(streams>1) for(int affinity=0;affinity<2;++affinity) {
      auto assignment=assign(hw,graph,order,streams,affinity);
      consider(assemble(graph,order,assignment,streams,0),order,assignment,streams);
      if(graph.n<=512) consider(assemble(graph,order,assignment,streams,2),order,assignment,streams);
    }
  }
  if(found && graph.n<=512) {
    auto order=best_order;auto assignment=best_assignment;int streams=best_streams;
    for(size_t k=0;k<order.size() && metrics.candidates<budget;++k) {
      int i=order[k];
      for(int s=0;s<std::min(streams,4) && metrics.candidates<budget;++s) if(s!=assignment[i]) {
        auto moved=assignment;moved[i]=s;
        consider(assemble(graph,order,moved,streams,0),order,moved,streams);
      }
      if(k+1<order.size()) {
        int j=order[k+1];
        if(std::find(graph.in[j].begin(),graph.in[j].end(),i)==graph.in[j].end()) {
          auto swapped=order;std::swap(swapped[k],swapped[k+1]);
          consider(assemble(graph,swapped,assignment,streams,0),swapped,assignment,streams);
        }
      }
    }
  }
  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
  if(!found) throw std::runtime_error("No verified feasible plan in bounded search; feasibility is not guaranteed by this heuristic");
  metrics.time=best.time;metrics.peak=best.peak;
  return answer;
}
