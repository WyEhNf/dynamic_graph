#include "candidate_search.h"
#include <exception>
CandidateSearchResult SelectFeasibleCandidate(const HardwareInfo& hw,const std::vector<OperatorNode>& nodes,int64_t deadline) {
  CandidateSearchResult result;
  try {
    auto plan=ScheduleCvGraph(hw,nodes,deadline);
    auto evaluated=Simulate(hw,nodes,plan,deadline);
    result.attempts.push_back(evaluated);
    if(evaluated.valid && evaluated.meets_deadline) {result.plan=std::move(plan);result.simulation=std::move(evaluated);}
    else result.simulation.error="Submission/local simulator disagreement or infeasible plan";
  } catch(const std::exception& e) {result.simulation.error=e.what();}
  return result;
}
