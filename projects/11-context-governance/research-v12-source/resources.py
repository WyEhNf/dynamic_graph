"""Read-only process and CUDA usage for reproducible benchmark costs."""
import os
import platform


def resource_snapshot(model=None):
    result={'platform':platform.platform(),'logical_cpus':os.cpu_count(),
            'process_peak_resident_bytes':None,'cuda_peak_allocated_bytes':None,
            'cuda_peak_reserved_bytes':None}
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
                      ('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),
                      ('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
                      ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
                      ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        get_process=ctypes.windll.kernel32.GetCurrentProcess; get_process.restype=wintypes.HANDLE
        get_info=ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if get_info(get_process(),ctypes.byref(counters),counters.cb):
            result['process_peak_resident_bytes']=counters.PeakWorkingSetSize
    else:
        import resource
        maximum=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['process_peak_resident_bytes']=maximum if platform.system()=='Darwin' else maximum*1024
    if model is not None and model.device_type=='cuda':
        torch=model.torch
        result.update(cuda_device=torch.cuda.get_device_name(model.device),
                      cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(model.device),
                      cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(model.device))
    result['measurement_scope']='This Python process; CUDA allocator, not whole-device usage or child test processes.'
    return result
