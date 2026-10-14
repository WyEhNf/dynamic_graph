#include "cholesky/native_workspace.hpp"
#include <algorithm>
#include <limits>
#include <new>
#include <stdexcept>
#include <utility>

namespace chol {
void NativeWorkspace::AlignedDelete::operator()(double* p)const noexcept{::operator delete[](p,std::align_val_t(64));}
NativeWorkspace::~NativeWorkspace(){close();}
NativeWorkspace::Lease NativeWorkspace::acquire(std::size_t elements){
  if(!elements||elements>std::numeric_limits<std::size_t>::max()/sizeof(double))throw std::length_error("invalid native workspace capacity");
  std::unique_lock lock(mutex_);
  const bool reused=capacity_>=elements;
  if(!reused){
    // Free before growth: no transient old+new capacity peak. A failed new
    // allocation leaves an empty valid owner; no previous result is stored here.
    buffer_.reset();capacity_=0;
    buffer_.reset(static_cast<double*>(::operator new[](elements*sizeof(double),std::align_val_t(64))));
    capacity_=elements;peak_capacity_=std::max(peak_capacity_,capacity_);++allocations_;
  }else ++reuses_;
  return Lease(std::move(lock),buffer_.get(),capacity_,reused);
}
void NativeWorkspace::close(){std::lock_guard lock(mutex_);buffer_.reset();capacity_=0;}
std::size_t NativeWorkspace::peak_capacity_bytes()const{std::lock_guard lock(mutex_);return peak_capacity_*sizeof(double);}
std::uint64_t NativeWorkspace::allocations()const{std::lock_guard lock(mutex_);return allocations_;}
std::uint64_t NativeWorkspace::reuses()const{std::lock_guard lock(mutex_);return reuses_;}
}
