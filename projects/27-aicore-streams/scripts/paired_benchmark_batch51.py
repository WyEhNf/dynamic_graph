"""Alternating paired CPU measurements with saved raw results and provenance.

Peak working set covers the complete CLI process (JSON DOM, witnesses, solver,
validators, results), not the simulated device memory limit or solver alone.
"""
import argparse
import ctypes
import hashlib
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from compare_research import summarize
from host_sampler_batch51 import HostSampler


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(executable, suite, output):
    command = [str(executable.resolve()), "--input", str(suite), "--output", str(output),
               "--csv", str(output.with_suffix(".csv")), "--failures", str(output.with_suffix(".failures.json"))]
    started = time.perf_counter()
    host = HostSampler()
    host.sample(force=True)
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    peak = 0
    handle = None
    if os.name == "nt":
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [(key, ctypes.c_size_t) for key in ["PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        handle = kernel.OpenProcess(0x0400 | 0x0010, False, child.pid)
    while child.poll() is None:
        host.sample()
        if handle:
            counter = Counters()
            counter.cb = ctypes.sizeof(counter)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counter), counter.cb):
                peak = max(peak, counter.PeakWorkingSetSize)
        time.sleep(.005)
    stdout, stderr = child.communicate()
    if handle:
        kernel.CloseHandle(handle)
    elapsed = time.perf_counter() - started
    host_load = host.finish()
    output.with_suffix(".host.json").write_text(json.dumps(host_load, indent=2)+"\n", encoding="utf-8")
    output.with_suffix(".stdout.txt").write_text(stdout, encoding="utf-8")
    output.with_suffix(".stderr.txt").write_text(stderr, encoding="utf-8")
    if child.returncode not in (0, 1) or not output.exists():
        raise RuntimeError(f"benchmark failed: {child.returncode} {stderr}")
    result = json.loads(output.read_text())
    print(f"{output.name}: {stdout.strip()} wall={elapsed:.3f}s peak_process={peak/2**20:.1f}MiB")
    return dict(report=str(output), exit_code=child.returncode, wall_seconds=elapsed,
                peak_working_set_bytes=peak or None, host_load=host_load,
                host_report=str(output.with_suffix(".host.json")),
                host_report_sha256=sha(output.with_suffix(".host.json")), result=result)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, default=Path("research/baseline-v1/aicore_bench.exe"))
    p.add_argument("--current", type=Path, default=Path("build/aicore_bench.exe"))
    p.add_argument("--current-source", type=Path, default=Path("solution/solution.cpp"), help="Exact source for an isolated candidate executable; avoids changing the validated default")
    p.add_argument("--suite", type=Path, default=Path("data/research-expanded.json"))
    p.add_argument("--prefix", type=Path, default=Path("reports/paired-expanded"))
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--allow-after-failures", action="store_true", help="exploratory hard workload only; keep failed feasible cases explicit, never counts them as passes")
    args = p.parse_args()
    runs = []
    for i in range(args.repetitions):
        measurements = {}
        for label in (["before", "after"] if i % 2 == 0 else ["after", "before"]):
            executable = args.baseline if label == "before" else args.current
            measurements[label] = execute(executable, args.suite, Path(f"{args.prefix}-{i+1}-{label}.json"))
        comparison = summarize(measurements["before"]["result"], measurements["after"]["result"])
        runs.append(dict(repetition=i+1, before={k:v for k,v in measurements["before"].items() if k!="result"},
                         after={k:v for k,v in measurements["after"].items() if k!="result"}, comparison=comparison))
    result = dict(suite=str(args.suite), suite_sha256=sha(args.suite), baseline_exe_sha256=sha(args.baseline),
                  current_exe_sha256=sha(args.current), current_solution_sha256=sha(args.current_source),current_solution_path=str(args.current_source),
                  baseline_solution_sha256=sha(args.baseline.with_name("solution.cpp")), runs=runs,
                  baseline_solution_path=str(args.baseline.with_name("solution.cpp")),
                  median_common_solve_us_before=statistics.median(r["comparison"]["common_solve_us_before"] for r in runs),
                  median_common_solve_us_after=statistics.median(r["comparison"]["common_solve_us_after"] for r in runs),
                  median_wall_seconds_before=statistics.median(r["before"]["wall_seconds"] for r in runs),
                  median_wall_seconds_after=statistics.median(r["after"]["wall_seconds"] for r in runs),
                  maximum_cli_working_set_bytes=max(r["after"]["peak_working_set_bytes"] or 0 for r in runs),
                  timing_scope="solve_us: ScheduleCvGraph elapsed wall time, includes OS preemption; thread CPU: Win32 user+kernel time, quantized; wall/working set: full CLI including JSON, witnesses and validation",
                  exploratory_failures_allowed=args.allow_after_failures)
    for side in ["before","after"]:
        values=[r["comparison"]["common_thread_cpu_us_"+side] for r in runs]
        result["median_common_thread_cpu_us_"+side]=statistics.median(values) if all(x is not None for x in values) else None
        result["median_all_solve_us_"+side]=statistics.median(r["comparison"]["all_solve_us_"+side] for r in runs)
        all_cpu=[r["comparison"]["all_thread_cpu_us_"+side] for r in runs]
        result["median_all_thread_cpu_us_"+side]=statistics.median(all_cpu) if all(x is not None for x in all_cpu) else None
    result["current_harness_source_sha256"]=sha("src/benchmark.cpp")
    result["measurement_driver_sha256"]=sha(__file__)
    result["host_sampler_sha256"]=sha(Path(__file__).with_name("host_sampler_batch51.py"))
    result["host_load_scope"]="Pertrial raw host CPU ticks/RAM samples including user background; sampled 0.25 seconds, same monitor both sides; no background subtraction or empty-host claim"
    provenance=args.baseline.with_name("provenance.json")
    if provenance.exists():result["baseline_build_provenance"]=json.loads(provenance.read_text())
    Path(f"{args.prefix}-summary.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="runs"}, indent=2))
    if any(r["after"]["exit_code"] for r in runs) and not args.allow_after_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
