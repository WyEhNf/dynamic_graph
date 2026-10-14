#pragma once
#include <cstddef>
namespace chol {
// Internal to the threaded VM. Each opcode grows the stack by at most one;
// DUP first pops one then pushes two. NEXT rejects depth >4096 before the next
// instruction. The extra slot preserves the original overflow PC and step count.
// The VM checks before every pop/back; unwritten values are never read.
class BoundedOperandStack {
  double values_[4097];
  std::size_t count_=0;
public:
  void reserve(std::size_t) noexcept {}
  bool empty() const noexcept { return count_==0; }
  std::size_t size() const noexcept { return count_; }
  double back() const noexcept { return values_[count_-1]; }
  void pop_back() noexcept { --count_; }
  void push_back(double value) noexcept { values_[count_++]=value; }
};
}
