#pragma once
#include <cstdint>
#include <functional>
#include <memory>

namespace chol {
// Explicit stream-owned worker lifetime. Jobs are synchronous: no callable,
// matrix, or graph reference remains active when run_workers returns.
// Concurrent submissions to one context are serialized; separate contexts are
// independent. Constructing a context creates no worker threads.
// Each worker restores its thread-start floating environment before each job.
// The CLI keeps its default environment throughout a stream. On this Windows
// CRT fresh threads likewise start in the default environment, independently
// of the submitting thread. A callback must not call run_workers/close on its
// own context (submissions are non-reentrant).
class ExecutionContext {
  struct Impl;
  std::unique_ptr<Impl> impl_;
public:
  ExecutionContext();
  ~ExecutionContext();
  ExecutionContext(const ExecutionContext&)=delete;
  ExecutionContext& operator=(const ExecutionContext&)=delete;
  void run_workers(unsigned count,const std::function<void()>& work);
  void close();
  std::uint64_t workers_created() const;
  std::uint64_t jobs_dispatched() const;
};
}
