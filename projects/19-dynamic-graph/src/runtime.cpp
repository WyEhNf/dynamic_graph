#include "cholesky/runtime.hpp"
#include "native_input_scan.hpp"
#include "metadata_number.hpp"
#ifdef CHOL_PROVED_VM_BUDGET
#include "cholesky/vm_step_bound.hpp"
#endif
#ifdef CHOL_HAVE_THREADED_DISPATCH
#include "cholesky/threaded_vm.hpp"
#endif
#ifdef CHOL_PREPARED_VM
#include "cholesky/prepared_vm.hpp"
#include "cholesky/tos2_stack.hpp"
#endif
#ifdef CHOL_HAVE_AVX512_KERNEL
#include "cholesky/simd_dispatch.hpp"
#endif
#ifdef CHOL_COMPRESSED_METADATA
#include "cholesky/compressed_metadata.hpp"
#endif
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cfenv>
#if defined(CHOL_AUTO_SMALL_STAGE_SERIAL) && (defined(__SSE__) || defined(_M_X64) || (defined(_M_IX86_FP) && _M_IX86_FP >= 1))
#include <xmmintrin.h>
#endif
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <functional>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <type_traits>

namespace chol {
namespace detail {
struct PreparedVMState {
  const Metadata metadata;
  explicit PreparedVMState(Metadata source):metadata(std::move(source)){}
#ifdef CHOL_PREPARED_VM
  mutable std::once_flag initialized;
  mutable std::vector<DecodedInstruction> decoded;
  const std::vector<DecodedInstruction>& plan(RunMetrics* metrics) const {
    bool built=false;
    double prepare_ms=0;
    std::call_once(initialized,[&] {
      const auto start=std::chrono::steady_clock::now();
      decoded=decode_vm_program(metadata);
#if defined(CHOL_PROVED_OPERAND_STACK) && defined(CHOL_HAVE_THREADED_DISPATCH)
      if(!decoded.empty())decoded.front().stack_proved_=prove_vm_stack(decoded);
#endif
      prepare_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
      built=true;
    });
    if(metrics) {
      metrics->vm_prepare_ms=prepare_ms;
      metrics->vm_plan_builds=built?1:0;
      metrics->vm_plan_reuses=built?0:1;
    }
    return decoded;
  }
#endif
};
}
PreparedVM::PreparedVM(Metadata metadata):state_(std::make_unique<detail::PreparedVMState>(std::move(metadata))){}
PreparedVM::~PreparedVM()=default;
PreparedVM::PreparedVM(PreparedVM&&) noexcept=default;
PreparedVM& PreparedVM::operator=(PreparedVM&&) noexcept=default;
Matrix tiled_cholesky(const Matrix& input, Options options, bool fused, Matrix* owned_input);
bool try_structured_factor(const Matrix&,Matrix&,Options,bool);
#if defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
bool all_finite_avx2(const double*,std::size_t);
#endif
namespace {
const std::map<std::string, Opcode> opcodes{
 {"CONST",Opcode::Const},{"LOAD",Opcode::Load},{"STORE",Opcode::Store},{"UNINIT",Opcode::Uninit},
 {"READ",Opcode::Read},{"WRITE",Opcode::Write},{"DUP",Opcode::Dup},{"POP",Opcode::Pop},
 {"ADD",Opcode::Add},{"SUB",Opcode::Sub},{"MUL",Opcode::Mul},{"DIV",Opcode::Div},
 {"IDIV",Opcode::IntDiv},{"MOD",Opcode::Mod},{"NEG",Opcode::Neg},{"NOT",Opcode::Not},
 {"BOOL",Opcode::Bool},{"TRUNC",Opcode::Trunc},{"SQRT",Opcode::Sqrt},{"ABS",Opcode::Abs},
 {"MIN",Opcode::Min},{"MAX",Opcode::Max},{"FMA",Opcode::Fma},{"LT",Opcode::Lt},{"LE",Opcode::Le},
 {"GT",Opcode::Gt},{"GE",Opcode::Ge},{"EQ",Opcode::Eq},{"NE",Opcode::Ne},
 {"JUMP",Opcode::Jump},{"JZ",Opcode::Jz},{"JNZ",Opcode::Jnz},{"RETURN",Opcode::Return}};
// Explicit wire order; never derive IDs from enum values or map iteration.
constexpr std::array<Opcode,33> wire_opcodes{
 Opcode::Const,Opcode::Load,Opcode::Store,Opcode::Uninit,Opcode::Read,Opcode::Write,Opcode::Dup,Opcode::Pop,
 Opcode::Add,Opcode::Sub,Opcode::Mul,Opcode::Div,Opcode::IntDiv,Opcode::Mod,Opcode::Neg,Opcode::Not,
 Opcode::Bool,Opcode::Trunc,Opcode::Sqrt,Opcode::Abs,Opcode::Min,Opcode::Max,Opcode::Fma,
 Opcode::Lt,Opcode::Le,Opcode::Gt,Opcode::Ge,Opcode::Eq,Opcode::Ne,Opcode::Jump,Opcode::Jz,Opcode::Jnz,Opcode::Return};
constexpr std::string_view wire_codes="0123456789ABCDEFGHIJKLMNOPQRSTUVW";

std::size_t checked_index(double value, std::size_t bound, const char* description) {
  if (!std::isfinite(value) || value < 0 || std::trunc(value) != value || value >= static_cast<double>(bound))
    throw std::runtime_error(std::string("invalid ") + description);
  return static_cast<std::size_t>(value);
}

#ifdef CHOL_AUTO_SMALL_STAGE_SERIAL
bool default_stage_fp_environment() {
  if(std::fegetround()!=FE_TONEAREST)return false;
#if defined(__SSE__) || defined(_M_X64) || (defined(_M_IX86_FP) && _M_IX86_FP >= 1)
  // SSE rounding may be changed independently from the x87 environment.
  // Keep fresh-worker behavior for non-nearest, flush-to-zero, or DAZ callers.
  return (_mm_getcsr()&0xE040u)==0;
#else
  return true;
#endif
}
#endif

// Workers persist throughout a complete matrix; each publication is a DAG stage.
// A column may start only after the previous column's row tasks have retired.
class StagePool {
  std::vector<std::jthread> workers_;
  std::mutex mutex_;
  std::condition_variable work_, done_;
  std::function<void(std::size_t, std::size_t)> task_;
  std::atomic<std::size_t> next_{0};
  std::size_t end_ = 0, epoch_ = 0, pending_ = 0;
  bool stopping_ = false;
public:
  explicit StagePool(unsigned threads) {
    for (unsigned index = 0; index < threads; ++index) workers_.emplace_back([this] {
      std::size_t seen = 0;
      for (;;) {
        std::unique_lock lock(mutex_);
        work_.wait(lock, [&] { return stopping_ || epoch_ != seen; });
        if (stopping_) return;
        seen = epoch_;
        const auto end = end_;
        lock.unlock();
        for (;;) {
          const auto first = next_.fetch_add(16, std::memory_order_relaxed);
          if (first >= end) break;
          task_(first, std::min(first + 16, end));
        }
        lock.lock();
        if (--pending_ == 0) done_.notify_one();
      }
    });
  }
  ~StagePool() {
    { std::lock_guard lock(mutex_); stopping_ = true; }
    work_.notify_all();
    // Join before synchronization objects are destroyed (reverse member order).
    workers_.clear();
  }
  void run(std::size_t first, std::size_t end, std::function<void(std::size_t, std::size_t)> task) {
    std::unique_lock lock(mutex_);
    task_ = std::move(task); next_.store(first, std::memory_order_relaxed);
    end_ = end; pending_ = workers_.size(); ++epoch_;
    work_.notify_all();
    done_.wait(lock, [&] { return pending_ == 0; });
  }
};

bool diagonal_factor(const Matrix& input, Matrix& out) {
  // A general data-dependent specialization, never a shape/dataset lookup.
  // Source-order reductions of all-zero off-diagonal values remain +0. The
  // input zero's sign is preserved by subtraction of +0 and positive division.
  const std::size_t n = input.n;
  for (std::size_t row = 1; row < n; ++row)
    for (std::size_t col = 0; col < row; ++col)
      if (input.values[row*n+col] != 0.0) return false;
  for (std::size_t row = 0; row < n; ++row) {
    if (!(input.values[row*n+row] > 0.0)) throw std::runtime_error("matrix is not positive definite");
    out.values[row*n+row] = std::sqrt(input.values[row*n+row]);
    for (std::size_t col = 0; col < row; ++col) out.values[row*n+col] = input.values[row*n+col];
  }
  return true;
}

Matrix scalar_cholesky(const Matrix& input, Options options) {
  const std::size_t n = input.n;
  Matrix out{input.n, std::vector<double>(n*n, 0.0)};
  if (try_structured_factor(input,out,options,false)) return out;
  const unsigned threads = std::min<unsigned>(std::max(1u, options.threads), static_cast<unsigned>(n));
  std::unique_ptr<StagePool> pool;
  if (options.parallel && threads > 1 && n >= 64) pool = std::make_unique<StagePool>(threads);
  if(options.metrics)options.metrics->worker_threads=pool?threads:1;
  for (std::size_t j = 0; j < n; ++j) {
    double sum = 0.0;
    for (std::size_t k = 0; k < j; ++k) sum += out.values[j*n+k]*out.values[j*n+k];
    const double pivot = input.values[j*n+j] - sum;
    if (!(pivot > 0.0) || !std::isfinite(pivot))
      throw std::runtime_error("matrix is not positive definite at pivot " + std::to_string(j));
    out.values[j*n+j] = std::sqrt(pivot);
    auto rows = [&](std::size_t first, std::size_t last) {
      for (std::size_t i = first; i < last; ++i) {
        double dot = 0.0;
        for (std::size_t k = 0; k < j; ++k) dot += out.values[i*n+k]*out.values[j*n+k];
        out.values[i*n+j] = (input.values[i*n+j] - dot)/out.values[j*n+j];
      }
    };
    if (pool && n-j-1 >= 32) pool->run(j+1, n, rows);
    else rows(j+1, n);
  }
  return out;
}

Matrix rightlooking_cholesky(const Matrix& input, Options options, bool fused) {
  const std::size_t n = input.n;
  Matrix out{input.n, std::vector<double>(n*n, 0.0)};
  if (try_structured_factor(input,out,options,fused)) return out;
  const unsigned threads = std::min<unsigned>(std::max(1u, options.threads), static_cast<unsigned>(n));
  std::unique_ptr<StagePool> pool;
  if (options.parallel && threads > 1 && n >= 64) pool = std::make_unique<StagePool>(threads);
  if(options.metrics)options.metrics->worker_threads=pool?threads:1;
  for (std::size_t i = 0; i < n; ++i) {
    const double pivot = input.values[i*n+i] - out.values[i*n+i];
    if (!(pivot > 0.0) || !std::isfinite(pivot)) throw std::runtime_error("matrix is not positive definite at pivot " + std::to_string(i));
    out.values[i*n+i] = std::sqrt(pivot);
    auto divide = [&](std::size_t first, std::size_t last) {
      for (std::size_t j = first; j < last; ++j)
        out.values[j*n+i] = (input.values[j*n+i] - out.values[j*n+i])/out.values[i*n+i];
    };
    auto update = [&](std::size_t first, std::size_t last) {
      for (std::size_t j = first; j < last; ++j) {
        const auto factor = out.values[j*n+i];
        for (std::size_t k = i+1; k <= j; ++k) {
          if (fused) out.values[j*n+k] = std::fma(factor, out.values[k*n+i], out.values[j*n+k]);
          else out.values[j*n+k] = factor*out.values[k*n+i] + out.values[j*n+k];
        }
      }
    };
    if (pool && n-i-1 >= 32) {
      // Every division is ready after the diagonal. Every row update is ready
      // after this column's divisions. Rows write disjoint accumulator ranges.
      pool->run(i+1, n, divide); pool->run(i+1, n, update);
    } else { divide(i+1,n); update(i+1,n); }
  }
  return out;
}

template<bool Prepared=false,bool Cached=false> Matrix run_program(const Matrix& input, const Metadata& metadata, Options options, const detail::PreparedVMState* session=nullptr) {
#ifdef CHOL_PREPARED_VM
  std::vector<DecodedInstruction> owned_plan;
  const std::vector<DecodedInstruction>* shared_plan=nullptr;
  if constexpr(Prepared) {
    if(session) shared_plan=&session->plan(options.metrics);
    else {
      const auto prepare_start=std::chrono::steady_clock::now();
      owned_plan=decode_vm_program(metadata);
      if(options.metrics) {
        options.metrics->vm_prepare_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-prepare_start).count();
        options.metrics->vm_plan_builds=1;
      }
    }
  }
  const auto& decoded=shared_plan?*shared_plan:owned_plan;
  if constexpr(Prepared) {
    if(options.metrics)options.metrics->vm_plan_bytes=decoded.capacity()*sizeof(DecodedInstruction);
  }
#endif
  if(options.metrics)options.metrics->vm_backend=Cached?"decoded-tos2":Prepared?"decoded":"legacy";
  Matrix output{input.n, std::vector<double>(input.values.size(), 0.0)};
  std::vector<double> slots(metadata.slots, 0.0);
#ifdef CHOL_PREPARED_VM
  std::conditional_t<Cached,Tos2Stack,std::vector<double>> stack;
#else
  std::vector<double> stack;
#endif
  std::vector<bool> initialized(metadata.slots, false);
  slots[metadata.shape_slot] = input.n; initialized[metadata.shape_slot] = true;
  if (metadata.block_slot >= 0) {
    slots[metadata.block_slot] = options.block_size; initialized[metadata.block_slot] = true;
  }
  stack.reserve(64);
  auto pop = [&] {
    if (stack.empty()) throw std::runtime_error("bytecode stack underflow");
    const auto value = stack.back(); stack.pop_back(); return value;
  };
  std::size_t pc = 0;
  std::size_t last_pc=0;
  std::uint64_t steps = 0;
  struct FinalSteps {RunMetrics* metrics;std::uint64_t& value;std::size_t& pc;~FinalSteps(){if(metrics){metrics->vm_steps=value;metrics->vm_last_pc=pc;}}} final_steps{options.metrics,steps,last_pc};
  while (pc < metadata.program.size()) {
    last_pc=pc;
    if (++steps > options.vm_step_limit) throw std::runtime_error("VM instruction limit exceeded");
    const auto instruction=[&]() {
#ifdef CHOL_PREPARED_VM
      if constexpr(Prepared)return Instruction{decoded[pc].opcode,decoded[pc].argument()};
#endif
      return metadata.program[pc];
    }();++pc;
    const auto op = instruction.opcode;
    const auto arg = instruction.argument;
    auto immediate_index=[&](std::size_t bound,const char* description) {
#ifdef CHOL_PREPARED_VM
      if constexpr(Prepared) {
        const auto& current=decoded[pc-1];
        if(!current.valid_index)throw std::runtime_error(std::string("invalid ")+description);
        return current.index();
      }
#endif
      return checked_index(arg,bound,description);
    };
    switch (op) {
      case Opcode::Const: stack.push_back(arg); break;
      case Opcode::Load: {
        const auto slot = immediate_index(slots.size(), "slot");
        if (!initialized[slot]) throw std::runtime_error("read of uninitialized scalar");
        stack.push_back(slots[slot]); break;
      }
      case Opcode::Store: { const auto slot = immediate_index(slots.size(), "slot"); slots[slot] = pop(); initialized[slot] = true; break; }
      case Opcode::Uninit: initialized[immediate_index(slots.size(), "slot")] = false; break;
      case Opcode::Read: {
        const auto index = checked_index(pop(), input.values.size(), "array index");
        stack.push_back(arg == 0 ? input.values[index] : output.values[index]); break;
      }
      case Opcode::Write: {
        const auto value = pop(); const auto index = checked_index(pop(), output.values.size(), "array index");
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result produced by source program");
        output.values[index] = value; break;
      }
      case Opcode::Dup: { const auto value = pop(); stack.push_back(value); stack.push_back(value); break; }
      case Opcode::Pop: (void)pop(); break;
      case Opcode::Jump: pc = immediate_index(metadata.program.size(), "jump target"); break;
      case Opcode::Jz: { if (pop() == 0) pc = immediate_index(metadata.program.size(), "jump target"); break; }
      case Opcode::Jnz: { if (pop() != 0) pc = immediate_index(metadata.program.size(), "jump target"); break; }
      case Opcode::Return: {
        if (pop() != 0) throw std::runtime_error("source function returned a nonzero status");
        if (!stack.empty()) throw std::runtime_error("unbalanced bytecode stack at return");
        return output;
      }
      case Opcode::Neg: stack.push_back(-pop()); break;
      case Opcode::Not: stack.push_back(pop() == 0); break;
      case Opcode::Bool: stack.push_back(pop() != 0); break;
      case Opcode::Trunc: {
        const auto value=std::trunc(pop());
        if(!std::isfinite(value)||value<std::numeric_limits<std::int32_t>::min()||value>std::numeric_limits<std::int32_t>::max())
          throw std::runtime_error("C int conversion outside representable int32 range");
        stack.push_back(value==0.0?0.0:value);break;
      }
      case Opcode::Sqrt: stack.push_back(std::sqrt(pop())); break;
      case Opcode::Abs: stack.push_back(std::fabs(pop())); break;
      case Opcode::Fma: { const auto c = pop(), b = pop(), a = pop(); stack.push_back(std::fma(a,b,c)); break; }
      default: {
        const auto right = pop(), left = pop();
        double value = 0;
        switch (op) {
          case Opcode::Add: value = left+right; break;
          case Opcode::Sub: value = left-right; break;
          case Opcode::Mul: value = left*right; break;
          case Opcode::Div: value = left/right; break;
          case Opcode::IntDiv:
          case Opcode::Mod:
            if(right==0||(left==std::numeric_limits<std::int32_t>::min()&&right==-1))throw std::runtime_error("undefined C integer division/remainder");
            value=op==Opcode::IntDiv?std::trunc(left/right):std::fmod(left,right);
            if(value==0.0)value=0.0;
            break;
          case Opcode::Min: value = std::fmin(left,right); break;
          case Opcode::Max: value = std::fmax(left,right); break;
          case Opcode::Lt: value = left<right; break;
          case Opcode::Le: value = left<=right; break;
          case Opcode::Gt: value = left>right; break;
          case Opcode::Ge: value = left>=right; break;
          case Opcode::Eq: value = left==right; break;
          case Opcode::Ne: value = left!=right; break;
          default: throw std::runtime_error("invalid bytecode operation");
        }
        stack.push_back(value); break;
      }
    }
    if (stack.size() > 4096) throw std::runtime_error("bytecode stack overflow");
  }
  throw std::runtime_error("program ended without return");
}
}

