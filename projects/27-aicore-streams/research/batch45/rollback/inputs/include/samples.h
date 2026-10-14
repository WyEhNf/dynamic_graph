#pragma once
#include "problem.h"
inline HardwareInfo SampleHardware() {return {16,12,3,400,2,3};}
inline std::vector<OperatorNode> SampleGraph() {
  return {{0,CoreType::AIV,4,40,60,40,{}}, {1,CoreType::AIV,6,50,70,50,{0}},
          {2,CoreType::AIC,12,120,160,80,{1}}, {3,CoreType::AIC,6,70,90,20,{2}},
          {4,CoreType::AIC,8,90,100,30,{2}}, {5,CoreType::AIV,8,60,80,10,{3,4}}};
}
inline SchedulePlan SamplePlan() {
  return {{{{{0,{},-1},{1,{},-1},{2,{},0},{4,{},-1},{5,{1},-1}}},
           {{{3,{0},1}}}}};
}
