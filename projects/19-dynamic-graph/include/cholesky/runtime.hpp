#pragma once
#include <cstddef>
#include <cstdint>
#include <istream>
#include <memory>
#include <ostream>
#include <string>
#include <vector>

namespace chol {
class ExecutionContext;
class NativeWorkspace;
struct Matrix { std::uint32_t n; std::vector<double> values; };
enum class Opcode { Const, Load, Store, Uninit, Read, Write, Dup, Pop,
  Add, Sub, Mul, Div, IntDiv, Mod, Neg, Not, Bool, Trunc, Sqrt, Abs, Min, Max, Fma,
  Lt, Le, Gt, Ge, Eq, Ne, Jump, Jz, Jnz, Return };
struct Instruction { Opcode opcode; double argument = 0; };
struct Metadata {
  std::string algorithm; std::string arithmetic; std::string dependencies;
  std::string optimized = "none";
  std::size_t slots = 0;
  std::size_t shape_slot = 0;
  int block_slot = -1;
  std::vector<Instruction> program;
};
struct RunMetrics {
  std::string engine;
  std::string vm_backend;
  std::uint64_t vm_steps=0,vm_plan_bytes=0,vm_last_pc=0;
  double vm_prepare_ms=0;
  std::uint64_t vm_plan_builds=0,vm_plan_reuses=0;
  std::string vm_budget_mode,vm_budget_proof_status,vm_budget_proof_reason;
  std::uint64_t vm_budget_bound=0,vm_budget_work=0,vm_effective_step_limit=0;
  double vm_budget_proof_ms=0;
  std::uint64_t tasks = 0;
  std::uint64_t packed_bytes = 0;
  std::uint64_t task_metadata_bytes = 0;
  std::uint64_t resident_task_states = 0;
  double graph_ms = 0;
  double kernel_ms = 0;
  double input_validation_ms = 0;
  std::string input_validation_kernel;
  std::string structure_scan_kernel;
  std::string vector_kernel;
  std::string ready_queue;
  std::uint64_t ready_peak = 0;
  unsigned effective_tile_size = 0;
  unsigned vector_rows = 0;
  unsigned structure_bandwidth = 0;
  double structure_scan_ms = 0;
  unsigned worker_threads = 1;
  double export_ms = 0;
  std::string workspace_layout;
  bool input_buffer_reused = false;
  double input_recycle_ms = 0;
  double workspace_acquire_ms=0;
  std::uint64_t workspace_capacity_bytes=0;
  bool workspace_reused=false;
};
struct Options {
  bool parallel = false; unsigned threads = 1;
  bool force_vm = false; unsigned block_size = 32;
  std::uint64_t vm_step_limit = 1000000000ull;
  std::string vm_budget_mode = "fixed"; // Proved policy requires an opt-in build.
  bool vm_step_limit_explicit = false; // Literal API/CLI limits cannot combine with proved.
  std::string engine = "auto";
  std::string vm_backend = "auto"; // GNU threaded, otherwise decoded/legacy build fallback.
  unsigned tile_size = 0; // 0 selects a measured shape policy; positive overrides it.
  RunMetrics* metrics = nullptr;
  std::string simd = "auto";
  std::string ready_queue = "heap";
  std::string structure = "auto";
  unsigned band_limit = 128;
  ExecutionContext* execution_context=nullptr; // Optional explicit owner; synchronous jobs.
  NativeWorkspace* native_workspace=nullptr; // Optional leased allocation capacity only.
};
namespace detail { struct PreparedVMState; }
// Explicit immutable Metadata snapshot. Each execution still owns fresh matrix,
// slots, initialization bits, operand stack and N/block-dependent budget state.
// A shared decoded plan is built lazily only after dispatch selects a typed VM.
// Concurrent execute calls are supported; moving/destroying the session requires
// the caller to finish those calls first. No global, TLS or address-keyed cache.
class PreparedVM {
 public:
  explicit PreparedVM(Metadata metadata);
  ~PreparedVM();
  PreparedVM(PreparedVM&&) noexcept;
  PreparedVM& operator=(PreparedVM&&) noexcept;
  PreparedVM(const PreparedVM&)=delete;
  PreparedVM& operator=(const PreparedVM&)=delete;
 private:
  std::unique_ptr<detail::PreparedVMState> state_;
  friend Matrix execute(const Matrix&,const PreparedVM&,Options);
  friend Matrix execute_owned(Matrix,const PreparedVM&,Options);
};
Matrix execute(const Matrix& input,const PreparedVM& session,Options options = {});
Matrix execute_owned(Matrix input,const PreparedVM& session,Options options = {});
Metadata read_metadata(const std::string& path);
std::uint32_t read_count(std::istream& input);
Matrix read_matrix(std::istream& input);
void write_count(std::ostream& output, std::uint32_t count);
void write_matrix(std::ostream& output, const Matrix& matrix);
void ensure_eof(std::istream& input);
Matrix execute(const Matrix& input, const Metadata& metadata, Options options = {});
// Consumes this private matrix. Dense column-workspace kernels may recycle it
// after all worker reads; when compiled in, owned native structured reuse may
// factor in place after validation/classification, then clear upper +0 and hand
// off the buffer. Borrowed execute inputs remain unchanged; other paths allocate.
Matrix execute_owned(Matrix input, const Metadata& metadata, Options options = {});
}
