#include "cholesky/vm_nested_step_bound.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using O=chol::Opcode;using I=chol::Instruction;using U=std::uint64_t;
namespace {
unsigned rectangles=0,triangles=0,triples=0,errors=0,boundaries=0,unknowns=0,mutations=0,proved_mutations=0,old_runs=0;
void require(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
struct Spec {int start,end,increment;bool parent_bound=false,shape_bound=false;};
struct Site {std::size_t start,head,guard,body,tail,latch,end;unsigned slot;};
struct Built {chol::Metadata m;std::vector<Site> sites;};
Built program(const std::vector<Spec>& specs,bool data_exit=false){
  Built b;b.m.algorithm="ast_vm_v2";b.m.arithmetic="fp64_source_order_no_implicit_fma";b.m.dependencies="source_control_flow";b.m.slots=specs.size()+3;
  auto& p=b.m.program;
  auto emit=[&](auto&& self,std::size_t level)->void{
    auto spec=specs[level];auto slot=unsigned(level+1);Site site{};site.slot=slot;site.start=p.size();
    p.insert(p.end(),{{O::Const,double(spec.start)},{O::Trunc},{O::Store,double(slot)}});site.head=p.size();p.push_back({O::Load,double(slot)});
    if(spec.parent_bound){require(level>0,"parent bound at root");p.push_back({O::Load,double(slot-1)});}
    else if(spec.shape_bound)p.push_back({O::Load,0});else p.push_back({O::Const,double(spec.end)});
    p.push_back({O::Lt});site.guard=p.size();p.push_back({O::Jz,0});site.body=p.size();const auto where=b.sites.size();b.sites.push_back(site);
    if(level+1<specs.size())self(self,level+1);else p.insert(p.end(),{{O::Const,0},{O::Pop}});
    if(data_exit&&level+1==specs.size())p.insert(p.end(),{{O::Const,0},{O::Read,0},{O::Jz,0}});
    site.tail=p.size();p.insert(p.end(),{{O::Load,double(slot)},{O::Const,double(spec.increment)},{O::Add},{O::Trunc},{O::Store,double(slot)},{O::Jump,double(site.head)}});site.latch=p.size()-1;site.end=p.size();p[site.guard].argument=double(site.end);b.sites[where]=site;
  };
  emit(emit,0);const auto returned=p.size();p.insert(p.end(),{{O::Const,0},{O::Return}});
  if(data_exit)for(auto& in:p)if(in.opcode==O::Jz&&in.argument==0)in.argument=double(returned);
  return b;
}
U actual_golden(const std::vector<Spec>& specs,std::size_t depth=0,int parent=0,int n=3){
  const auto s=specs[depth];const int end=s.parent_bound?parent:s.shape_bound?n:s.end;U steps=3;
  // Independent direct enumeration counts instructions, not candidate summaries.
  for(int value=s.start;;value+=s.increment){steps+=4;if(value>=end)break;steps+=depth+1<specs.size()?actual_golden(specs,depth+1,value,n):2;steps+=6;}
  return steps;
}
U conservative_golden(const std::vector<Spec>& specs,std::size_t depth=0,int parent_lo=0,int parent_hi=0,int n=3){
  const auto s=specs[depth];const int end=s.parent_bound?parent_hi:s.shape_bound?n:s.end;const U trips=end<=s.start?0:U((end-s.start+s.increment-1)/s.increment);
  U body=2;
  if(trips&&depth+1<specs.size())body=conservative_golden(specs,depth+1,s.start,s.start+int(trips-1)*s.increment,n);
  (void)parent_lo;return 3+4*(trips+1)+trips*(body+6);
}
struct Observed {U steps;std::string error;};
Observed run(const chol::Metadata& m,U budget=100000,bool zero=false){
  chol::RunMetrics metrics;chol::Options opts;opts.engine="vm";opts.vm_backend="legacy";opts.simd="portable";opts.block_size=7;opts.vm_step_limit=budget;opts.metrics=&metrics;std::string error;
  try{(void)chol::execute({3,std::vector<double>(9,zero?0.0:1.0)},m,opts);}catch(const std::exception& e){error=e.what();}
  ++old_runs;return {metrics.vm_steps,error};
}
void golden(const std::vector<Spec>& specs){
  const auto b=program(specs);const auto proof=chol::prove_vm_nested_step_bound(b.m,3,7);const U expected=actual_golden(specs)+2,upper=conservative_golden(specs)+2;
  if(!proof.proved){std::cerr<<"gold unknown "<<proof.reason<<'\n';throw std::runtime_error("golden not proved");}
  require(proof.bound==upper,"independent conservative instruction bound differs");auto got=run(b.m);require(got.error.empty()&&got.steps==expected,"original VM count differs");require(expected<=proof.bound,"bound below original steps");
  auto exact=run(b.m,expected),shorter=run(b.m,expected-1);require(exact.error.empty()&&exact.steps==expected,"exact actual-step budget failed");require(shorter.error=="VM instruction limit exceeded"&&shorter.steps==expected,"one-short step contract differs");boundaries+=2;
  std::cout<<"{\"kind\":\"root_gold\",\"bound\":"<<proof.bound<<",\"actual_steps\":"<<got.steps<<",\"specs\":[";
  for(std::size_t k=0;k<specs.size();++k){auto s=specs[k];if(k)std::cout<<',';std::cout<<'['<<s.start<<','<<s.end<<','<<s.increment<<','<<(s.parent_bound?"true":"false")<<','<<(s.shape_bound?"true":"false")<<']';}
  std::cout<<"]}\n";
}
void unknown(const chol::Metadata& m){auto p=chol::prove_vm_nested_step_bound(m,3,7);require(!p.proved&&p.bound==0,"targeted unsafe program proved");++unknowns;}
void bounded(const chol::Metadata& m,bool want_error=false){auto p=chol::prove_vm_nested_step_bound(m,3,7);require(p.proved&&p.bound<100000,"valid conservative program not proved");for(bool zero:{false,true}){auto got=run(m,100000,zero);require(got.steps<=p.bound,"pre-error or early-exit steps exceed bound");if(want_error)require(!got.error.empty(),"expected VM error absent");}++errors;}
}
int main(){try{
  for(int a:{-1,0,1})for(int ae:{-1,0,2,4})for(int as:{1,2})for(int b:{-1,0,1})for(int be:{-1,0,2,4})for(int bs:{1,2}){golden({{a,ae,as},{b,be,bs}});++rectangles;}
  for(int a:{-1,0,1})for(int ae=0;ae<=5;++ae)for(int as:{1,2})for(int b:{-1,0,1})for(int bs:{1,2}){golden({{a,ae,as},{b,0,bs,true}});++triangles;}
  for(int a:{0,1,3})for(int as:{1,2})for(int b:{0,1,3})for(int bs:{1,2})for(int c:{0,1,3})for(int cs:{1,2}){golden({{0,a,as},{0,b,bs},{0,c,cs}});++triples;}
  for(int a:{1,3,5})for(int as:{1,2})for(int b:{-1,0,1})for(int bs:{1,2})for(int c:{-1,0}){golden({{0,a,as},{b,0,bs,true},{c,0,1,true}});++triples;}
  golden({{0,0,1,false,true},{0,0,1,true}});++triangles;
  auto base=program({{0,3,1},{0,2,1}});auto renamed=base.m;
  for(auto& in:renamed.program)if((in.opcode==O::Load||in.opcode==O::Store)&&in.argument==2)in.argument=4;
  bounded(renamed);
  auto dead=base.m;dead.program.push_back({O::Load,-1});dead.program.push_back({O::Jump,std::numeric_limits<double>::quiet_NaN()});bounded(dead);
  auto early=program({{0,3,1},{0,2,1}},true);bounded(early.m);
  auto fault=base.m;const auto leaf=base.sites[1].body;fault.program[leaf]={O::Const,-1};fault.program[leaf+1]={O::Read,0};fault.program.insert(fault.program.begin()+leaf+2,{O::Pop,0});
  // Rebase all targets past the inserted POP, while preserving complete PROGRAM.
  for(auto& in:fault.program)if((in.opcode==O::Jump||in.opcode==O::Jz||in.opcode==O::Jnz)&&in.argument>=double(leaf+2))++in.argument;bounded(fault,true);
  auto changed=base.m;changed.program[base.sites[1].start]={O::Load,2};unknown(changed); //child retains previous value, uninitialized first entry
  changed=base.m;changed.program[base.sites[1].start]={O::Load,4};unknown(changed);
  changed=base.m;changed.program[base.sites[1].start]={O::Const,.125};unknown(changed);
  changed=base.m;changed.program[base.sites[1].start]={O::Const,std::numeric_limits<double>::infinity()};unknown(changed);
  changed=base.m;changed.program[base.sites[1].tail+4]={O::Store,1};unknown(changed); //child changes parent's progress
  changed=base.m;changed.program[leaf+1]={O::Uninit,1};unknown(changed);
  changed=base.m;changed.program[leaf]={O::Load,1};changed.program[leaf+1]={O::Store,1};unknown(changed);
  changed=base.m;changed.program[leaf]={O::Jump,double(base.sites[0].latch)};unknown(changed); //parent-tail bypass
  changed=base.m;changed.program[leaf]={O::Jump,double(base.sites[1].tail+2)};unknown(changed); //partial child latch
  changed=base.m;changed.program[0]={O::Jump,double(leaf)};unknown(changed); //side entry, no dominating child header
  changed=base.m;changed.program[base.sites[1].tail+1].argument=0;unknown(changed);
  changed=base.m;changed.program[base.sites[1].tail+1].argument=-1;unknown(changed);
  changed=base.m;changed.program[base.sites[1].tail+1].argument=.5;unknown(changed);
  changed=base.m;changed.program[base.sites[1].guard-1].opcode=O::Le;unknown(changed);
  changed=base.m;changed.program[leaf+1].opcode=O::Dup;unknown(changed); //loop boundary stack mismatch
  changed=base.m;changed.program[leaf].opcode=O::Pop;unknown(changed);
  auto over=program({{0,2,1},{INT32_MAX-1,INT32_MAX,2}});unknown(over.m);
  auto many=program({{0,INT32_MAX,1},{0,INT32_MAX,1},{0,INT32_MAX,1}});unknown(many.m); //uint64 cost overflow, no VM execution
  changed=base.m;changed.program[base.sites[0].head+1]={O::Load,3};changed.program[leaf]={O::Const,1};changed.program[leaf+1]={O::Store,3};unknown(changed); //write guard invariant
  chol::Metadata irreducible=base.m;irreducible.program={{O::Const,0},{O::Jz,3},{O::Jump,0},{O::Const,1},{O::Jnz,2},{O::Const,0},{O::Return}};unknown(irreducible);
  for(U work=0;work<200;++work){auto p=chol::prove_vm_nested_step_bound(base.m,3,7,work);require(!p.proved&&p.bound==0&&p.work<=work,"work cap bypass");++unknowns;}
  require(chol::prove_vm_nested_step_bound(base.m,3,7).proved,"state persisted after work exhaustion");
  const double arguments[]={-1,0,1,2,3,7,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()};
  for(const auto& seed:{base,program({{0,3,1},{0,0,1,true}})})for(std::size_t pc=0;pc<seed.m.program.size();++pc)for(unsigned op=0;op<34;++op)for(double argument:arguments){
    auto mutant=seed.m;mutant.program[pc]={static_cast<O>(op),argument};++mutations;auto proof=chol::prove_vm_nested_step_bound(mutant,3,7);if(!proof.proved)continue;
    require(proof.bound<20000,"mutation proof unexpectedly large");
    for(bool zero:{false,true}){auto got=run(mutant,20000,zero);require(got.steps<=proof.bound,"mutant original VM exceeded proof bound");}
    ++proved_mutations;
  }
  require(chol::Options{}.vm_step_limit==1000000000ull&&chol::Options{}.vm_budget_mode=="fixed","default budget changed");
  std::cout<<"{\"passed\":true,\"rectangular_goldens\":"<<rectangles<<",\"triangular_goldens\":"<<triangles<<",\"three_level_goldens\":"<<triples<<",\"exact_actual_and_one_short_boundaries\":"<<boundaries<<",\"early_or_pre_error_cases\":"<<errors<<",\"unknown_cases\":"<<unknowns<<",\"single_position_mutations\":"<<mutations<<",\"proved_mutations\":"<<proved_mutations<<",\"original_VM_executions\":"<<old_runs<<",\"newRuntimeIntegration\":false,\"N10000_execution\":false}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
