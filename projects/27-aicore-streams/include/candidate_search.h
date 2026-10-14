#pragma once
#include "simulator.h"
#include <optional>
#include <vector>
struct CandidateSearchResult {
  std::optional<SchedulePlan> plan;
  SimulationResult simulation;
  std::vector<SimulationResult> attempts;
};
// Local framework wrapper. Only returns a plan independently verified as feasible.
CandidateSearchResult SelectFeasibleCandidate(const HardwareInfo&,const std::vector<OperatorNode>&,int64_t);
