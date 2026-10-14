#pragma once
#include <cstddef>
#include <vector>
namespace chol {
// Two newest values stay in scalar FP64 fields. The vector owns only colder
// entries. This container performs no arithmetic or early depth/error checks:
// the interpreter retains the exact legacy checks and per-opcode overflow time.
class Tos2Stack {
  std::vector<double> lower_;
  double top_=0.0,second_=0.0;
  unsigned hot_=0;
public:
  void reserve(std::size_t capacity) { lower_.reserve(capacity); }
  bool empty()const noexcept { return hot_==0; }
  std::size_t size()const noexcept { return lower_.size()+hot_; }
  double back()const noexcept { return top_; } // caller checks empty first
  void push_back(double value) {
    if(hot_==2)lower_.push_back(second_);
    else ++hot_;
    if(hot_>1)second_=top_;
    top_=value;
  }
  void pop_back()noexcept {
    if(hot_==2) {
      top_=second_;
      if(!lower_.empty()) {second_=lower_.back();lower_.pop_back();}
      else hot_=1;
    } else hot_=0;
  }
};
}
