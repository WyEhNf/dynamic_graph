#include "simulator.h"
#include <algorithm>
#include <limits>
#include <set>
#include <unordered_map>

SimulationResult Simulate(const HardwareInfo& hw,const std::vector<OperatorNode>& nodes,
                          const SchedulePlan& raw,int64_t deadline) {
  SimulationResult r;
  auto fail=[&](const std::string& message){r.error=message; return r;};
  if(hw.aic_core_num<0 || hw.aiv_core_num<0 || hw.stream_num<1 || hw.memory_limit<0 ||
     hw.event_record_time<0 || hw.event_wait_time<0) return fail("Invalid hardware");
  const int n=static_cast<int>(nodes.size());
  std::unordered_map<int,int> ix;
  for(int i=0;i<n;++i) {
    const auto& v=nodes[i];
    if(!ix.emplace(v.id,i).second) return fail("Duplicate operator ID");
    int core=static_cast<int>(v.core_type);
    if(core<0 || core>1 || v.core_num<1 || v.core_num>128 || v.exec_time<1 ||
       v.exec_time>1000000000LL || v.workspace_memory<0 || v.output_memory<0)
      return fail("Invalid operator attributes");
    if(v.core_num>(core==0?hw.aic_core_num:hw.aiv_core_num)) return fail("Operator exceeds core capacity");
  }
  std::vector<int> successors(n), remaining(n);
  std::vector<std::vector<int>> graph(n);
  for(int i=0;i<n;++i) {
    std::set<int> seen;
    for(int id:nodes[i].inputs) {
      if(!ix.count(id) || !seen.insert(id).second || ix.at(id)==i) return fail("Invalid inputs");
      int p=ix.at(id); ++successors[p]; graph[p].push_back(i);
    }
    remaining[i]=static_cast<int>(nodes[i].inputs.size());
  }
  std::vector<int> queue;
  for(int i=0;i<n;++i) if(!remaining[i]) queue.push_back(i);
  for(size_t k=0;k<queue.size();++k) for(int j:graph[queue[k]]) if(!--remaining[j]) queue.push_back(j);
  if(static_cast<int>(queue.size())!=n) return fail("Graph is cyclic");
  auto streams=raw.streams;
  streams.erase(std::remove_if(streams.begin(),streams.end(),[](const auto& s){return s.tasks.empty();}),streams.end());
  if(static_cast<int>(streams.size())>hw.stream_num) return fail("Too many nonempty streams");
  const int count=static_cast<int>(streams.size());
  std::vector<int> stream_of(n,-1), position(n,-1), recorded(n,-1);
  std::unordered_map<int,int> recorder, wait_count;
  for(int s=0;s<count;++s) for(int k=0;k<static_cast<int>(streams[s].tasks.size());++k) {
    const auto& t=streams[s].tasks[k];
    if(!ix.count(t.op_id)) return fail("Unknown scheduled operator");
    int i=ix.at(t.op_id);
    if(stream_of[i]>=0) return fail("Operator scheduled twice");
    stream_of[i]=s; position[i]=k; recorded[i]=t.record_after;
    if(t.record_after< -1) return fail("Invalid record event");
    if(t.record_after>=0 && !recorder.emplace(t.record_after,i).second) return fail("Duplicate event recorder");
    std::set<int> seen;
    for(int e:t.wait_before) {
      if(e<0 || !seen.insert(e).second) return fail("Invalid or duplicate wait event");
      ++wait_count[e];
    }
  }
  for(int i=0;i<n;++i) if(stream_of[i]<0) return fail("Missing operator");
  for(auto [e,i]:recorder) if(!wait_count.count(e)) return fail("Recorded event never waited");
  for(int s=0;s<count;++s) for(const auto& t:streams[s].tasks) {
    for(int e:t.wait_before) {
      if(!recorder.count(e)) return fail("Wait event has no recorder");
      if(stream_of[recorder.at(e)]==s) return fail("Same-stream event is forbidden");
    }
    int i=ix.at(t.op_id);
    for(int id:nodes[i].inputs) {
      int p=ix.at(id);
      if(stream_of[p]==s) {if(position[p]>=position[i]) return fail("Same-stream dependency reversed");}
      else if(recorded[p]<0 || std::find(t.wait_before.begin(),t.wait_before.end(),recorded[p])==t.wait_before.end())
        return fail("Direct cross-stream dependency lacks explicit synchronization");
    }
  }
  // State machine: Waiting -> Wait timer -> Compute ready -> Compute timer -> Record timer.
  // All completions at t release resources before starts at t. Starts follow compressed stream ID.
  struct State {int task=0, phase=0; int64_t until=-1;};
  std::vector<State> state(count);
  std::set<int> ready_events;
  std::vector<bool> done(n,false);
  auto live_successors=successors;
  r.starts.assign(n,-1); r.ends.assign(n,-1);
  int used[2]={0,0}, completed=0;
  int64_t now=0, memory=0;
  while(completed<n) {
    bool changed=true;
    while(changed) {
      changed=false;
      // Timed transitions are completed together before the next resource allocation.
      for(int s=0;s<count;++s) {
        auto& st=state[s]; if(st.task>=static_cast<int>(streams[s].tasks.size())) continue;
        auto& task=streams[s].tasks[st.task]; int i=ix.at(task.op_id); const auto& v=nodes[i];
        if(st.until!=now) continue;
        if(st.phase==1) {st.phase=2; st.until=-1; changed=true;}
        else if(st.phase==3) {
          used[static_cast<int>(v.core_type)]-=v.core_num; memory-=v.workspace_memory;
          done[i]=true; r.ends[i]=now; ++completed; r.makespan=std::max(r.makespan,now);
          for(int id:v.inputs) {int p=ix.at(id); if(--live_successors[p]==0) memory-=nodes[p].output_memory;}
          if(task.record_after>=0 && hw.event_record_time==0) {
            ready_events.insert(task.record_after); ++st.task; st.phase=0; st.until=-1;
          }
          else if(task.record_after>=0) {st.phase=4; st.until=now+hw.event_record_time;}
          else {++st.task; st.phase=0; st.until=-1;}
          changed=true;
        } else if(st.phase==4) {
          ready_events.insert(task.record_after); ++st.task; st.phase=0; st.until=-1; changed=true;
        }
      }
      if(completed==n) break; // T excludes final Record; sink outputs last until whole graph finishes.
      for(int s=0;s<count;++s) {
        auto& st=state[s]; if(st.task>=static_cast<int>(streams[s].tasks.size())) continue;
        auto& task=streams[s].tasks[st.task]; int i=ix.at(task.op_id); const auto& v=nodes[i];
        if(st.phase==0) {
          bool ready=true; for(int e:task.wait_before) if(!ready_events.count(e)) ready=false;
          if(!ready) continue;
          st.phase=1; st.until=now+static_cast<int64_t>(task.wait_before.size())*hw.event_wait_time;
          changed=true;
          // Zero wait timers are immediate before a later stream is attempted.
          if(st.until==now) {st.phase=2; st.until=-1;}
        }
        if(st.phase==2) {
          int type=static_cast<int>(v.core_type), capacity=type==0?hw.aic_core_num:hw.aiv_core_num;
          if(used[type]+v.core_num>capacity || memory+v.workspace_memory+v.output_memory>hw.memory_limit) continue;
          for(int id:v.inputs) if(!done[ix.at(id)]) return fail("Dependency executes before producer completes");
          used[type]+=v.core_num; memory+=v.workspace_memory+v.output_memory;
          r.peak_memory=std::max(r.peak_memory,memory); r.starts[i]=now;
          st.phase=3; st.until=now+v.exec_time; changed=true;
        }
      }
    }
    if(completed==n) break;
    int64_t next=std::numeric_limits<int64_t>::max();
    for(const auto& st:state) if(st.until>now) next=std::min(next,st.until);
    if(next==std::numeric_limits<int64_t>::max()) return fail("Deadlock: events, cores or live-output memory");
    now=next;
  }
  r.valid=true; r.meets_deadline=r.makespan<=deadline; return r;
}
