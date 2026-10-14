#include "cholesky/execution_context.hpp"
#include <cfenv>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <thread>
#include <vector>
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace chol {
struct ExecutionContext::Impl {
  mutable std::mutex owner_mutex;
  std::mutex mutex;
  std::condition_variable begin,finished;
  std::vector<std::jthread> workers;
  bool stopping=false;
  std::uint64_t epoch=0,created=0,jobs=0;
  unsigned pending=0;
  const std::function<void()>* job=nullptr;
  std::exception_ptr error;

  void worker() {
    // Restore the environment a fresh worker starts with; a prior callback's
    // rounding, exceptions, FTZ, or DAZ must not leak into the next matrix.
    std::fenv_t initial_environment;
    std::fegetenv(&initial_environment);
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
    const auto initial_mxcsr=_mm_getcsr();
#endif
    std::uint64_t seen=0;
    std::unique_lock lock(mutex);
    for(;;) {
      begin.wait(lock,[&]{return stopping||epoch!=seen;});
      if(stopping)return;
      seen=epoch;const auto* current=job;
      lock.unlock();
      std::exception_ptr local_error;
      try {
        std::fesetenv(&initial_environment);
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
        // Some CRT fenv implementations omit the nonstandard FTZ/DAZ bits.
        // Avoid a redundant write when fesetenv already restored all bits.
        if(_mm_getcsr()!=initial_mxcsr)_mm_setcsr(initial_mxcsr);
#endif
        (*current)();
      }catch(...) {local_error=std::current_exception();}
      current=nullptr;
      lock.lock();
      if(local_error&&!error)error=local_error;
      if(--pending==0)finished.notify_one();
    }
  }
  // Called only with owner_mutex held and no active job.
  void stop_workers() {
    {std::lock_guard lock(mutex);stopping=true;}
    begin.notify_all();workers.clear();
    {std::lock_guard lock(mutex);stopping=false;epoch=0;job=nullptr;}
  }
  void configure(unsigned count) {
    if(workers.size()==count)return;
    stop_workers();workers.reserve(count);
    try {
      for(unsigned i=0;i<count;++i) {workers.emplace_back([this]{worker();});++created;}
    }catch(...) {stop_workers();throw;}
  }
  void run(unsigned count,const std::function<void()>& work) {
    std::lock_guard owner(owner_mutex);
    if(count<=1){work();return;}
    configure(count);
    std::unique_lock lock(mutex);
    pending=count;job=&work;error=nullptr;++epoch;++jobs;
    begin.notify_all();
    finished.wait(lock,[&]{return pending==0;});
    job=nullptr;auto failure=error;error=nullptr;
    lock.unlock();
    if(failure)std::rethrow_exception(failure);
  }
};
ExecutionContext::ExecutionContext():impl_(std::make_unique<Impl>()){}
ExecutionContext::~ExecutionContext(){close();}
void ExecutionContext::run_workers(unsigned count,const std::function<void()>& work){impl_->run(count,work);}
void ExecutionContext::close(){std::lock_guard owner(impl_->owner_mutex);impl_->stop_workers();}
std::uint64_t ExecutionContext::workers_created()const{std::lock_guard owner(impl_->owner_mutex);return impl_->created;}
std::uint64_t ExecutionContext::jobs_dispatched()const{std::lock_guard owner(impl_->owner_mutex);return impl_->jobs;}
}
