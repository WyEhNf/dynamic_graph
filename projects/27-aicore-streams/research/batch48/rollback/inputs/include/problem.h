#pragma once
#include <cstdint>
#include <vector>
// Transcribed from the public statement on 2026-10-10; replace with organizer header when available.
enum class CoreType : int { AIC = 0, AIV = 1 };
struct HardwareInfo {
  int aic_core_num, aiv_core_num, stream_num;
  int64_t memory_limit, event_record_time, event_wait_time;
};
struct OperatorNode {
  int id;
  CoreType core_type;
  int core_num;
  int64_t exec_time, workspace_memory, output_memory;
  std::vector<int> inputs;
};
struct StreamTask { int op_id; std::vector<int> wait_before; int record_after; };
struct StreamPlan { std::vector<StreamTask> tasks; };
struct SchedulePlan { std::vector<StreamPlan> streams; };
SchedulePlan ScheduleCvGraph(const HardwareInfo&, const std::vector<OperatorNode>&, int64_t deadline_us);
