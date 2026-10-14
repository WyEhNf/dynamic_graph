#include "cholesky/vm_step_bound.hpp"
#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>

namespace chol { namespace {
using O=Opcode;using U=std::uint64_t;using S=std::int64_t;
struct Stop {const char* reason;};
struct Meter {
  U used=0,limit;
  void tick(U count=1){if(count>limit-used)throw Stop{"work-limit"};used+=count;}
};
U plus(U a,U b){if(b>std::numeric_limits<U>::max()-a)throw Stop{"bound-overflow"};return a+b;}
U times(U a,U b){if(a&&b>std::numeric_limits<U>::max()/a)throw Stop{"bound-overflow"};return a*b;}
std::size_t index(double value,std::size_t size){
  if(!std::isfinite(value)||value<0||std::trunc(value)!=value||value>=static_cast<double>(size))throw Stop{"bad-index"};
  return static_cast<std::size_t>(value);
}
constexpr S exact_limit=S{1}<<53;
struct Value {
  enum Kind {Unknown,Constant,Induction}kind=Unknown;S integer=0;
  static Value known(S n){return {Constant,n};}
  bool operator==(const Value&)const=default;
};
Value literal(double x){
  if(!std::isfinite(x)||std::trunc(x)!=x||x<-static_cast<double>(exact_limit)||x>static_cast<double>(exact_limit))return {};
  return Value::known(static_cast<S>(x));
}
struct State {std::map<std::size_t,Value> slots;std::vector<Value> stack;};
Value pop(State& s){if(s.stack.empty())throw Stop{"stack-state"};auto v=s.stack.back();s.stack.pop_back();return v;}
void push(State& s,Value v){if(s.stack.size()>=4096)throw Stop{"stack-state"};s.stack.push_back(v);}
Value binary(O op,Value a,Value b){
  if(a.kind!=Value::Constant||b.kind!=Value::Constant)return {};
  const S x=a.integer,y=b.integer;
  // Signed64 cannot overflow: inputs are limited to2^53, add/sub to2^54;
  // multiplication is checked before it is performed.
  switch(op){
    case O::Add:if(x+y>=-exact_limit&&x+y<=exact_limit)return Value::known(x+y);break;
    case O::Sub:if(x-y>=-exact_limit&&x-y<=exact_limit)return Value::known(x-y);break;
    case O::Mul:
      if(x==0||y==0)return Value::known(0);
      if(std::abs(x)<=exact_limit/std::abs(y))return Value::known(x*y);
      break;
    case O::Lt:return Value::known(x<y);case O::Le:return Value::known(x<=y);
    case O::Gt:return Value::known(x>y);case O::Ge:return Value::known(x>=y);
    case O::Eq:return Value::known(x==y);case O::Ne:return Value::known(x!=y);
    default:break;
  }
  return {};
}
void step(State& s,const Instruction& in,const Metadata& m,std::optional<std::size_t> iv={}){
  const O op=in.opcode;
  if(static_cast<unsigned>(op)>static_cast<unsigned>(O::Return))throw Stop{"bad-opcode"};
  switch(op){
    case O::Const:push(s,literal(in.argument));break;
    case O::Load:{auto slot=index(in.argument,m.slots);auto it=s.slots.find(slot);push(s,iv&&slot==*iv?Value{Value::Induction,0}:it==s.slots.end()?Value{}:it->second);break;}
    case O::Store:{auto slot=index(in.argument,m.slots);auto v=pop(s);if(v.kind==Value::Constant)s.slots[slot]=v;else s.slots.erase(slot);break;}
    case O::Uninit:s.slots.erase(index(in.argument,m.slots));break;
    case O::Read:(void)pop(s);push(s,{});break;
    case O::Write:(void)pop(s);(void)pop(s);break;
    case O::Dup:{auto v=pop(s);push(s,v);push(s,v);break;}
    case O::Pop:(void)pop(s);break;
    case O::Neg:{auto v=pop(s);push(s,v.kind==Value::Constant?Value::known(-v.integer):Value{});break;}
    case O::Trunc:{auto v=pop(s);if(v.kind==Value::Induction)push(s,v);else push(s,v.kind==Value::Constant&&v.integer>=INT32_MIN&&v.integer<=INT32_MAX?v:Value{});break;}
    case O::Not:case O::Bool:{auto v=pop(s);push(s,v.kind==Value::Constant?Value::known(op==O::Not?v.integer==0:v.integer!=0):Value{});break;}
    case O::Sqrt:case O::Abs:(void)pop(s);push(s,{});break;
    case O::Fma:(void)pop(s);(void)pop(s);(void)pop(s);push(s,{});break;
    case O::Jump:break;
    case O::Jz:case O::Jnz:case O::Return:(void)pop(s);break;
    default:{auto right=pop(s),left=pop(s);push(s,binary(op,left,right));break;}
  }
}
void merge(std::optional<State>& dst,const State& src,Meter& meter){
  meter.tick(plus(src.stack.size(),plus(src.slots.size(),1)));
  if(!dst){dst=src;return;}
  if(dst->stack.size()!=src.stack.size())throw Stop{"stack-merge"};
  for(std::size_t i=0;i<src.stack.size();++i)if(dst->stack[i]!=src.stack[i])dst->stack[i]={};
  for(auto it=dst->slots.begin();it!=dst->slots.end();){
    meter.tick();auto other=src.slots.find(it->first);
    if(other==src.slots.end()||it->second!=other->second)it=dst->slots.erase(it);else ++it;
  }
}
using Graph=std::vector<std::vector<std::size_t>>;
struct Loop {std::size_t head,latch,guard,iv,tail;S increment;std::set<std::size_t> writes;std::vector<std::size_t> exits;bool early_exit=false;};
std::vector<std::size_t> topo(const Graph& graph,const std::vector<bool>& active,Meter& meter){
  meter.tick(times(graph.size(),3)); // allocations and full scans, including inactive nodes
  std::vector<std::size_t> degree(graph.size(),0),result;std::deque<std::size_t> ready;std::size_t count=0;
  for(std::size_t i=0;i<graph.size();++i)if(active[i]){++count;for(auto j:graph[i])if(active[j]){meter.tick();++degree[j];}}
  for(std::size_t i=0;i<graph.size();++i)if(active[i]&&!degree[i])ready.push_back(i);
  while(!ready.empty()){auto i=ready.front();ready.pop_front();result.push_back(i);meter.tick();for(auto j:graph[i])if(active[j]&&!--degree[j])ready.push_back(j);}
  if(result.size()!=count)throw Stop{"unproved-cycle"};
  return result;
}
} // namespace

StepBoundProof prove_vm_step_bound(const Metadata& m,std::uint32_t n,unsigned block,U limit) noexcept {
  Meter meter{0,limit};std::size_t loop_count=0;
  try {
    const auto size=m.program.size();
    if(!size||size>100000||!m.slots||m.slots>100000||m.shape_slot>=m.slots||m.block_slot< -1||(m.block_slot>=0&&static_cast<std::size_t>(m.block_slot)>=m.slots))throw Stop{"metadata-shape"};
    meter.tick(times(size,3));Graph cfg(size+1),pred(size+1);std::vector<bool> reachable(size+1,false);std::deque<std::size_t> pending{0};reachable[0]=true;
    while(!pending.empty()){
      auto pc=pending.front();pending.pop_front();meter.tick();if(pc==size)continue;
      const auto in=m.program[pc];if(static_cast<unsigned>(in.opcode)>static_cast<unsigned>(O::Return))throw Stop{"bad-opcode"};
      if(in.opcode==O::Load||in.opcode==O::Store||in.opcode==O::Uninit)(void)index(in.argument,m.slots);
      if(in.opcode==O::Jump)cfg[pc]={index(in.argument,size)};
      else if(in.opcode==O::Jz||in.opcode==O::Jnz)cfg[pc]={pc+1,index(in.argument,size)};
      else if(in.opcode==O::Return)cfg[pc]={size};
      else cfg[pc]={pc+1};
      for(auto dest:cfg[pc]){meter.tick();pred[dest].push_back(pc);if(!reachable[dest]){reachable[dest]=true;pending.push_back(dest);}}
    }
    std::vector<Loop> loops;
    for(std::size_t latch=0;latch<size;++latch)if(reachable[latch])for(auto head:cfg[latch])if(head<=latch){
      meter.tick();if(m.program[latch].opcode!=O::Jump||latch<head+6)throw Stop{"unproved-backedge"};
      const auto tail=latch-5;
      const O pattern[]={O::Load,O::Const,O::Add,O::Trunc,O::Store,O::Jump};
      for(std::size_t k=0;k<6;++k)if(m.program[tail+k].opcode!=pattern[k])throw Stop{"induction-update"};
      auto iv=index(m.program[tail].argument,m.slots);if(index(m.program[latch-1].argument,m.slots)!=iv)throw Stop{"induction-update"};
      auto increment=literal(m.program[tail+1].argument);if(increment.kind!=Value::Constant||increment.integer<=0||increment.integer>INT32_MAX)throw Stop{"induction-step"};
      for(auto k=tail+1;k<=latch;++k)if(pred[k].size()!=1||pred[k][0]!=k-1)throw Stop{"update-bypass"};
      auto guard=head;
      for(;guard<tail;++guard){auto op=m.program[guard].opcode;if(op==O::Jz)break;if(op==O::Jump||op==O::Jnz||op==O::Return||op==O::Store||op==O::Uninit||op==O::Read||op==O::Write)throw Stop{"guard-form"};}
      if(guard>=tail||guard==head||m.program[guard-1].opcode!=O::Lt||index(m.program[guard].argument,size)!=latch+1)throw Stop{"guard-form"};
      Loop loop{head,latch,guard,iv,tail,increment.integer,{},{latch+1},false};
      std::set<std::size_t> invariant;
      for(auto k=head;k<guard;++k)if(m.program[k].opcode==O::Load){auto slot=index(m.program[k].argument,m.slots);if(slot!=iv)invariant.insert(slot);}
      for(auto k=head;k<=latch;++k)if(reachable[k]){
        meter.tick();for(auto origin:pred[k])if((origin<head||origin>latch)&&k!=head)throw Stop{"loop-side-entry"};
        for(auto dest:cfg[k]){
          if(dest<head)throw Stop{"unproved-backedge"};
          if(dest>latch){loop.exits.push_back(dest);if(k!=guard&&m.program[k].opcode!=O::Return)loop.early_exit=true;}
        }
        auto op=m.program[k].opcode;
        if(op==O::Store||op==O::Uninit){auto slot=index(m.program[k].argument,m.slots);loop.writes.insert(slot);if(invariant.contains(slot)||(slot==iv&&k!=latch-1))throw Stop{"induction-or-bound-write"};}
      }
      std::sort(loop.exits.begin(),loop.exits.end());loop.exits.erase(std::unique(loop.exits.begin(),loop.exits.end()),loop.exits.end());loops.push_back(std::move(loop));
    }
    std::sort(loops.begin(),loops.end(),[](const Loop& a,const Loop& b){return a.head<b.head;});
    for(std::size_t i=1;i<loops.size();++i)if(loops[i].head<=loops[i-1].latch)throw Stop{"nested-or-shared-loop"};
    loop_count=loops.size();
    // Removing only the verified latch edge must eliminate ALL cycles.
    meter.tick(times(size+1,6));Graph without=cfg;for(const auto& l:loops)without[l.latch].clear();(void)topo(without,reachable,meter);
    Graph outer=cfg;auto active=reachable;
    std::map<std::size_t,std::size_t> loop_at;
    for(std::size_t i=0;i<loops.size();++i){const auto& l=loops[i];loop_at[l.head]=i;outer[l.head]=l.exits;for(auto k=l.head+1;k<=l.latch;++k)active[k]=false;}
    auto order=topo(outer,active,meter);meter.tick(times(size+1,2));std::vector<std::optional<State>> states(size+1);std::vector<U> costs(size+1,0);State start;start.slots[m.shape_slot]=Value::known(n);if(m.block_slot>=0)start.slots[static_cast<std::size_t>(m.block_slot)]=Value::known(block);states[0]=std::move(start);
    for(auto pc:order){
      if(!states[pc])continue;
      meter.tick(plus(states[pc]->slots.size(),plus(states[pc]->stack.size(),1)));State state=*states[pc];U weight=1;
      if(pc==size)continue;
      auto found=loop_at.find(pc);
      if(found==loop_at.end())step(state,m.program[pc],m);
      else {
        const auto& l=loops[found->second];if(!state.stack.empty())throw Stop{"loop-stack"};auto initial=state.slots.find(l.iv);if(initial==state.slots.end()||initial->second.kind!=Value::Constant||initial->second.integer<INT32_MIN||initial->second.integer>INT32_MAX)throw Stop{"induction-initial"};S begin=initial->second.integer;
        meter.tick(plus(state.slots.size(),plus(state.stack.size(),1)));
        State guard_state=state;for(auto k=l.head;k<l.guard-1;++k){meter.tick();step(guard_state,m.program[k],m,l.iv);}
        auto bound=pop(guard_state),induction=pop(guard_state);if(!guard_state.stack.empty()||induction.kind!=Value::Induction||bound.kind!=Value::Constant||bound.integer<INT32_MIN||bound.integer>INT32_MAX)throw Stop{"guard-values"};
        U trips=bound.integer<=begin?0:static_cast<U>((bound.integer-begin+l.increment-1)/l.increment);
        U distance=times(trips,static_cast<U>(l.increment));if(distance>static_cast<U>(INT32_MAX-begin))throw Stop{"induction-range"};S last=begin+static_cast<S>(distance);
        // Body stack analysis and longest path count are independent of data.
        meter.tick(times(size+1,3));auto body_active=std::vector<bool>(size+1,false);for(auto k=l.guard+1;k<=l.latch;++k)body_active[k]=reachable[k];
        auto body_order=topo(without,body_active,meter);std::vector<std::optional<State>> body_states(size+1);std::vector<U> body_cost(size+1,0);
        meter.tick(plus(state.slots.size(),plus(state.stack.size(),1)));
        State body_entry=state;body_entry.slots.erase(l.iv);body_states[l.guard+1]=std::move(body_entry);U maximum=0;
        for(auto k:body_order)if(body_states[k]){
          meter.tick(plus(body_states[k]->slots.size(),plus(body_states[k]->stack.size(),1)));State body=*body_states[k];step(body,m.program[k],m);U used=plus(body_cost[k],1);
          if(k==l.latch){if(!body.stack.empty())throw Stop{"loop-stack"};maximum=std::max(maximum,used);}
          else for(auto dest:cfg[k]){
            if(dest>l.latch){if(!body.stack.empty())throw Stop{"loop-exit-stack"};maximum=std::max(maximum,used);}
            else if(dest>=l.guard+1){body_cost[dest]=std::max(body_cost[dest],used);merge(body_states[dest],body,meter);}
            else throw Stop{"body-guard-reentry"};
          }
        }
        weight=plus(times(plus(trips,1),l.guard-l.head+1),times(trips,maximum));
        for(auto slot:l.writes)state.slots.erase(slot);
        if(!l.early_exit)state.slots[l.iv]=Value::known(last);
      }
      U cost=plus(costs[pc],weight);
      for(auto dest:outer[pc]){if(!active[dest])throw Stop{"collapsed-side-entry"};costs[dest]=std::max(costs[dest],cost);merge(states[dest],state,meter);}
    }
    if(!states[size]||costs[size]==std::numeric_limits<U>::max())throw Stop{"no-finite-exit"};
    return {true,costs[size],meter.used,loop_count,"proved"};
  }catch(const Stop& stop){return {false,0,meter.used,loop_count,stop.reason};}
  catch(...){return {false,0,meter.used,loop_count,"analysis-allocation"};}
}
} // namespace chol