bool try_diagonal_factor(const Matrix& input, Matrix& output) {
  return diagonal_factor(input, output);
}

Metadata read_metadata(const std::string& path) {
  std::ifstream plain(path);
  if (!plain) throw std::runtime_error("cannot open metadata: " + path);
#ifdef CHOL_COMPRESSED_METADATA
  const auto decoded=read_compressed_metadata(path);
  std::istringstream decoded_stream(decoded.value_or(std::string{}));
  std::istream& in=decoded?static_cast<std::istream&>(decoded_stream):static_cast<std::istream&>(plain);
#else
  std::istream& in=plain;
#endif
  std::string line; std::getline(in, line);
  if (!line.empty() && line.back() == '\r') line.pop_back();
  const bool legacy = line == "DYNCHOL 1";
  const bool compact_wire = line == "DYNCHOL 3";
  if (!legacy && !compact_wire && line != "DYNCHOL 2") throw std::runtime_error("unsupported metadata schema");
  std::map<std::string, std::string> fields;
  Metadata metadata;
  bool program = false;
  while (std::getline(in, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line == "PROGRAM" && !legacy) { if (program) throw std::runtime_error("duplicate PROGRAM"); program = true; continue; }
    if (program) {
      Opcode opcode;
      if(compact_wire) {
        if(line.empty())throw std::runtime_error("malformed compact instruction");
        const auto id=wire_codes.find(line[0]);
        if(id==std::string_view::npos||(line.size()>1&&line[1]!=' '))throw std::runtime_error("malformed compact opcode");
        opcode=wire_opcodes[id];
        const bool required=opcode==Opcode::Const||opcode==Opcode::Load||opcode==Opcode::Store||opcode==Opcode::Uninit||opcode==Opcode::Read||opcode==Opcode::Write||opcode==Opcode::Jump||opcode==Opcode::Jz||opcode==Opcode::Jnz;
        // Only canonical operand-free lines bypass the old stream parser.
        // Noncanonical lines retain its existing rejection precedence/messages.
        if(!required&&line.size()==1) {
          if(metadata.program.size()>=100000)throw std::runtime_error("metadata instruction limit exceeded");
          metadata.program.push_back({opcode,0});continue;
        }
      }
      std::istringstream row(compact_wire?line.substr(1):line);std::string name,extra;double argument=0;
      if(!compact_wire) {
        if(!(row>>name)||!opcodes.contains(name))throw std::runtime_error("malformed bytecode instruction");
        opcode=opcodes.at(name);
      }
      const bool required=opcode==Opcode::Const||opcode==Opcode::Load||opcode==Opcode::Store||opcode==Opcode::Uninit||opcode==Opcode::Read||opcode==Opcode::Write||opcode==Opcode::Jump||opcode==Opcode::Jz||opcode==Opcode::Jnz;
      if(compact_wire&&required&&(line.size()<3||!detail::canonical_metadata_number(std::string_view(line).substr(2))))throw std::runtime_error("noncanonical compact numeric argument");
      if(row>>argument) {
        if(row>>extra||!std::isfinite(argument)||(!required&&(compact_wire||argument!=0)))throw std::runtime_error("malformed bytecode argument");
      } else if(!row.eof()||required)throw std::runtime_error("missing or malformed bytecode argument");
      if(compact_wire&&((required&&line.size()<3)||(!required&&line.size()!=1)))throw std::runtime_error("noncanonical compact instruction");
      if (metadata.program.size() >= 100000) throw std::runtime_error("metadata instruction limit exceeded");
      metadata.program.push_back({opcode, argument}); continue;
    }
    const auto split = line.find('=');
    if (split == std::string::npos || split == 0 || split+1 == line.size() || !fields.emplace(line.substr(0,split), line.substr(split+1)).second)
      throw std::runtime_error("malformed or duplicate metadata field");
  }
  auto field = [&](const std::string& key) -> std::string {
    if (!fields.contains(key)) throw std::runtime_error("missing metadata field: " + key);
    return fields.at(key);
  };
  if(compact_wire) {
    if(field("bytecode_encoding")!="base36_opcode_v1")throw std::runtime_error("unsupported compact bytecode encoding");
  } else if(fields.contains("bytecode_encoding"))throw std::runtime_error("encoding field requires schema 3");
  metadata.algorithm = field("algorithm"); metadata.arithmetic = field("arithmetic"); metadata.dependencies = field("dependencies");
  if (legacy) {
    if (metadata.algorithm != "cholesky_column_v1" || metadata.arithmetic != "fp64_ascending_k_no_fma" || metadata.dependencies != "column_barrier_diagonal_then_rows")
      throw std::runtime_error("unsupported legacy semantics");
    return metadata;
  }
  if (metadata.algorithm != "ast_vm_v2" || metadata.arithmetic != "fp64_source_order_no_implicit_fma" || metadata.dependencies != "source_control_flow" || !program || metadata.program.empty())
    throw std::runtime_error("unsupported source program semantics");
  auto integer = [&](const std::string& key) {
    const auto text = field(key); std::size_t used = 0; const auto number = std::stoll(text, &used);
    if (used != text.size()) throw std::runtime_error("invalid integer field: " + key);
    return number;
  };
  const auto slots = integer("slots"), shape = integer("shape_slot"), block = integer("block_slot");
  if (slots < 1 || slots > 4096 || shape < 0 || shape >= slots || block < -1 || block >= slots || block == shape)
    throw std::runtime_error("invalid program slots");
  metadata.slots = static_cast<std::size_t>(slots); metadata.shape_slot = static_cast<std::size_t>(shape); metadata.block_slot = static_cast<int>(block);
  metadata.optimized = field("optimized");
  if (metadata.optimized != "none" && metadata.optimized != "scalar_cholesky_column_dag" && metadata.optimized != "rightlooking_cholesky_column_dag" && metadata.optimized != "rightlooking_cholesky_column_dag_fma") throw std::runtime_error("unknown optimized semantics");
  for (const auto instruction : metadata.program) {
    switch (instruction.opcode) {
      case Opcode::Load: case Opcode::Store: case Opcode::Uninit: (void)checked_index(instruction.argument, metadata.slots, "slot"); break;
      case Opcode::Jump: case Opcode::Jz: case Opcode::Jnz: (void)checked_index(instruction.argument, metadata.program.size(), "jump target"); break;
      case Opcode::Read: if (instruction.argument != 0 && instruction.argument != 1) throw std::runtime_error("invalid read array"); break;
      case Opcode::Write: if (instruction.argument != 1) throw std::runtime_error("input writes forbidden"); break;
      default: break;
    }
  }
  return metadata;
}

