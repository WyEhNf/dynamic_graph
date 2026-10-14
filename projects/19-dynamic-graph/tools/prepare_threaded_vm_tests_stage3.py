"""Record the phase2 contract test origin; generate an independent phase3 suite."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
s=(p/'tests/prepared_vm_tos2_tests.cpp').read_text()
s=s.replace('#include "cholesky/tos2_stack.hpp"\n','').replace('decoded-tos2','decoded-threaded').replace('legacy/decoded/TOS2','legacy/decoded/threaded')
start=s.index('  // Independent raw IEEE754 payload')
s=s[:start]+r'''
  const auto original_contract_cases=comparisons;
  require(original_contract_cases==480,"original480 contracts changed");
  // Out-of-range table entries must preserve pop2 error ordering; unreachable
  // enum/immediate faults must remain delayed. Repeat to exercise unwinding.
  for(int code:{-1,33,999})for(unsigned count:{0,1,2})for(unsigned repeat=0;repeat<5;++repeat) {
    std::vector<I> program(count,{O::Const,0});program.push_back({static_cast<O>(code),0});
    pair(meta(program),count<2?"bytecode stack underflow":"invalid bytecode operation");
    auto dead=meta({{O::Const,0},{O::Return,0},{static_cast<O>(code),0},{O::Load,-1}});pair(dead);
  }
  // Enter every33 handler through a jump with independent original-PC budgets.
  for(int code=0;code<33;++code) {
    std::vector<I> program{{O::Const,0},{O::Const,0},{O::Const,0},{O::Jump,5},{O::Load,-1},{static_cast<O>(code),0},{O::Pop,0},{O::Const,0},{O::Return,0}};
    if(code==static_cast<int>(O::Jump)||code==static_cast<int>(O::Jz)||code==static_cast<int>(O::Jnz))program[5].argument=7;
    for(unsigned limit=0;limit<=program.size()+1;++limit) {
      const auto m=meta(program);pair(m,run(m,"legacy",limit).error,limit);
    }
  }
  // Invalid raw metadata after an early return cannot be decoded into errors.
  pair(meta({{O::Const,0},{O::Return,0},{O::Store,nan},{O::Jump,inf}}));
  // Effective backend must report fallback honestly, including exceptional exits.
  for(auto program:{std::vector<I>{{O::Const,0},{O::Return,0}},std::vector<I>{{O::Pop,0}}}) {
    const auto r=run(meta(program),"decoded-threaded");
#ifdef CHOL_HAVE_THREADED_DISPATCH
    require(r.metrics.vm_backend=="decoded-threaded","effective GNU backend absent");
#else
    require(r.metrics.vm_backend=="decoded-fallback","effective switch fallback absent");
#endif
  }
  std::cout<<"{\"passed\":true,\"opcode_coverage\":33,\"phase1_cases\":"<<phase1_cases<<",\"original_contract_cases\":"<<original_contract_cases<<",\"comparisons\":"<<comparisons<<",\"stack_limit\":4096,\"mechanism\":\"threaded vector stack\"}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''
(p/'tests/threaded_vm_tests.cpp').write_text(s)
