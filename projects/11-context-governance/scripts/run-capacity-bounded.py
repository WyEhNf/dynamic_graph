"""Bound one capacity session, retaining an unfinished stage without calling it OOM."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
parser.add_argument('--timeout-seconds',type=float,default=600)
args,forwarded=parser.parse_known_args()
if args.timeout_seconds<=0:parser.error('Timeout must be positive')
root=Path(__file__).resolve().parents[1]
output=(root/args.output).resolve()
if output.exists():raise FileExistsError(output)
output.parent.mkdir(parents=True,exist_ok=True)
command=[sys.executable,str(root/'scripts/probe-model-capacity.py'),'--output',str(output),*forwarded]
invocation={'command':command,'session_timeout_seconds':args.timeout_seconds,'cutoff_predeclared':True,
            'started_unix':time.time(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'Deadline covers child startup, model loading, warmup, prompt construction and all requested stages. Stage call start is separately saved before inference.'}
output.with_suffix('.invocation.json').write_text(json.dumps(invocation,indent=2),encoding='utf-8')
with output.with_suffix('.stdout.log').open('w',encoding='utf-8') as stdout, output.with_suffix('.stderr.log').open('w',encoding='utf-8') as stderr:
    child=subprocess.Popen(command,cwd=root,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        code=child.wait(timeout=args.timeout_seconds)
    except subprocess.TimeoutExpired:
        observed=time.time()
        interrupted={'observed_unix':observed,'status':'session_deadline_without_complete_result','cutoff_predeclared':True,
                     'session_timeout_seconds':args.timeout_seconds,'process_id':child.pid,'reason':'Predeclared capacity-session deadline; not a CUDA OOM classification.'}
        if output.exists():
            interrupted['source_report_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
            current=json.loads(output.read_text(encoding='utf-8'))
            interrupted['in_progress_stage']=current.get('in_progress_stage')
            if current.get('in_progress_stage'):
                interrupted['unfinished_call_elapsed_seconds']=observed-current['in_progress_stage']['call_started_unix']
        try:
            import psutil
            process=psutil.Process(child.pid)
            interrupted['process_memory_observation']=process.memory_info()._asdict()
        except Exception as error:interrupted['process_observation_unavailable']=type(error).__name__
        try:
            interrupted['device_wide_gpu_observation']=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,power.draw','--format=csv,noheader'],capture_output=True,text=True,timeout=10).stdout.strip()
        except Exception as error:interrupted['gpu_observation_unavailable']=type(error).__name__
        child.kill();child.wait(timeout=30)
        output.with_suffix('.interruption.json').write_text(json.dumps(interrupted,indent=2),encoding='utf-8')
        print(json.dumps(interrupted),flush=True)
        raise SystemExit(124)
if code:raise SystemExit(code)
record=json.loads(output.read_text(encoding='utf-8'))
if 'finished_unix' not in record:raise RuntimeError('Child exited without a finalized report')
print(json.dumps({'output':str(output),'completed_stages':len(record['runs']),'runs':[{'tokens':r['actual_prompt_tokens'],'completed':r['completed'],'seconds':r['live_wall_seconds']} for r in record['runs']]}),flush=True)