static Matrix execute_impl(const Matrix& input, const Metadata& metadata, Options options, Matrix* owned_input, const detail::PreparedVMState* session=nullptr) {
  const std::size_t n = input.n;
  if (n < 3 || n > 10000 || input.values.size() != n*n) throw std::runtime_error("matrix dimensions out of supported range");
  if (options.threads == 0 || options.threads > 256 || options.block_size == 0 || options.block_size > 10000)
    throw std::runtime_error("invalid runtime options");
  if (options.tile_size > 1024 ||
      (options.vm_backend!="auto"&&options.vm_backend!="legacy"
#ifdef CHOL_PREPARED_VM
       &&options.vm_backend!="decoded"&&options.vm_backend!="decoded-tos2"
#endif
#ifdef CHOL_THREADED_VM
       &&options.vm_backend!="decoded-threaded"
#endif
      ) ||
      (options.engine != "auto" && options.engine != "vm" && options.engine != "stage" && options.engine != "tiled") ||
      (options.simd!="auto"&&options.simd!="portable"
#ifdef CHOL_HAVE_AVX512_KERNEL
       &&options.simd!="avx2"&&options.simd!="avx512"
#endif
      ) || (options.ready_queue!="heap"&&options.ready_queue!="bucket") ||
      (options.structure!="auto"&&options.structure!="dense") || options.band_limit>1024)
    throw std::runtime_error("invalid execution engine or tile size");
  if (options.metrics) *options.metrics = {};
  if(options.vm_budget_mode!="fixed"&&options.vm_budget_mode!="proved")
    throw std::runtime_error("VM budget mode must be fixed or proved");
  if(options.vm_budget_mode=="proved") {
#ifndef CHOL_PROVED_VM_BUDGET
    throw std::runtime_error("proved VM budget is disabled in this build");
#else
    if(options.vm_step_limit_explicit||options.vm_step_limit!=1000000000ull)
      throw std::runtime_error("proved VM budget cannot combine with an explicit VM step limit");
#endif
  }
  if(options.metrics) {
    options.metrics->vm_budget_mode=options.vm_budget_mode;
    options.metrics->vm_budget_proof_status="not-run";
  }
#ifdef CHOL_HAVE_AVX512_KERNEL
  if(options.simd=="avx512"&&!usable_avx512(detect_simd_capabilities()))throw std::runtime_error("requested avx512 requires CPU AVX512F/AVX2/FMA and enabled OS ZMM/opmask state");
#endif
  const auto validation_start=std::chrono::steady_clock::now();
  bool scan_simd=false;
  const NativeInputScan* native_scan_ptr=nullptr;
#if defined(CHOL_FUSED_FINITE_BAND_SCAN) && defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
  NativeInputScan native_scan;
#endif
#if defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
  scan_simd=options.simd!="portable"&&__builtin_cpu_supports("avx2")&&__builtin_cpu_supports("fma");
  if(scan_simd) {
#ifdef CHOL_FUSED_FINITE_BAND_SCAN
    // Read only selection tags here. Metadata validation and its errors remain
    // after full input finiteness, exactly as in the unfused entry path.
    const bool recognized_for_scan=metadata.optimized=="scalar_cholesky_column_dag"||
      metadata.optimized=="rightlooking_cholesky_column_dag"||metadata.optimized=="rightlooking_cholesky_column_dag_fma";
    const bool native_tiled_for_scan=metadata.algorithm=="ast_vm_v2"&&!options.force_vm&&
      options.engine!="vm"&&recognized_for_scan&&options.structure=="auto"&&
      (options.engine=="tiled"||(options.engine=="auto"&&n>=128));
    if(native_tiled_for_scan) {
      const auto limit=std::min<std::size_t>(options.band_limit,(n-1)/4);
      native_scan={input.values.data(),n,limit,fused_finite_band_avx2(input.values.data(),n,limit)};
      native_scan_ptr=&native_scan;
      if(!native_scan.facts.finite)throw std::runtime_error("non-finite matrix element");
    } else
#endif
    if(!all_finite_avx2(input.values.data(),input.values.size()))throw std::runtime_error("non-finite matrix element");
  } else
#endif
  for (const double value : input.values) if (!std::isfinite(value)) throw std::runtime_error("non-finite matrix element");
  if(options.metrics) {
    options.metrics->input_validation_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-validation_start).count();
    options.metrics->input_validation_kernel=native_scan_ptr?"avx2_combined_finite_band":(scan_simd?"avx2_exponent_bits":"scalar_finite");
  }
  if (metadata.algorithm == "cholesky_column_v1") {
    if (metadata.arithmetic != "fp64_ascending_k_no_fma" || metadata.dependencies != "column_barrier_diagonal_then_rows") throw std::runtime_error("invalid legacy semantics");
    if(options.metrics)options.metrics->engine="stage";
    return scalar_cholesky(input, options);
  }
  if (metadata.algorithm != "ast_vm_v2" || metadata.program.empty() || metadata.shape_slot >= metadata.slots ||
      metadata.block_slot >= static_cast<int>(metadata.slots) || metadata.block_slot < -1)
    throw std::runtime_error("unsupported execution metadata");
  const bool recognized = metadata.optimized == "scalar_cholesky_column_dag" ||
    metadata.optimized == "rightlooking_cholesky_column_dag" || metadata.optimized == "rightlooking_cholesky_column_dag_fma";
