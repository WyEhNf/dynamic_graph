"""Isolated-process Python allocation/RSS observations, not latency benchmark."""
import argparse
import ctypes
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


def peak_rss():
    if sys.platform!='win32':return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(n,ctypes.c_size_t)for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    value=Counters();value.cb=ctypes.sizeof(value)
    ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    ctypes.windll.psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(value),value.cb):return None
    return value.PeakWorkingSetSize


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',action='store_true');parser.add_argument('--family',default='parallel_chains');parser.add_argument('--size',type=int,default=2048)
    parser.add_argument('--output',default='experiments/resources.json');parser.add_argument('--bits',type=int,default=4);args=parser.parse_args()
    if args.worker:
        tracemalloc.start();start=perf_counter();data=generate_workload(18001,args.family,args.size,args.bits)
        row={'family':args.family,'target_nodes':args.size,'node_count':len(data['instructions']),'bit_width':args.bits}
        try:
            result=optimize(data,time_budget_ms=20000,max_states=30000);verify(data,result)
            row.update(status='verified',copies=result['stats']['inserted_copy_count'])
        except Exception as exc:row.update(status=type(exc).__name__,error=str(exc))
        row.update(elapsed_with_tracing_s=perf_counter()-start,peak_traced_bytes=tracemalloc.get_traced_memory()[1],peak_process_working_set_bytes=peak_rss())
        print(json.dumps(row));return
    start=perf_counter();rows=[]
    for family in ('parallel_chains','skew_tree','sparse_shared','hazard_multi'):
        for size in (128,512,2048,8192):
            process=subprocess.run([sys.executable,__file__,'--worker','--family',family,'--size',str(size),'--bits',str(args.bits)],capture_output=True,text=True,check=True)
            rows.append(json.loads(process.stdout))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'runtime':platform.platform(),'python':sys.version,'measurement':'isolated process, tracemalloc enabled; latency is instrumentation-inflated; peak Windows process working set includes interpreter and imports',
                                'elapsed_seconds':perf_counter()-start,'records':rows},indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
