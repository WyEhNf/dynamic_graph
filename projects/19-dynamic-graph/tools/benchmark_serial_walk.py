"""Single-worker closed tile traversal, with unchanged multiworker control."""
from benchmark_column_workspace import main
from pathlib import Path
import argparse,json,subprocess,sys
from research_reference import sha256

if __name__=='__main__':
    gate=argparse.ArgumentParser(add_help=False);gate.add_argument('--phase',default='stress');args,_=gate.parse_known_args()
    project=Path(__file__).resolve().parent.parent
    if args.phase=='performance':
        for folder in('serial-walk-fp','serial-walk-lifecycle'):
            evidence=json.loads((project/'artifacts'/folder/'test-report.json').read_text())
            if not evidence['passed']or evidence['binary_sha256']!=sha256(project/'artifacts/baseline-serial-walk-runtime.exe'):raise AssertionError('single-worker FP and exception lifecycle must pass for this binary')
    main(milestone='serial-walk',variants=('thread-policy','serial-walk'),
         stress_variants=('serial-walk',),stress_queues=('heap','bucket'),
         perf_threads=(1,4),perf_sizes=(512,1024,2048,4096,10000),stream_threads=(1,),
         extra_geometry=((4096,32,(1,)),(10000,32,(1,))),
         large_single_repeats=3,
         contract='original C full bytes; single worker closed column/panel/row traversal, same ascending cell reduction and kernels; no resident tasks/locks/queues for serial; logical task cap retained; 4 workers unchanged materialized DAG control; auto geometry and forced B32 separate')
    if args.phase=='stress':
        subprocess.run([sys.executable,str(project/'tools/test_serial_fp.py')],check=True)
        subprocess.run([sys.executable,str(project/'tools/test_lazy_lifecycle.py'),'--variant','serial-walk'],check=True)