#ifdef CHOL_AUTO_SMALL_STAGE_SERIAL
  // AUTO already chooses stage below N128. In that existing domain a whole
  // column contains too little work to amortize StagePool wake/barriers.
  // Keep explicit stage/tiled and forced VM selection unchanged.
  if(!options.force_vm&&options.engine=="auto"&&recognized&&input.n<128&&default_stage_fp_environment())
    options.parallel=false;
#endif
  if (!options.force_vm && options.engine != "vm" && recognized && (options.engine == "tiled" || (options.engine == "auto" && input.n >= 128)))
    return tiled_cholesky(input, options, metadata.optimized == "rightlooking_cholesky_column_dag_fma", owned_input, native_scan_ptr);
  if (options.metrics) options.metrics->engine = !options.force_vm && options.engine != "vm" && recognized ? "stage" : "vm";
  if (!options.force_vm && options.engine != "vm" && metadata.optimized == "scalar_cholesky_column_dag") return scalar_cholesky(input, options);
  if (!options.force_vm && options.engine != "vm" && metadata.optimized == "rightlooking_cholesky_column_dag") return rightlooking_cholesky(input, options, false);
  if (!options.force_vm && options.engine != "vm" && metadata.optimized == "rightlooking_cholesky_column_dag_fma") return rightlooking_cholesky(input, options, true);
  // This proof only changes the generic VM's finite cap; native kernels above
  // retain their original selection, geometry, validation and FP arithmetic.
  if(options.metrics) {
    options.metrics->vm_budget_proof_status="fixed";
    options.metrics->vm_effective_step_limit=options.vm_step_limit;
  }
