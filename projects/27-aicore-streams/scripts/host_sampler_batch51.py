"""Per-trial host observations, independent of the C++ solver's thread CPU.

GetSystemTimes kernel ticks include idle ticks, hence busy=(kernel+user-idle).
On this <=64 logical-processor host the counters cover all processors. More
than 64 processors would cover only the caller's primary processor group.
RAM is volatile available physical memory, not process working set/device RAM.
References: Microsoft Learn GetSystemTimes and GlobalMemoryStatusEx.
"""
import ctypes
import os
import time


class FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
        (name, ctypes.c_uint64) for name in (
            "total_phys", "avail_phys", "total_page", "avail_page",
            "total_virtual", "avail_virtual", "avail_extended_virtual")]


def cpu_delta(first, last):
    """Return exact integer tick differences; invalid/zero deltas are missing."""
    if first is None or last is None:
        return None
    idle, kernel, user = [last[key] - first[key] for key in ("idle", "kernel", "user")]
    total = kernel + user
    if min(idle, kernel, user) < 0 or total <= 0 or idle > total:
        return None
    return dict(idle_ticks=idle, kernel_ticks=kernel, user_ticks=user,
                total_ticks=total, busy_ticks=total-idle,
                busy_fraction=(total-idle)/total)


class HostSampler:
    interval_seconds = .25

    def __init__(self):
        self.started = time.perf_counter()
        self.samples = []
        self.errors = []
        self.logical_processors = os.cpu_count()
        self.kernel = None
        if os.name == "nt":
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.GetSystemTimes.argtypes = [ctypes.POINTER(FileTime)] * 3
            self.kernel.GetSystemTimes.restype = ctypes.c_int
            self.kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MemoryStatus)]
            self.kernel.GlobalMemoryStatusEx.restype = ctypes.c_int
        else:
            self.errors.append("non-Windows host: Win32 observations unavailable")

    def sample(self, force=False):
        elapsed = time.perf_counter() - self.started
        if not force and self.samples and elapsed-self.samples[-1]["elapsed_seconds"] < self.interval_seconds:
            return
        row = dict(elapsed_seconds=elapsed, cpu_ticks=None, memory=None)
        if self.kernel is not None:
            idle, kernel, user = FileTime(), FileTime(), FileTime()
            if self.kernel.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                ticks = lambda ft: (ft.high << 32) | ft.low
                row["cpu_ticks"] = dict(idle=ticks(idle), kernel=ticks(kernel), user=ticks(user))
            else:
                self.errors.append(dict(api="GetSystemTimes", elapsed_seconds=elapsed,
                                        win32_error=ctypes.get_last_error()))
            memory = MemoryStatus()
            memory.length = ctypes.sizeof(memory)
            if self.kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
                row["memory"] = dict(total_physical_bytes=memory.total_phys,
                                     available_physical_bytes=memory.avail_phys,
                                     memory_load_percent=memory.load)
            else:
                self.errors.append(dict(api="GlobalMemoryStatusEx", elapsed_seconds=elapsed,
                                        win32_error=ctypes.get_last_error()))
        self.samples.append(row)

    def finish(self):
        self.sample(force=True)
        intervals = []
        for first, last in zip(self.samples, self.samples[1:]):
            delta = cpu_delta(first["cpu_ticks"], last["cpu_ticks"])
            intervals.append(dict(begin_seconds=first["elapsed_seconds"],
                                  end_seconds=last["elapsed_seconds"], delta=delta))
        endpoints = cpu_delta(self.samples[0]["cpu_ticks"], self.samples[-1]["cpu_ticks"])
        memories = [row["memory"] for row in self.samples if row["memory"] is not None]
        complete = (not self.errors and endpoints is not None
                    and len(memories) == len(self.samples)
                    and all(row["delta"] is not None for row in intervals))
        return dict(status="measured" if complete else "partial_or_unmeasured",
                    sample_interval_seconds=self.interval_seconds,
                    logical_processors=self.logical_processors,
                    processor_scope="all processors" if self.logical_processors is not None and self.logical_processors <= 64 else "primary processor group only",
                    trial_cpu_delta=endpoints,
                    available_physical_bytes_start=memories[0]["available_physical_bytes"] if memories else None,
                    available_physical_bytes_end=memories[-1]["available_physical_bytes"] if memories else None,
                    available_physical_bytes_min=min(row["available_physical_bytes"] for row in memories) if memories else None,
                    total_physical_bytes_observed=sorted({row["total_physical_bytes"] for row in memories}),
                    samples=self.samples, cpu_intervals=intervals, errors=self.errors,
                    scope="Whole-host activity includes benchmark, monitoring and user apps; RAM observations are sampled, not a guaranteed continuous minimum; no subtraction of background activity",
                    sources=["https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes",
                             "https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex"])
