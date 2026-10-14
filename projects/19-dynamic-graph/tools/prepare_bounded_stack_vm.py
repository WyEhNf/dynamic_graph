"""Prepare matched vector/bounded operand-stack builds without altering default.

All 33 VM handlers have net growth <=1. NEXT rejects size>4096 after each
handler, so 4097 slots include the observable overflow boundary. DUP pops one
before pushing two. Empty checks and exception/PC timing remain in the VM.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')

HEADER='''#pragma once
#include <cstddef>
namespace chol {
// Internal VM stack: caller checks underflow and checks overflow after every
// opcode. Capacity includes the single transient overflow value, preserving
// the original VM error PC and instruction count. No values are read unwritten.
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
'''


def main():
    OUT.mkdir(exist_ok=False)
    dest=OUT/'workspace';dest.mkdir()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={}
    for directory in ['src','include','tests','fixtures','tools']:
        shutil.copytree(ROOT/directory,dest/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copyfile(ROOT/'CMakeLists.txt',dest/'CMakeLists.txt')
    for relative in ['src/threaded_vm.cpp','CMakeLists.txt']:
        before[relative]=sha(ROOT/relative)
    path=dest/'src/threaded_vm.cpp';text=path.read_text()
    text=text.replace('#include "cholesky/prepared_vm.hpp"','#include "cholesky/prepared_vm.hpp"\n#ifdef CHOL_BOUNDED_OPERAND_STACK\n#include "cholesky/bounded_operand_stack.hpp"\n#endif')
    old='  std::vector<double> slots(metadata.slots,0.0),stack;'
    assert text.count(old)==1
    text=text.replace(old,'''  std::vector<double> slots(metadata.slots,0.0);
#ifdef CHOL_BOUNDED_OPERAND_STACK
  BoundedOperandStack stack;
#else
  std::vector<double> stack;
#endif''')
    path.write_text(text)
    (dest/'include/cholesky/bounded_operand_stack.hpp').write_text(HEADER)
    cmake=dest/'CMakeLists.txt';text=cmake.read_text()
    text+='''
# Isolated matched optimization experiment; affects only GNU threaded VM.
option(CHOL_BOUNDED_OPERAND_STACK "Use VM's proven 4097-slot operand bound" OFF)
if(CHOL_BOUNDED_OPERAND_STACK)
  if(NOT CHOL_THREADED_VM OR NOT CHOL_COMPILER_LABELS_AS_VALUES OR CHOL_THREADED_VM_FORCE_PORTABLE)
    message(FATAL_ERROR "Bounded operand stack requires actual threaded dispatch")
  endif()
  target_compile_definitions(cholesky_core PRIVATE CHOL_BOUNDED_OPERAND_STACK=1)
endif()
'''
    cmake.write_text(text)
    manifest={'default_changed':False,'base_sha256':before,'workspace':str(dest),
        'candidate_sha256':{name:sha(dest/name) for name in ['src/threaded_vm.cpp','include/cholesky/bounded_operand_stack.hpp','CMakeLists.txt']},
        'preparer_sha256':sha(Path(__file__)),'capacity_proof':'4096 max entry depth, each handler net growth <=1 including DUP, original NEXT catches 4097',
        'builds':'same source/flags except CHOL_BOUNDED_OPERAND_STACK OFF versus ON'}
    (OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest))


if __name__=='__main__':main()