#ifdef CHOL_PROVED_VM_BUDGET
  if(options.vm_budget_mode=="proved") {
    const auto proof_start=std::chrono::steady_clock::now();
    const auto proof=prove_vm_step_bound(metadata,input.n,options.block_size);
    if(proof.proved)options.vm_step_limit=std::max(options.vm_step_limit,proof.bound);
    if(options.metrics) {
      options.metrics->vm_budget_proof_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-proof_start).count();
      options.metrics->vm_budget_proof_status=proof.proved?"proved":"unknown";
      options.metrics->vm_budget_proof_reason=proof.reason;
      options.metrics->vm_budget_bound=proof.bound;
      options.metrics->vm_budget_work=proof.work;
      options.metrics->vm_effective_step_limit=options.vm_step_limit;
    }
  }
#endif
#ifdef CHOL_PREPARED_VM
#ifdef CHOL_THREADED_VM
  if(options.vm_backend=="auto"||options.vm_backend=="decoded-threaded") {
#ifdef CHOL_HAVE_THREADED_DISPATCH
    return run_threaded_vm(input,metadata,options,session?&session->plan(options.metrics):nullptr);
#else
    // Report the effective dispatch, including on exceptional execution.
    struct FallbackMetric {RunMetrics* metrics;~FallbackMetric(){if(metrics)metrics->vm_backend="decoded-fallback";}} fallback_metric{options.metrics};
    return run_program<true>(input,metadata,options,session);
#endif
  }
#endif
  if(options.vm_backend=="decoded-tos2")return run_program<true,true>(input,metadata,options,session);
  if(options.vm_backend=="auto"||options.vm_backend=="decoded")return run_program<true>(input,metadata,options,session);
#endif
  return run_program<false>(input, metadata, options);
}
Matrix execute(const Matrix& input,const PreparedVM& session,Options options) {
  if(!session.state_)throw std::runtime_error("empty prepared VM session");
  return execute_impl(input,session.state_->metadata,options,nullptr,session.state_.get());
}
Matrix execute_owned(Matrix input,const PreparedVM& session,Options options) {
  if(!session.state_)throw std::runtime_error("empty prepared VM session");
  return execute_impl(input,session.state_->metadata,options,&input,session.state_.get());
}
Matrix execute(const Matrix& input, const Metadata& metadata, Options options) {
  return execute_impl(input,metadata,options,nullptr);
}
Matrix execute_owned(Matrix input, const Metadata& metadata, Options options) {
  return execute_impl(input,metadata,options,&input);
}
}
