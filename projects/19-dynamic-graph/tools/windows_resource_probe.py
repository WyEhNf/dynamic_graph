"""Read actual Win32 process/host memory counters; no third-party packages."""
import ctypes,os,subprocess,time
from ctypes import wintypes

class ProcessMemory(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t)for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]

class HostMemory(ctypes.Structure):
    _fields_=[('dwLength',wintypes.DWORD),('dwMemoryLoad',wintypes.DWORD)]+[(name,ctypes.c_ulonglong)for name in ('ullTotalPhys','ullAvailPhys','ullTotalPageFile','ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual')]

def monitored_run(command,interval=0.02,*,check=True,timeout=None):
    if os.name!='nt':raise RuntimeError('this resource probe requires Windows')
    psapi=ctypes.WinDLL('psapi',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    get_process=psapi.GetProcessMemoryInfo;get_process.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessMemory),wintypes.DWORD];get_process.restype=wintypes.BOOL
    get_host=kernel.GlobalMemoryStatusEx;get_host.argtypes=[ctypes.POINTER(HostMemory)];get_host.restype=wintypes.BOOL
    filetime_pointer=ctypes.POINTER(wintypes.FILETIME)
    get_system=kernel.GetSystemTimes;get_system.argtypes=[filetime_pointer]*3;get_system.restype=wintypes.BOOL
    get_times=kernel.GetProcessTimes;get_times.argtypes=[wintypes.HANDLE]+[filetime_pointer]*4;get_times.restype=wintypes.BOOL
    def ticks(value):return(int(value.dwHighDateTime)<<32)|int(value.dwLowDateTime)
    def system_times():
        values=[wintypes.FILETIME()for _ in range(3)]
        if not get_system(*(ctypes.byref(v)for v in values)):raise ctypes.WinError(ctypes.get_last_error())
        return tuple(ticks(v)for v in values)
    host_before=system_times()
    metrics={'process_peak_working_set_bytes':0,'process_peak_commit_bytes':0,'process_private_bytes_peak_sampled':0,'host_available_ram_min_bytes':2**64-1,'host_ram_bytes':0,'resource_samples':0,'resource_sample_interval_ms':interval*1000}
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)as process:
        def sample():
            memory=ProcessMemory();memory.cb=ctypes.sizeof(memory)
            if get_process(wintypes.HANDLE(int(process._handle)),ctypes.byref(memory),memory.cb):
                metrics['process_peak_working_set_bytes']=max(metrics['process_peak_working_set_bytes'],memory.PeakWorkingSetSize)
                metrics['process_peak_commit_bytes']=max(metrics['process_peak_commit_bytes'],memory.PeakPagefileUsage)
                metrics['process_private_bytes_peak_sampled']=max(metrics['process_private_bytes_peak_sampled'],memory.PrivateUsage)
                metrics['resource_samples']+=1
                metrics['process_page_fault_count_peak_sampled']=max(metrics.get('process_page_fault_count_peak_sampled',0),memory.PageFaultCount)
            host=HostMemory();host.dwLength=ctypes.sizeof(host)
            if not get_host(ctypes.byref(host)):raise ctypes.WinError(ctypes.get_last_error())
            metrics['host_ram_bytes']=host.ullTotalPhys;metrics['host_available_ram_min_bytes']=min(metrics['host_available_ram_min_bytes'],host.ullAvailPhys)
        began=time.perf_counter();timed_out=False
        while process.poll()is None:
            sample()
            if timeout is not None and time.perf_counter()-began>timeout:
                timed_out=True;process.kill();break
            time.sleep(interval)
        sample();stdout,stderr=process.communicate()

        if metrics['resource_samples']==0 or metrics['process_peak_working_set_bytes']==0:raise RuntimeError('memory probe produced no process samples')
        values=[wintypes.FILETIME()for _ in range(4)]
        if not get_times(wintypes.HANDLE(int(process._handle)),*(ctypes.byref(v)for v in values)):raise ctypes.WinError(ctypes.get_last_error())
        metrics['process_kernel_cpu_ms']=ticks(values[2])/10000
        metrics['process_user_cpu_ms']=ticks(values[3])/10000
        metrics['process_cpu_time_ms']=metrics['process_kernel_cpu_ms']+metrics['process_user_cpu_ms']
        host_after=system_times();idle=host_after[0]-host_before[0];total=(host_after[1]-host_before[1])+(host_after[2]-host_before[2]);busy=total-idle
        metrics['host_busy_percent_during_process']=100*busy/total if total>0 else None
        metrics['host_busy_cpu_ms_during_process']=busy/10000
        metrics['host_other_cpu_ms_estimate']=max(0,busy/10000-metrics['process_cpu_time_ms'])
        metrics['host_cpu_counter_scope']='all logical CPUs on this <=64-CPU host; includes IO/startup, probe and other processes; kernel includes idle before subtraction'
        if timed_out:raise subprocess.TimeoutExpired(command,timeout,output=stdout,stderr=stderr)
        if check and process.returncode:raise subprocess.CalledProcessError(process.returncode,command,output=stdout,stderr=stderr)
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr),metrics
