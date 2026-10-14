#include "cholesky/runtime.hpp"
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
#include "cholesky/native_workspace.hpp"
#endif
#ifdef CHOL_REUSE_WORKERS
#include "cholesky/execution_context.hpp"
#endif
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

int main(int argc, char** argv) {
  std::filesystem::path partial_output;
  bool published=false;
  try {
    using Clock=std::chrono::steady_clock;
    const auto ms=[](Clock::time_point start){return std::chrono::duration<double,std::milli>(Clock::now()-start).count();};
    std::string input_path, output_path, metadata_path, vm_plan="per-matrix",native_workspace_mode="off";
    chol::Options options;
#ifdef CHOL_REUSE_WORKERS
    bool reuse_workers=true;
#endif
    for (int i = 1; i < argc; ++i) {
      const std::string arg = argv[i];
      if (arg == "--help") {
        std::cout << "cholesky_runtime --metadata file.meta --input matrices.bin --output result.bin [--scheduler serial|parallel] [--threads 4] [--engine auto|vm|stage|tiled] [--tile-size auto|1..1024] [--ready-queue heap|bucket] [--simd auto|portable] [--structure auto|dense] [--band-limit 128] [--block-size 32] [--vm-backend auto|legacy"
#ifdef CHOL_PREPARED_VM
          << "|decoded|decoded-tos2"
#endif
#ifdef CHOL_THREADED_VM
          << "|decoded-threaded"
#endif
#ifdef CHOL_REUSE_WORKERS
          << "] [--worker-context auto|off"
#endif
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
          << "] [--native-workspace off|session|session-trim"
#endif
          << "] [--vm-plan per-matrix|session] [--vm-step-limit 1000000000] [--vm-budget fixed"
#ifdef CHOL_PROVED_VM_BUDGET
          << "|proved"
#endif
          << "]\n";
        return 0;
      }
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + arg);
      const std::string value = argv[++i];
      if (arg == "--input") input_path = value;
      else if (arg == "--output") output_path = value;
      else if (arg == "--metadata") metadata_path = value;
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
      else if(arg=="--native-workspace") {
        if(value!="off"&&value!="session"&&value!="session-trim")throw std::runtime_error("native workspace must be off, session, or session-trim");
        native_workspace_mode=value;
      }
#endif
#ifdef CHOL_REUSE_WORKERS
      else if(arg=="--worker-context") {
        if(value!="auto"&&value!="off")throw std::runtime_error("worker context must be auto or off");
        reuse_workers=value=="auto";
      }
#endif
      else if(arg=="--vm-plan") {
        if(value!="per-matrix"&&value!="session")throw std::runtime_error("VM plan must be per-matrix or session");
        vm_plan=value;
      }
      else if(arg=="--vm-backend") {
        if(value!="auto"&&value!="legacy"
#ifdef CHOL_PREPARED_VM
           &&value!="decoded"&&value!="decoded-tos2"
#endif
#ifdef CHOL_THREADED_VM
           &&value!="decoded-threaded"
#endif
        )throw std::runtime_error("unknown or disabled VM backend");
        options.vm_backend=value;
      } else if(arg=="--vm-budget") {
        if(value!="fixed"&&value!="proved")throw std::runtime_error("VM budget mode must be fixed or proved");
#ifndef CHOL_PROVED_VM_BUDGET
        if(value=="proved")throw std::runtime_error("proved VM budget is disabled in this build");
#endif
        options.vm_budget_mode=value;
      } else if (arg == "--scheduler") {
        if (value != "serial" && value != "parallel") throw std::runtime_error("unknown scheduler");
        options.parallel = value == "parallel";
      } else if (arg == "--engine") {
        if (value != "auto" && value != "vm" && value != "stage" && value != "tiled") throw std::runtime_error("unknown execution engine");
        options.engine = value;
        options.force_vm = value == "vm";
      } else if(arg=="--ready-queue") {
        if(value!="heap"&&value!="bucket")throw std::runtime_error("ready queue must be heap or bucket");
        options.ready_queue=value;
      } else if(arg=="--simd") {
        if(value!="auto"&&value!="portable"
#ifdef CHOL_HAVE_AVX512_KERNEL
           &&value!="avx2"&&value!="avx512"
#endif
        )throw std::runtime_error("simd must be auto/portable or an enabled optional avx2/avx512 mode");
        options.simd=value;
      } else if(arg=="--structure") {
        if(value!="auto"&&value!="dense")throw std::runtime_error("structure must be auto or dense");
        options.structure=value;
      } else if(arg=="--band-limit") {
        std::size_t consumed=0;const auto width=std::stoul(value,&consumed);
        if(consumed!=value.size()||width>1024)throw std::runtime_error("band limit must be within [0,1024]");
        options.band_limit=static_cast<unsigned>(width);
      } else if (arg == "--tile-size") {
        if(value=="auto"){options.tile_size=0;continue;}
        std::size_t consumed = 0; const auto size = std::stoul(value, &consumed);
        if (consumed != value.size() || size < 1 || size > 1024) throw std::runtime_error("tile size must be within [1, 1024]");
        options.tile_size = static_cast<unsigned>(size);
      } else if (arg == "--block-size") {
        std::size_t consumed = 0; const auto size = std::stoul(value, &consumed);
        if (consumed != value.size() || size < 1 || size > 10000) throw std::runtime_error("block size must be within [1, 10000]");
        options.block_size = static_cast<unsigned>(size);
      } else if (arg == "--vm-step-limit") {
        std::size_t consumed = 0; const auto size = std::stoull(value, &consumed);
        if (consumed != value.size() || size < 1) throw std::runtime_error("VM step limit must be positive");
        options.vm_step_limit = size;
        options.vm_step_limit_explicit = true;
      } else if (arg == "--threads") {
        std::size_t consumed = 0; const auto threads = std::stoul(value, &consumed);
        if (consumed != value.size() || threads < 1 || threads > 256) throw std::runtime_error("threads must be within [1, 256]");
        options.threads = static_cast<unsigned>(threads);
      } else throw std::runtime_error("unknown argument: " + arg);
    }
    if(options.vm_budget_mode=="proved"&&options.vm_step_limit_explicit)
      throw std::runtime_error("proved VM budget cannot combine with an explicit VM step limit");
    if (input_path.empty() || output_path.empty() || metadata_path.empty()) throw std::runtime_error("input, output and metadata are required");
    if (std::filesystem::weakly_canonical(input_path) == std::filesystem::weakly_canonical(output_path))
      throw std::runtime_error("input and output paths must differ");
    const auto metadata_start=Clock::now();
    auto metadata = chol::read_metadata(metadata_path);const auto metadata_ms=ms(metadata_start);
    auto io_start=Clock::now();
    std::ifstream input(input_path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open input");
    const auto count = chol::read_count(input);
    double read_ms=ms(io_start),write_ms=0;io_start=Clock::now();
    const auto temporary = output_path + ".partial";
    partial_output=temporary;
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot open output");
    chol::write_count(output, count);
    write_ms+=ms(io_start);
    double vm_session_setup_ms=0,vm_session_release_ms=0;
    std::unique_ptr<chol::PreparedVM> session;
    if(vm_plan=="session") {
      const auto start=Clock::now();
      session=std::make_unique<chol::PreparedVM>(std::move(metadata));
      vm_session_setup_ms=ms(start);
    }
    double milliseconds = vm_session_setup_ms;
    double worker_context_release_ms=0;
    std::uint64_t context_workers_created=0,context_jobs=0;
#ifdef CHOL_REUSE_WORKERS
    std::unique_ptr<chol::ExecutionContext> execution_context;
    // A single matrix cannot amortize stream worker lifetime. Preserve the
    // ordinary per-call worker path unless the input declares multiple jobs.
    if(reuse_workers&&count>1&&options.parallel&&options.threads>1) {
      const auto context_start=Clock::now();
      execution_context=std::make_unique<chol::ExecutionContext>();
      options.execution_context=execution_context.get();
      milliseconds+=ms(context_start);
    }
#endif
    double workspace_setup_ms=0,workspace_release_ms=0,workspace_acquire_ms=0;
    std::uint64_t workspace_allocations=0,workspace_reuses=0,workspace_capacity_peak=0;
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
    std::unique_ptr<chol::NativeWorkspace> native_workspace;
    if(native_workspace_mode!="off") {
      const auto start=Clock::now();
      native_workspace=std::make_unique<chol::NativeWorkspace>(native_workspace_mode=="session-trim");
      options.native_workspace=native_workspace.get();
      workspace_setup_ms=ms(start);milliseconds+=workspace_setup_ms;
    }
#endif
    chol::RunMetrics metrics;
    std::uint64_t tasks = 0, packed_bytes = 0, task_metadata_bytes = 0, ready_peak=0,resident_task_states=0;
    double graph_ms = 0, kernel_ms = 0, export_ms=0, input_validation_ms=0, input_recycle_ms=0;
    double vm_prepare_ms=0;std::uint64_t vm_steps=0,vm_plan_bytes_peak=0,vm_plan_builds=0,vm_plan_reuses=0;std::string vm_backend;
    double vm_budget_proof_ms=0;std::uint64_t vm_budget_work=0,vm_budget_bound_peak=0,vm_effective_step_limit_max=0;
    std::uint32_t vm_budget_proved_matrices=0,vm_budget_unknown_matrices=0,vm_budget_not_run_matrices=0;
    unsigned input_buffers_reused=0;
    std::string engine,vector_kernel,ready_queue,workspace_layout,input_validation_kernel,structure_scan_kernel;
    unsigned tile_size_min=1025,tile_size_max=0,effective_tile_size=0,vector_rows=0,structure_bandwidth=0,worker_threads=1,worker_threads_max=0;
    double structure_scan_ms=0;
    options.metrics = &metrics;
    for (std::uint32_t index = 0; index < count; ++index) {
      io_start=Clock::now();auto matrix = chol::read_matrix(input);read_ms+=ms(io_start);
      const auto start = std::chrono::steady_clock::now();
      auto result = session?chol::execute_owned(std::move(matrix),*session,options):chol::execute_owned(std::move(matrix),metadata,options);
      milliseconds += std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
      input_buffers_reused+=metrics.input_buffer_reused?1u:0u;input_recycle_ms+=metrics.input_recycle_ms;
      workspace_acquire_ms+=metrics.workspace_acquire_ms;
      tasks += metrics.tasks; packed_bytes = std::max(packed_bytes, metrics.packed_bytes);
      task_metadata_bytes = std::max(task_metadata_bytes,metrics.task_metadata_bytes);
      resident_task_states=std::max(resident_task_states,metrics.resident_task_states);
      ready_peak=std::max(ready_peak,metrics.ready_peak);
      input_validation_ms+=metrics.input_validation_ms;input_validation_kernel=metrics.input_validation_kernel;structure_scan_kernel=metrics.structure_scan_kernel;
      graph_ms += metrics.graph_ms; kernel_ms += metrics.kernel_ms;export_ms+=metrics.export_ms;
      vm_plan_builds+=metrics.vm_plan_builds;vm_plan_reuses+=metrics.vm_plan_reuses;
      vm_prepare_ms+=metrics.vm_prepare_ms;vm_steps+=metrics.vm_steps;vm_plan_bytes_peak=std::max(vm_plan_bytes_peak,metrics.vm_plan_bytes);vm_backend=metrics.vm_backend;
      vm_budget_proof_ms+=metrics.vm_budget_proof_ms;vm_budget_work+=metrics.vm_budget_work;
      vm_budget_bound_peak=std::max(vm_budget_bound_peak,metrics.vm_budget_bound);
      vm_effective_step_limit_max=std::max(vm_effective_step_limit_max,metrics.vm_effective_step_limit);
      vm_budget_proved_matrices+=metrics.vm_budget_proof_status=="proved";
      vm_budget_unknown_matrices+=metrics.vm_budget_proof_status=="unknown";
      vm_budget_not_run_matrices+=metrics.vm_budget_proof_status=="not-run";
      engine = metrics.engine;
      vector_kernel=metrics.vector_kernel;
      ready_queue=metrics.ready_queue;workspace_layout=metrics.workspace_layout;
      effective_tile_size=metrics.effective_tile_size;
      vector_rows=metrics.vector_rows;
      structure_bandwidth=metrics.structure_bandwidth;structure_scan_ms+=metrics.structure_scan_ms;
      worker_threads=metrics.worker_threads;worker_threads_max=std::max(worker_threads_max,worker_threads);
      if(effective_tile_size){tile_size_min=std::min(tile_size_min,effective_tile_size);tile_size_max=std::max(tile_size_max,effective_tile_size);}
      io_start=Clock::now();chol::write_matrix(output, result);write_ms+=ms(io_start);
    }
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
    if(native_workspace) {
      // Include cold allocation above and final release here in stream compute.
      // The API's scope guard has released every lease before this boundary.
      const auto start=Clock::now();
      workspace_allocations=native_workspace->allocations();workspace_reuses=native_workspace->reuses();
      workspace_capacity_peak=native_workspace->peak_capacity_bytes();
      options.native_workspace=nullptr;native_workspace.reset();
      workspace_release_ms=ms(start);milliseconds+=workspace_release_ms;
    }
#endif
    if(session) {
      const auto start=Clock::now();
      session.reset();
      vm_session_release_ms=ms(start);
      milliseconds+=vm_session_release_ms;
    }
    io_start=Clock::now();chol::ensure_eof(input);read_ms+=ms(io_start);
#ifdef CHOL_REUSE_WORKERS
    // Final pool shutdown is charged to aggregate compute, just as every
    // per-matrix join is charged in the baseline. No deferred job survives.
    if(execution_context) {
      const auto context_release_start=Clock::now();
      context_workers_created=execution_context->workers_created();context_jobs=execution_context->jobs_dispatched();
      options.execution_context=nullptr;execution_context.reset();
      worker_context_release_ms=ms(context_release_start);milliseconds+=worker_context_release_ms;
    }
#endif
    io_start=Clock::now();
    output.close();
    if (!output) throw std::runtime_error("output flush failed");
    std::filesystem::rename(temporary, output_path);
    published=true;write_ms+=ms(io_start);
    std::cout << "{\"matrices\":" << count << ",\"compute_ms\":" << milliseconds << ",\"metadata_bytes\":" << std::filesystem::file_size(metadata_path)
      << ",\"worker_context_release_ms\":" << worker_context_release_ms << ",\"context_workers_created\":" << context_workers_created << ",\"context_jobs\":" << context_jobs
      << ",\"native_workspace_mode\":\"" << native_workspace_mode << "\""
      << ",\"workspace_setup_ms\":" << workspace_setup_ms << ",\"workspace_acquire_ms\":" << workspace_acquire_ms << ",\"workspace_release_ms\":" << workspace_release_ms
      << ",\"workspace_allocations\":" << workspace_allocations << ",\"workspace_reuses\":" << workspace_reuses << ",\"workspace_capacity_peak_bytes\":" << workspace_capacity_peak
      << ",\"input_validation_ms\":" << input_validation_ms << ",\"input_validation_kernel\":\"" << input_validation_kernel << "\",\"structure_scan_kernel\":\"" << structure_scan_kernel << "\""
      << ",\"input_buffers_reused\":" << input_buffers_reused << ",\"input_recycle_ms\":" << input_recycle_ms
      << ",\"vm_backend\":\"" << vm_backend << "\",\"vm_steps\":" << vm_steps << ",\"vm_prepare_ms\":" << vm_prepare_ms << ",\"vm_plan_bytes_peak\":" << vm_plan_bytes_peak
      << ",\"vm_plan\":\"" << vm_plan << "\",\"vm_plan_builds\":" << vm_plan_builds << ",\"vm_plan_reuses\":" << vm_plan_reuses
      << ",\"vm_session_setup_ms\":" << vm_session_setup_ms << ",\"vm_session_release_ms\":" << vm_session_release_ms
      << ",\"vm_budget_mode\":\"" << options.vm_budget_mode << "\",\"vm_budget_proof_ms\":" << vm_budget_proof_ms << ",\"vm_budget_work\":" << vm_budget_work
      << ",\"vm_budget_bound_peak\":" << vm_budget_bound_peak << ",\"vm_effective_step_limit_max\":" << vm_effective_step_limit_max
      << ",\"vm_budget_proved_matrices\":" << vm_budget_proved_matrices << ",\"vm_budget_unknown_matrices\":" << vm_budget_unknown_matrices << ",\"vm_budget_not_run_matrices\":" << vm_budget_not_run_matrices
      << ",\"resident_task_states_peak\":" << resident_task_states
      << ",\"selected_engine\":\"" << engine << "\",\"task_count\":" << tasks << ",\"graph_ms\":" << graph_ms << ",\"kernel_ms\":" << kernel_ms << ",\"export_ms\":" << export_ms << ",\"workspace_layout\":\"" << workspace_layout << "\",\"packed_bytes_peak\":" << packed_bytes << ",\"task_metadata_bytes_peak\":" << task_metadata_bytes << ",\"vector_kernel\":\"" << vector_kernel << "\",\"metadata_read_ms\":" << metadata_ms << ",\"input_read_ms\":" << read_ms << ",\"output_write_ms\":" << write_ms << ",\"ready_queue\":\"" << ready_queue << "\",\"ready_peak\":" << ready_peak << ",\"effective_tile_size\":" << effective_tile_size << ",\"vector_rows\":" << vector_rows << ",\"structure_bandwidth\":" << structure_bandwidth << ",\"structure_scan_ms\":" << structure_scan_ms << ",\"worker_threads\":" << worker_threads << ",\"worker_threads_max\":" << worker_threads_max << ",\"tile_size_min\":" << (tile_size_max?tile_size_min:0) << ",\"tile_size_max\":" << tile_size_max << "}\n";
    return 0;
  } catch (const std::exception& error) {
    if(!published&&!partial_output.empty()){std::error_code ignored;std::filesystem::remove(partial_output,ignored);}
    std::cerr << "error: " << error.what() << '\n'; return 1;
  }
}
