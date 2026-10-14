#pragma once
#include <cstdint>
#include "problem.h"
// key 0=unique evaluations,1=feasible,2=T,3=peak,4=solver microseconds,
// 5=exact duplicate plans skipped,6=generated candidate attempts,
// 7=beam child states expanded,8=maximum retained beam width,
// 9=proven lexicographic optimality certificate,10=time lower bound,
// 11=memory lower bound (conditional on T=key10 if strengthened by overlaps).
int64_t AicoreLastMetric(int key);
int64_t AicoreEvaluateMetric(const HardwareInfo&,const std::vector<OperatorNode>&,const SchedulePlan&,int);
