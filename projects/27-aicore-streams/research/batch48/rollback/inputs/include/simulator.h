#pragma once
#include "problem.h"
#include <string>
struct SimulationResult {
  bool valid = false;
  bool meets_deadline = false;
  int64_t makespan = 0, peak_memory = 0;
  std::string error;
  std::vector<int64_t> starts, ends; // input-vector order, not operator ID
};
SimulationResult Simulate(const HardwareInfo&, const std::vector<OperatorNode>&,
                          const SchedulePlan&, int64_t deadline_us);
