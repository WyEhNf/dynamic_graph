#pragma once
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <utility>

namespace chol {
// Explicit allocation cache, independent of worker execution context.
// Keep this owner alive until all calls/leases finish. Acquisitions and close
// on the same owner serialize; they are not reentrant within an active lease.
class NativeWorkspace {
  struct AlignedDelete { void operator()(double*)const noexcept; };
  const bool trim_on_structured_;
  mutable std::mutex mutex_;
  std::unique_ptr<double[],AlignedDelete> buffer_;
  std::size_t capacity_=0,peak_capacity_=0;
  std::uint64_t allocations_=0,reuses_=0;
public:
  class Lease {
    friend class NativeWorkspace;
    std::unique_lock<std::mutex> lock_;
    double* data_;
    std::size_t capacity_;
    bool reused_;
    Lease(std::unique_lock<std::mutex> lock,double* data,std::size_t capacity,bool reused)
      :lock_(std::move(lock)),data_(data),capacity_(capacity),reused_(reused){}
  public:
    Lease(Lease&&)=default;
    Lease& operator=(Lease&&)=delete;
    Lease(const Lease&)=delete;
    Lease& operator=(const Lease&)=delete;
    double* data()const noexcept{return data_;}
    std::size_t capacity_elements()const noexcept{return capacity_;}
    bool reused()const noexcept{return reused_;}
  };
  // Immutable per-owner opt-in; existing session owners retain their allocation.
  NativeWorkspace() noexcept : NativeWorkspace(false) {}
  explicit NativeWorkspace(bool trim_on_structured) noexcept : trim_on_structured_(trim_on_structured) {}
  bool trim_on_structured()const noexcept{return trim_on_structured_;}
  ~NativeWorkspace();
  NativeWorkspace(const NativeWorkspace&)=delete;
  NativeWorkspace& operator=(const NativeWorkspace&)=delete;
  Lease acquire(std::size_t elements);
  void close();
  std::size_t peak_capacity_bytes()const;
  std::uint64_t allocations()const;
  std::uint64_t reuses()const;
};
}
