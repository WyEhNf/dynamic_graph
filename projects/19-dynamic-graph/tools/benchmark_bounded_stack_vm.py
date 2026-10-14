"""Matched build experiment over every frozen real-C stream, with all costs.

No source/shape selection from observed improvements. Build provenance must
identify the options that differ. Original-C reference files are freshly
hashed and every produced full stream is checked against the reference.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from time import perf_counter

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')
PLAN=Path('G:/Hackathon-stage2-artifacts/project19/load-pair/next-static-plan/plan.json')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def launch(command, affinity):
    if affinity is None:
        return subprocess.run(command,capture_output=True,text=True,timeout=45),None
    # Pin only our own suspended child, before it executes any benchmark work.
    # This avoids migration between cores while unrelated projects keep working.
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);nt=ctypes.WinDLL('ntdll')
    kernel.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype=wintypes.BOOL
    nt.NtResumeProcess.argtypes=[wintypes.HANDLE];nt.NtResumeProcess.restype=ctypes.c_long
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x4)
    handle=wintypes.HANDLE(int(process._handle))
    try:
        if not kernel.SetProcessAffinityMask(handle,1<<affinity):raise ctypes.WinError(ctypes.get_last_error())
        if nt.NtResumeProcess(handle)!=0:raise RuntimeError('resume own benchmark process failed')
        stdout,stderr=process.communicate(timeout=45)
        times=[wintypes.FILETIME() for _ in range(4)]
        kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        kernel.GetProcessTimes.restype=wintypes.BOOL
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]):raise ctypes.WinError(ctypes.get_last_error())
        ticks=lambda t:(t.dwHighDateTime<<32)|t.dwLowDateTime
        cpu=(ticks(times[2])+ticks(times[3]))/10000000
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr),cpu
    finally:
        if process.poll() is None:process.kill();process.wait()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pairs',type=int,default=5)
    parser.add_argument('--output',default='paired25');parser.add_argument('--candidate',default='bounded')
    parser.add_argument('--baseline',default='vector')
    parser.add_argument('--plan',type=Path,default=PLAN)
    parser.add_argument('--affinity',type=int)
    parser.add_argument('--output-root',type=Path,default=BASE)
    parser.add_argument('--build-root',type=Path,default=BASE)
    parser.add_argument('--deadline-utc',type=lambda value:datetime.fromisoformat(value))
    parser.add_argument('--omit-fixed-budget-option',action='store_true',
        help='Both builds use their default fixed limit; support older CLIs without --vm-budget')
    args=parser.parse_args()
    if args.pairs<1:parser.error('--pairs must be positive')
    if args.deadline_utc is not None and args.deadline_utc.utcoffset() is None:
        parser.error('--deadline-utc must include a UTC offset')
    out=args.output_root/args.output;out.mkdir(parents=True,exist_ok=False)
    plan=json.loads(args.plan.read_text());cases=plan['functional']['cases'];assert len(cases)==25
    variants=[args.baseline,args.candidate]
    assert len(set(variants)) == 2, 'comparison requires distinct variants'
    binaries={v:args.build_root/f'build-{v}/cholesky_runtime.exe' for v in variants}
    report={'completed':False,'records':[],'summary':[],'exe_sha256':{v:sha(p) for v,p in binaries.items()},
        'source_plan_sha256':sha(args.plan),'source_plan':str(args.plan),'tool_sha256':sha(Path(__file__)),
        'declaration':{'all_frozen_streams':25,'pairs':args.pairs,'variants':variants,'logical_cpu_affinity':args.affinity,
            'omit_redundant_fixed_budget_option':args.omit_fixed_budget_option,
            'warmups':1,'sequence':'alternate pair order and source starting variant',
            'scope':'all existing frozen streams, not new sources or independent holdout',
            'cpu_contention':'other project work may run; paired exploratory measurements, not exclusive hardware'}}
    began=perf_counter()
    def save(): (out/'partial.json').write_text(json.dumps(report,indent=2))
    try:
        for case_index,c in enumerate(cases):
            if args.deadline_utc is not None and datetime.now(timezone.utc)>=args.deadline_utc:
                raise TimeoutError('requested experiment deadline reached')
            reference={k:sha(c['paths'][k]) for k in ['source.c','program.meta','input.bin','oracle.bin']}
            assert all(v==c['hashes'][k] for k,v in reference.items())
            name=c['source']
            for phase in range(-1,args.pairs):
                order=variants.copy()
                if (phase+case_index)%2:order.reverse()
                for variant in order:
                    label=f'{case_index}-{phase}-{variant}';output=out/f'{label}.bin'
                    command=c['runtime_command_common'].copy();command[0]=str(binaries[variant])
                    if args.omit_fixed_budget_option and '--vm-budget' in command:
                        index=command.index('--vm-budget')
                        assert command[index+1]=='fixed', 'cannot omit a proved budget request'
                        del command[index:index+2]
                    command+=['--vm-backend','decoded-threaded','--output',str(output)]
                    row={'source':name,'kind':c['kind'],'phase':phase,'warmup':phase<0,'variant':variant,
                        'command':command,'passed':False};report['records'].append(row)
                    start=perf_counter();p,cpu=launch(command,args.affinity)
                    row.update(wall_seconds=perf_counter()-start,exit_code=p.returncode,cpu_seconds=cpu)
                    (out/f'{label}.stdout').write_text(p.stdout);(out/f'{label}.stderr').write_text(p.stderr)
                    p.check_returncode();metrics=json.loads(p.stdout);row['metrics']=metrics
                    assert metrics['vm_steps']==c['expected_vm_steps'],(name,'steps')
                    tick=perf_counter();assert sha(output)==c['hashes']['oracle.bin'],(name,'full C bytes')
                    assert output.stat().st_size==c['reference_bytes']
                    row.update(passed=True,reference_bytes=c['reference_bytes'],byte_check_seconds=perf_counter()-tick)
                    save()
            paired=[]
            for phase in range(args.pairs):
                pair={r['variant']:r for r in report['records'] if r['source']==name and r['phase']==phase}
                a,b=pair[args.baseline],pair[args.candidate]
                paired.append({'wall':b['wall_seconds']/a['wall_seconds'],
                    'compute':b['metrics']['compute_ms']/a['metrics']['compute_ms']})
            summary={'source':name,'kind':c['kind'],'pairs':paired,
                'wall_ratio_median':statistics.median(p['wall'] for p in paired),
                'compute_ratio_median':statistics.median(p['compute'] for p in paired)}
            report['summary'].append(summary);save()
            print(json.dumps({k:v for k,v in summary.items() if k!='pairs'}),flush=True)
        report.update(completed=True,passed=True,wall_seconds=perf_counter()-began)
        (out/'report.json').write_text(json.dumps(report,indent=2))
    except BaseException as error:
        report.update(failure={'type':type(error).__name__,'message':str(error)},wall_seconds=perf_counter()-began);save();raise


if __name__=='__main__':main()
