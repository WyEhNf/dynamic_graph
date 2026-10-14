#include "samples.h"
#include "candidate_search.h"
#include "simulator.h"
#include <algorithm>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
static int cases=0;
void check(bool condition,const std::string& name) {
  ++cases; if(!condition) throw std::runtime_error(name);
}
int main() {
  try {
    auto hw=SampleHardware(); auto nodes=SampleGraph(); auto plan=SamplePlan();
    auto r=Simulate(hw,nodes,plan,400);
    check(r.valid && r.meets_deadline && r.makespan==365 && r.peak_memory==320,"official sample 1");
    check(!Simulate(hw,nodes,plan,364).meets_deadline,"deadline gate");
    auto generated=ScheduleCvGraph(hw,nodes,400);
    auto gr=Simulate(hw,nodes,generated,400);
    check(gr.valid && gr.meets_deadline,"baseline sample 1 validated independently");
    auto selected=SelectFeasibleCandidate(hw,nodes,400);
    check(selected.plan && selected.simulation.valid && selected.simulation.meets_deadline,"bounded candidate search filters feasibility");
    auto impossible=SelectFeasibleCandidate(hw,nodes,1);
    check(!impossible.plan,"no feasible candidate does not return an invalid plan");
    std::cout<<"sample1_reference T="<<r.makespan<<" peak="<<r.peak_memory
             <<" baseline_T="<<gr.makespan<<" baseline_peak="<<gr.peak_memory<<'\n';
    HardwareInfo h2{8,8,2,200,2,2};
    std::vector<OperatorNode> n2{{0,CoreType::AIC,8,100,20,10,{}},
                               {1,CoreType::AIV,4,80,15,10,{}},{2,CoreType::AIV,4,20,10,5,{0,1}}};
    SchedulePlan p2{{{{{0,{},0}}},{{{1,{},-1},{2,{0},-1}}}}};
    r=Simulate(h2,n2,p2,200);
    check(r.valid && r.makespan==124 && r.peak_memory==55,"official sample 2");
    std::cout<<"sample2_reference T="<<r.makespan<<" peak="<<r.peak_memory<<'\n';
    HardwareInfo h3{8,8,2,50,2,3};
    std::vector<OperatorNode> n3{{0,CoreType::AIC,4,60,20,10,{}},
                               {1,CoreType::AIV,4,50,20,5,{}},{2,CoreType::AIC,4,100,5,5,{1}}};
    SchedulePlan p3{{{{{0,{0},-1}}},{{{1,{},0},{2,{},-1}}}}};
    r=Simulate(h3,n3,p3,220);
    check(r.valid && r.makespan==152 && r.peak_memory==45,"official sample 3 with extra event");
    std::cout<<"sample3_reference T="<<r.makespan<<" peak="<<r.peak_memory<<'\n';
    // Sparse/negative operator IDs, reordered input nodes, sparse event IDs, empty-stream compression.
    for(auto& v:n2) {v.id=v.id*7+101; for(int& id:v.inputs) id=id*7+101;}
    for(auto& s:p2.streams) for(auto& t:s.tasks) {t.op_id=t.op_id*7+101; if(t.record_after>=0)t.record_after=1000007; for(int& e:t.wait_before)e=1000007;}
    std::reverse(n2.begin(),n2.end()); p2.streams.insert(p2.streams.begin(),StreamPlan{});
    r=Simulate(h2,n2,p2,200);
    check(r.valid && r.makespan==124 && r.peak_memory==55,"sparse IDs and compressed streams");
    auto invalid=plan; invalid.streams[0].tasks.back().wait_before.clear();
    check(!Simulate(hw,nodes,invalid,400).valid,"missing cross-stream synchronization");
    invalid=plan; invalid.streams[0].tasks.back().wait_before={1,1};
    check(!Simulate(hw,nodes,invalid,400).valid,"duplicate wait rejected");
    invalid=plan; invalid.streams[0].tasks[0].record_after=0;
    check(!Simulate(hw,nodes,invalid,400).valid,"duplicate record rejected");
    invalid=plan; invalid.streams[0].tasks[1].wait_before={0};
    check(!Simulate(hw,nodes,invalid,400).valid,"same stream event rejected");
    invalid=plan; invalid.streams[0].tasks[0].record_after=42;
    check(!Simulate(hw,nodes,invalid,400).valid,"unconsumed record rejected");
    invalid=plan; invalid.streams[0].tasks.push_back({0,{},-1});
    check(!Simulate(hw,nodes,invalid,400).valid,"duplicate operator rejected");
    invalid=plan; invalid.streams[0].tasks.erase(invalid.streams[0].tasks.begin());
    check(!Simulate(hw,nodes,invalid,400).valid,"missing operator rejected");
    auto cyclic=nodes; cyclic[0].inputs={5};
    check(!Simulate(hw,cyclic,plan,400).valid,"graph cycle rejected");
    // Event cycle independent of data DAG.
    HardwareInfo hc{1,1,2,100,1,1};
    std::vector<OperatorNode> nc{{10,CoreType::AIC,1,1,0,0,{}},{20,CoreType::AIV,1,1,0,0,{}}};
    SchedulePlan pc{{{{{10,{2},1}}},{{{20,{1},2}}}}};
    check(!Simulate(hc,nc,pc,100).valid,"event deadlock detected");
    // Resource-blocked earlier stream must not prevent later streams progressing.
    HardwareInfo hb{1,1,3,100,0,0};
    std::vector<OperatorNode> nb{{0,CoreType::AIC,1,10,0,0,{}},
                               {1,CoreType::AIC,1,10,0,0,{}},{2,CoreType::AIV,1,10,0,0,{}}};
    SchedulePlan pb{{{{{0,{},-1}}},{{{1,{},-1}}},{{{2,{},-1}}}}};
    r=Simulate(hb,nb,pb,20);
    check(r.valid && r.starts[0]==0 && r.starts[1]==10 && r.starts[2]==0,"resource arbitration and half-open intervals");
    // Retained sink output can make an otherwise individually fitting plan impossible.
    HardwareInfo hm{1,1,1,35,0,0};
    std::vector<OperatorNode> nm{{0,CoreType::AIC,1,1,0,30,{}},{1,CoreType::AIC,1,1,10,0,{}}};
    SchedulePlan pm{{{{{0,{},-1},{1,{},-1}}}}};
    check(!Simulate(hm,nm,pm,10).valid,"sink output retained until graph completion");
    auto hz=h2; hz.event_record_time=hz.event_wait_time=0;
    r=Simulate(hz,n2,p2,200);
    check(r.valid && r.makespan==120,"zero event durations");
    check(Simulate(hw,{},SchedulePlan{},0).valid,"empty graph");
    // Producer outputs survive until the LAST direct consumer COMPUTE ends, not starts.
    HardwareInfo hl{2,1,2,100,0,0};
    std::vector<OperatorNode> nl{{0,CoreType::AIC,1,1,0,20,{}},
                               {1,CoreType::AIC,1,10,10,0,{0}},
                               {2,CoreType::AIC,1,20,10,0,{0}}};
    SchedulePlan pl{{{{{0,{},7},{1,{},-1}}},{{{2,{7},-1}}}}};
    r=Simulate(hl,nl,pl,100);
    check(r.valid && r.makespan==21 && r.peak_memory==40,"last direct consumer output lifetime");
    std::mt19937 rng(20261010);
    for(int round=0;round<50;++round) {
      HardwareInfo hr{4,4,4,1000000,2,3};
      std::vector<OperatorNode> nr;
      for(int i=0;i<25;++i) {
        OperatorNode v{1000+i*13,static_cast<CoreType>(rng()%2),static_cast<int>(rng()%4+1),
                       static_cast<int64_t>(rng()%100+1),static_cast<int64_t>(rng()%50),
                       static_cast<int64_t>(rng()%20),{}};
        for(int p=0;p<i;++p) if(rng()%10==0) v.inputs.push_back(1000+p*13);
        nr.push_back(v);
      }
      std::shuffle(nr.begin(),nr.end(),rng);
      auto pr=ScheduleCvGraph(hr,nr,1000000);
      auto rr=Simulate(hr,nr,pr,1000000);
      check(rr.valid && rr.meets_deadline,"deterministic random DAG " + std::to_string(round));
    }
    std::cout<<"PASS "<<cases<<" semantic checks\n";
  } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<'\n'; return 1;}
}
